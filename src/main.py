#!/usr/bin/env python3

from dotenv import load_dotenv
import json
import os
from batch_asr import BatchASR
from ibm_watson.websocket import RecognizeCallback

WATSON_ASR_API_KEY = "ZYBXe-YjIkeaOSS272kN5nbJY-QsCny7QFsXNKT3_adx"
WATSON_ASR_URL = "https://api.eu-gb.speech-to-text.watson.cloud.ibm.com/instances/57bf3a5e-6986-4115-b0b6-127b2b66fc4a"


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

    # TODO: write the file to local storage, then it is ready to
    # be processed by the ASR service

    audio_file = 'test.wav'

    cb1 = CustomASRCallback()
    asr = BatchASR(api_key=WATSON_ASR_API_KEY, service_url=WATSON_ASR_URL,
                   callback=cb1)
    asr.recognize_audio(audio_file)


if __name__ == "__main__":
    main()
