#!/usr/bin/env python3

from dotenv import load_dotenv
import json
import os


def main() -> None:
    load_dotenv()

    bucket_name = os.getenv("BUCKET") 
    print(f"Bucket name is: {bucket_name}")

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

    print(f"Bucket is: {bucket}")
    print(f"Object key is: {object_key}")


if __name__ == "__main__":
    main()
