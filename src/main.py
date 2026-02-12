#!/usr/bin/env python3

from dotenv import load_dotenv
import json
import os
from batch_asr import BatchASR
from ibm_watson.websocket import RecognizeCallback
import ibm_boto3
from ibm_botocore.client import Config, ClientError



class CustomASRCallback(RecognizeCallback):
    """Callback handler for ASR recognition events."""
    
    def __init__(self):
        RecognizeCallback.__init__(self)
    
    def on_data(self, data):
        """Called when recognition data is received."""
        print("Your speech has been recognized! Here are the results:")
        print(json.dumps(data, indent=2))
    
    def on_error(self, error):
        """Called when an error occurs."""
        print('Error received: {}'.format(error))
    
    def on_inactivity_timeout(self, error):
        """Called when inactivity timeout occurs."""
        print('Inactivity timeout: {}'.format(error))


def create_cos_client(cos_api_key_id, cos_instance_crn, cos_endpoint):
    """Create and return an IBM COS client."""
    return ibm_boto3.client(
        service_name='s3',
        ibm_api_key_id=cos_api_key_id,
        ibm_service_instance_id=cos_instance_crn,
        config=Config(signature_version='oauth'),
        endpoint_url=cos_endpoint
    )


def load_audio_from_cos(cos, bucket_name, object_key, local_filename):
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

        print(f"Audio file saved as '{local_filename}'")

    except ClientError as e:
        print(f"Unable to stream file: {e}")


def main() -> None:
    load_dotenv()

    # read the CE_DATA environment variable, which contains
    # the event data from the COS trigger
    event_data = os.getenv("CE_DATA")
    print(f"Received event data: {event_data}")

    COS_ENDPOINT = os.getenv("COS_ENDPOINT")
    COS_API_KEY_ID = os.getenv("COS_API_KEY_ID")
    COS_INSTANCE_CRN = os.getenv("COS_INSTANCE_CRN")

    if not COS_API_KEY_ID or not COS_ENDPOINT or not COS_INSTANCE_CRN:
        raise ValueError("COS environment variables not set")

    cos_client = create_cos_client(COS_API_KEY_ID,
                                   COS_INSTANCE_CRN,
                                   COS_ENDPOINT)
    
    WATSON_API_KEY = os.getenv("WATSON_ASR_API_KEY")
    WATSON_ASR_URL = os.getenv("WATSON_ASR_URL")
    if not WATSON_API_KEY or not WATSON_ASR_URL:
        raise ValueError("Watson ASR environment variables not set")

    # extract the bucket name and object key from the event data as strings
    if event_data is None:
        print("No event data found in CE_DATA environment variable.")
        return
  
    event_payload = json.loads(event_data)
    bucket = event_payload.get("bucket")
    object_key = event_payload.get("key")
    request_id = event_payload.get("request_id")

    print(f"Bucket is: {bucket}")
    print(f"Object key is: {object_key}")
    print(f"Request ID is: {request_id}")

    local_audio_file = "temp.wav"
    load_audio_from_cos(cos_client, bucket, object_key, local_audio_file)

    cb1 = CustomASRCallback()
    asr = BatchASR(api_key=WATSON_API_KEY,
                   service_url=WATSON_ASR_URL,
                   callback=cb1)
    
    asr.recognize_audio(local_audio_file)


if __name__ == "__main__":
    main()
