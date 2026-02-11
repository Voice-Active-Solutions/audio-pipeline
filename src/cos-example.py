#!/usr/bin/env python3

import ibm_boto3
from ibm_botocore.client import Config, ClientError

# IBM COS credentials and configuration
COS_ENDPOINT = "https://s3.eu-gb.cloud-object-storage.appdomain.cloud"
COS_API_KEY_ID = "1wU_ZzCdnFqXCv8DdYusdrpSH0XuA_YBixMLtP6znt3r"
COS_INSTANCE_CRN = "crn:v1:bluemix:public:cloud-object-storage:global:a/8186f85d5f36d73d0caeb990c044a71f:946fec9c-f641-4a52-9a75-ed49dfc28949::"
BUCKET_NAME = "cos-audio-pipeline"
OBJECT_KEY = "test1.wav"  # The object key in COS

def create_cos_client():
    """Create and return an IBM COS client."""
    return ibm_boto3.client(
        service_name='s3',
        ibm_api_key_id=COS_API_KEY_ID,
        ibm_service_instance_id=COS_INSTANCE_CRN,
        config=Config(signature_version='oauth'),
        endpoint_url=COS_ENDPOINT
    )


def stream_audio_from_cos(bucket_name, object_key, local_filename):
    """
    Stream an audio file from IBM COS and save it locally without loading into memory.
    """
    cos = create_cos_client()
    try:
        response = cos.get_object(Bucket=bucket_name, Key=object_key)
        body_stream = response['Body']

        # Open a local file in binary write mode
        with open(local_filename, 'wb') as f:
            for chunk in iter(lambda: body_stream.read(1024 * 1024), b''):  # 1 MB chunks
                f.write(chunk)

        print(f"Audio file streamed and saved as '{local_filename}'")

    except ClientError as e:
        print(f"Unable to stream file: {e}")


if __name__ == "__main__":
    # Save streamed audio locally
    stream_audio_from_cos(BUCKET_NAME, OBJECT_KEY, "test.wav")