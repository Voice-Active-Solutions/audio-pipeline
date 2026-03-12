#!/usr/bin/env python3

import os

import ibm_boto3
from dotenv import load_dotenv
from ibm_botocore.client import ClientError, Config

CHUNK_SIZE = 1024 * 1024    # 1 MB chunk size for streaming audio from COS


def create_cos_client(cos_api_key_id, cos_instance_crn, cos_endpoint):
    """Create and return an IBM COS client."""
    return ibm_boto3.client(
        service_name='s3',
        ibm_api_key_id=cos_api_key_id,
        ibm_service_instance_id=cos_instance_crn,
        config=Config(signature_version='oauth'),
        endpoint_url=cos_endpoint
    )


def stream_audio_from_cos(cos, bucket_name, object_key, local_filename):
    """
    Stream an audio file from IBM COS and save it
    locally. This method reads the file in chunks to avoid
    loading the entire file into memory.
    """
    try:
        response = cos.get_object(Bucket=bucket_name, Key=object_key)
        body_stream = response['Body']

        # Open a local file in binary write mode
        with open(local_filename, 'wb') as f:
            for chunk in iter(lambda: body_stream.read(CHUNK_SIZE), b''):
                f.write(chunk)

        print(f"Audio file streamed and saved as '{local_filename}'")

    except ClientError as e:
        print(f"Unable to stream file: {e}")


if __name__ == "__main__":
    load_dotenv()

    COS_ENDPOINT = os.getenv("COS_ENDPOINT")
    COS_API_KEY_ID = os.getenv("COS_API_KEY_ID")
    COS_INSTANCE_CRN = os.getenv("COS_INSTANCE_CRN")

    if not COS_API_KEY_ID or not COS_ENDPOINT or not COS_INSTANCE_CRN:
        raise ValueError("Environment variables not set")

    cos_client = create_cos_client(COS_API_KEY_ID,
                                   COS_INSTANCE_CRN,
                                   COS_ENDPOINT)

    bucket_name = "cos-audio-pipeline"
    audio_test_file = "test1.wav"  # The object key in the COS bucket

    # Save streamed audio locally
    stream_audio_from_cos(cos_client, bucket_name, 
                          audio_test_file, "downloaded-test.wav")