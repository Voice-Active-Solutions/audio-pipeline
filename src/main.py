#!/usr/bin/env python3

import json
import logging
import os
import re
import sys
import tempfile
from logging.handlers import RotatingFileHandler

from dotenv import load_dotenv
import ibm_boto3
from ibm_botocore.client import ClientError, Config

from batch_asr import IBMWatsonASR

VERSIONFILE = "_version.py"

ERROR_COS = 1
ERROR_ASR = 2
ERROR_EVENT_DATA = 3

CHUNK_SIZE = 1024 * 1024    # 1 MB chunk size for streaming audio from COS


def setup_logging():
    """Set up logging configuration.

    Creates a logs directory if one does not already exist, then configures
    the root logger with two handlers:
      - A console (stdout) handler for visibility via `docker logs`.
      - A rotating file handler that persists logs to a mounted volume,
        capped at 5 MB per file with up to 3 backup files retained.

    The log directory and log level are controlled by the ``LOG_DIR`` and
    ``LOG_LEVEL`` environment variables, defaulting to ``"logs"`` and
    ``"INFO"`` respectively.

    Returns:
        logging.Logger: The configured root logger instance.
    """

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


def redact_key(s: str, start_count: int = 5, end_count: int = 5) -> str:
    """Redact a sensitive key or token for safe inclusion in log output.

    Preserves the first ``start_count`` and last ``end_count`` characters of
    the string and replaces everything in between with ``"..."``, giving just
    enough context to identify a key without exposing its full value.

    If the string is shorter than or equal to ``start_count + end_count``
    characters it is returned unchanged.

    Args:
        s: The sensitive string to redact.
        start_count: Number of leading characters to preserve. Defaults to 5.
        end_count: Number of trailing characters to preserve. Defaults to 5.

    Returns:
        str: The redacted string, e.g. ``"ABCDE...VWXYZ"``.
    """
    if len(s) <= start_count + end_count:
        return s
    return s[:start_count] + "..." + s[-end_count:]


def create_cos_client(cos_api_key_id, cos_instance_crn, cos_endpoint):
    """Create and return an IBM Cloud Object Storage (COS) S3 client.

    Initialises an ``ibm_boto3`` S3 client using OAuth-based authentication
    against the specified COS endpoint.

    Args:
        cos_api_key_id (str): IBM Cloud API key used to authenticate with COS.
        cos_instance_crn (str): CRN of the COS service instance.
        cos_endpoint (str): Full URL of the COS regional or cross-region endpoint.

    Returns:
        botocore.client.S3: A configured IBM COS S3 client ready to make requests.
    """
    return ibm_boto3.client(
        service_name='s3',
        ibm_api_key_id=cos_api_key_id,
        ibm_service_instance_id=cos_instance_crn,
        config=Config(signature_version='oauth'),
        endpoint_url=cos_endpoint
    )


def load_audio_from_cos(cos, bucket_name, object_key, object_length,
                        local_filename, logger) -> bool:
    """Stream an audio file from IBM COS and save it to a local file.

    Downloads the object in fixed-size chunks (``CHUNK_SIZE``) to avoid
    loading the entire file into memory, then verifies that the number of
    bytes written matches the expected ``object_length``.

    Args:
        cos: An IBM COS S3 client as returned by :func:`create_cos_client`.
        bucket_name (str): Name of the COS bucket containing the audio file.
        object_key (str): Key (path) of the object within the bucket.
        object_length (int): Expected size of the object in bytes, used to
            verify download integrity.
        local_filename (str): Absolute path to the local file where the audio
            data will be written.
        logger (logging.Logger): Logger instance used to record progress and
            error messages.

    Returns:
        bool: ``True`` if the file was downloaded successfully and the byte
        count matches ``object_length``; ``False`` otherwise.
    """
    try:
        response = cos.get_object(Bucket=bucket_name, Key=object_key)
        body_stream = response['Body']

        total_bytes = 0
        # Open a local file in binary write mode
        with open(local_filename, 'wb') as f:
            for chunk in iter(lambda: body_stream.read(CHUNK_SIZE), b''):  # 1 MB chunks
                total_bytes += f.write(chunk)

        if total_bytes == object_length:
            logger.info("Successfully loaded audio file '%s' from bucket: %d bytes",
                        object_key, total_bytes)
            return True

        logger.error("Mismatch in expected and actual bytes read from bucket: "
                     "expected %d, got %d", object_length, total_bytes)
        return False
    except ClientError as e:
        logger.error("Failed to load audio from bucket: %s", e)
        return False


def read_app_version(versionfile: str) -> str:
    """Read and return the application version string from a version file.

    Looks for a line of the form ``__version__ = 'x.y.z'`` (single or double
    quotes) in the specified file, which must reside in the same directory as
    this module.

    Args:
        versionfile (str): Filename (not full path) of the version file to
            read, e.g. ``"_version.py"``.

    Returns:
        str: The version string extracted from the file, e.g. ``"1.2.3"``.

    Raises:
        RuntimeError: If no ``__version__`` assignment is found in the file.
    """
    local_path = os.path.join(os.path.dirname(__file__), versionfile)
    with open(local_path, "rt", encoding="utf-8") as f:
        verstrline = f.read().strip()
    VSRE = r"^__version__ = ['\"]([^'\"]*)['\"]"
    mo = re.search(VSRE, verstrline, re.M)
    if mo:
        verstr = mo.group(1)
    else:
        raise RuntimeError("No version string in %s" % versionfile)
    return verstr


# MAIN APPLICATION LOGIC ###############
def main() -> int:
    """Entry point for the AudioPipeline application.

    Orchestrates the end-to-end audio transcription pipeline:

    1. Loads environment variables and reads the application version.
    2. Parses the COS trigger event from the ``CE_DATA`` environment variable.
    3. Validates required COS and Watson ASR credentials.
    4. Downloads the audio file (WAV only) from IBM COS to a temporary file.
    5. Submits the audio to IBM Watson Speech-to-Text via :class:`BatchASR`.
    6. Prints the assembled transcript to stdout.
    7. Cleans up the temporary audio file on exit.

    Returns:
        int: An exit code indicating the outcome of the run:
            - ``0``  — success.
            - ``ERROR_COS`` (1) — COS configuration or download failure.
            - ``ERROR_ASR`` (2) — ASR configuration or API failure.
            - ``ERROR_EVENT_DATA`` (3) — missing or malformed event data.
    """
    load_dotenv()

    app_version = read_app_version(VERSIONFILE)
    logger = setup_logging()
    logger.info("Starting AudioPipeline application version %s", app_version)

    # read the CE_DATA environment variable, which contains
    # the event data from the COS trigger
    event_data = os.getenv("CE_DATA")
    logger.info("Received event data")

    # extract the bucket name and object key from the event data as strings
    if event_data is None:
        logger.warning("No event data found in CE_DATA environment variable.")
        return ERROR_EVENT_DATA
    logger.debug("Received event data: %s", event_data)

    event_payload = json.loads(event_data)
    bucket = event_payload.get("bucket")
    object_key = event_payload.get("key")
    notification_object = event_payload.get("notification")
    request_id = notification_object.get("request_id")
    request_time = notification_object.get("request_time")
    content_type = notification_object.get("content_type")
    object_length = int(notification_object.get("object_length"))

    if content_type != "audio/wav":
        logger.warning("Unsupported content type: %s. Only audio/wav is supported.",
                       content_type)
        return ERROR_COS

    if object_length == 0:
        logger.warning("Audio file is empty.")
        return ERROR_COS

    logger.info("Processing request_id: %s", request_id)
    logger.info("Processing request_time: %s", request_time)
    logger.info("Looking for '%s' in bucket '%s'", object_key, bucket)

    local_audio_file = None

    COS_ENDPOINT = os.getenv("COS_ENDPOINT")
    COS_API_KEY_ID = os.getenv("COS_API_KEY_ID")
    COS_INSTANCE_CRN = os.getenv("COS_INSTANCE_CRN")

    if not COS_API_KEY_ID or not COS_ENDPOINT or not COS_INSTANCE_CRN:
        logger.error("COS environment variables not set.")
        return ERROR_COS

    cos_client = create_cos_client(COS_API_KEY_ID,
                                   COS_INSTANCE_CRN,
                                   COS_ENDPOINT)

    try:
        _fd, local_audio_file = tempfile.mkstemp(suffix=".wav")
        os.close(_fd)
        if load_audio_from_cos(cos_client, bucket, object_key, object_length,
                               local_audio_file, logger):
            WATSON_ASR_API_KEY = os.getenv("WATSON_ASR_API_KEY")
            WATSON_ASR_URL = os.getenv("WATSON_ASR_URL")
            try:
                asr = IBMWatsonASR(WATSON_ASR_API_KEY, WATSON_ASR_URL)
            except Exception as e:
                logger.error("Failed to initialise ASR client: %s", e)
                return ERROR_ASR

            try:
                # run the ASR transcription and print the result
                transcript = asr.recognize_audio(local_audio_file)
                print(transcript)
            except ValueError as e:
                logger.error("Error occurred while attempting to transcribe audio: %s", e)
                logger.error("Check ASR API key, service URL, and audio file format.")
                logger.error("ASR API key: %s", redact_key(WATSON_ASR_API_KEY))
                logger.error("ASR service URL: %s", WATSON_ASR_URL)
                return ERROR_ASR
        else:
            return ERROR_COS
    finally:
        if local_audio_file and os.path.exists(local_audio_file):
            os.remove(local_audio_file)

    return 0


if __name__ == "__main__":
    sys.exit(main())
