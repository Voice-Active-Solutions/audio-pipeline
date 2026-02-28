#!/usr/bin/env python3

import tempfile
from dotenv import load_dotenv
import json
import os
from batch_asr import BatchASR
from ibm_watson.websocket import RecognizeCallback
from ibm_watson import ApiException
import ibm_boto3
from ibm_botocore.client import Config, ClientError
import logging
import sys
from logging.handlers import RotatingFileHandler
import threading
import re


VERSIONFILE = "_version.py"


def setup_logging():
    """Set up logging configuration."""

    # Create logs directory if it doesn't exist
    log_dir = os.getenv("LOG_DIR", "logs")
    os.makedirs(log_dir, exist_ok=True)

    # Configure root logger
    logger = logging.getLogger()
    logger.setLevel(os.getenv('LOG_LEVEL', 'INFO'))

    # Console handler (stdout) — visible via `docker logs`
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    ))
    logger.addHandler(console_handler)

    # Rotating file handler — persisted in mounted volume
    file_handler = RotatingFileHandler(
        os.path.join(log_dir, "app.log"),
        maxBytes=5 * 1024 * 1024,  # 5 MB per file
        backupCount=3
    )
    file_handler.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    ))
    logger.addHandler(file_handler)

    return logger


def create_cos_client(cos_api_key_id, cos_instance_crn, cos_endpoint):
    """Create and return an IBM COS client."""
    return ibm_boto3.client(
        service_name='s3',
        ibm_api_key_id=cos_api_key_id,
        ibm_service_instance_id=cos_instance_crn,
        config=Config(signature_version='oauth'),
        endpoint_url=cos_endpoint
    )


class CustomASRCallback(RecognizeCallback):
    """Callback handler for ASR recognition events."""
    
    def __init__(self, logger):
        self.logger = logger
        RecognizeCallback.__init__(self)
        self.end_event = threading.Event()
    
    def on_data(self, data):
        """Called when recognition data is received."""
        self.logger.info("ASR batch job completed: %s", json.dumps(data, indent=2))
        self.end_event.set()
    
    def on_error(self, error):
        """Called when an error occurs."""
        self.logger.error('Error received: %s', error)
        self.end_event.set()

    def on_inactivity_timeout(self, error):
        """Called when inactivity timeout occurs."""
        self.logger.warning('ASR batch job timed out: %s', error)
        self.end_event.set()


def load_audio_from_cos(cos, bucket_name, object_key, local_filename, logger) -> bool:
    """
    Stream an audio file from IBM COS and save it locally 
    without loading it entirely into memory.
    """
    try:
        response = cos.get_object(Bucket=bucket_name, Key=object_key)
        body_stream = response['Body']

        # Open a local file in binary write mode
        with open(local_filename, 'wb') as f:
            for chunk in iter(lambda: body_stream.read(1024 * 1024), b''):  # 1 MB chunks
                f.write(chunk)
        return True
    except ClientError as e:
        logger.error("Failed to load audio from COS: %s", e)
        return False


def read_app_version(versionfile: str) -> str:
    local_path = os.path.join(os.path.dirname(__file__), versionfile)
    verstrline = open(local_path, "rt", encoding="utf-8").read()
    VSRE = r"^__version__ = ['\"]([^'\"]*)['\"]"
    mo = re.search(VSRE, verstrline, re.M)
    if mo:
        verstr = mo.group(1)
    else:
        raise RuntimeError("No version string in %s", versionfile)
    
    return verstr


################# MAIN APPLICATION LOGIC ###############
def main() -> None:
    load_dotenv()

    app_version = read_app_version(VERSIONFILE)
    logger = setup_logging()
    logger.info("Starting AudioPipeline application version %s", app_version)

    # read the CE_DATA environment variable, which contains
    # the event data from the COS trigger
    event_data = os.getenv("CE_DATA")
    logger.info("Received event data")

    COS_ENDPOINT = os.getenv("COS_ENDPOINT")
    COS_API_KEY_ID = os.getenv("COS_API_KEY_ID")
    COS_INSTANCE_CRN = os.getenv("COS_INSTANCE_CRN")

    if not COS_API_KEY_ID or not COS_ENDPOINT or not COS_INSTANCE_CRN:
        logger.error("COS environment variables not set.")
        raise ValueError("COS environment variables not set")

    cos_client = create_cos_client(COS_API_KEY_ID,
                                   COS_INSTANCE_CRN,
                                   COS_ENDPOINT)
    
    WATSON_API_KEY = os.getenv("WATSON_ASR_API_KEY")
    WATSON_ASR_URL = os.getenv("WATSON_ASR_URL")
    if not WATSON_API_KEY or not WATSON_ASR_URL:
        logger.error("Watson ASR environment variables not set")
        raise ValueError("Watson ASR environment variables not set")

    # extract the bucket name and object key from the event data as strings
    if event_data is None:
        logger.warning("No event data found in CE_DATA environment variable.")
        return
  
    logger.debug("Received event data: %s", event_data)
    event_payload = json.loads(event_data)
    bucket = event_payload.get("bucket")
    object_key = event_payload.get("key")
    request_id = event_payload.get("request_id")

    logger.info("Processing request_id: %s", request_id)
    logger.info("File %s being read from from bucket: %s", object_key, bucket)

    local_audio_file = None
    try:
        _fd, local_audio_file = tempfile.mkstemp(suffix=".wav")
        os.close(_fd)
        if load_audio_from_cos(cos_client, bucket, object_key, 
                               local_audio_file, logger):
            cb = CustomASRCallback(logger)
            asr = BatchASR(api_key=WATSON_API_KEY,
                           service_url=WATSON_ASR_URL,
                           callback=cb)
            
            asr.recognize_audio(local_audio_file)
            # Wait for ASR to complete before exiting
            cb.end_event.wait()
        else:
            logger.error("Failed to load audio file from COS.")
    except ApiException as e:
        logger.error("IBM Speech to Text error with code %d: %s",
                     e.code, e.message)
        if e.code == 400:
            logger.error("Check value of WATSON_ASR_API_KEY")
    finally:
        if local_audio_file and os.path.exists(local_audio_file):
            os.remove(local_audio_file)


if __name__ == "__main__":
    main()
