#!/usr/bin/env python3

from dotenv import load_dotenv
import json
import os

WATSON_ASR_API_KEY = "ZYBXe-YjIkeaOSS272kN5nbJY-QsCny7QFsXNKT3_adx"
WATSON_ASR_URL = "https://api.eu-gb.speech-to-text.watson.cloud.ibm.com/instances/57bf3a5e-6986-4115-b0b6-127b2b66fc4a"


def main() -> None:
    load_dotenv()

    # read the CE_DATA environment variable, which contains
    # the event data from the COS trigger
    event_data = os.getenv("CE_DATA")

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


if __name__ == "__main__":
    main()
