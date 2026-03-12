#!/usr/bin/env python3

import json
import os

from dotenv import load_dotenv
from ibm_cloud_sdk_core.authenticators import IAMAuthenticator
from ibm_watson import SpeechToTextV1
from ibm_watson.websocket import AudioSource, RecognizeCallback


# setup the callback function
class ASRCallback(RecognizeCallback):
    def __init__(self):
        RecognizeCallback.__init__(self)

    def on_data(self, data):
        print("ASR job has completed!")
        print(json.dumps(data, indent=2))

    def on_error(self, error):
        print('Error received: {}'.format(error))

    def on_inactivity_timeout(self, error):
        print('Inactivity timeout: {}'.format(error))


if __name__ == "__main__":
    load_dotenv()

    WATSON_API_KEY = os.getenv("WATSON_ASR_API_KEY")
    WATSON_ASR_URL = os.getenv("WATSON_ASR_URL")

    if not WATSON_API_KEY or not WATSON_ASR_URL:
        raise ValueError("Environment variables not set")

    # initialise the Watson Speech to Text client
    authenticator = IAMAuthenticator(WATSON_API_KEY)
    speech_to_text = SpeechToTextV1(authenticator=authenticator)
    speech_to_text.set_service_url(WATSON_ASR_URL)

    asr_cb = ASRCallback()
    local_wav_filename = '../../audio/recording.wav'

    with open(local_wav_filename, 'rb') as audio_file:
        audio_source = AudioSource(audio_file)
        speech_to_text.recognize_using_websocket(
            audio=audio_source,
            content_type='audio/wav',
            recognize_callback=asr_cb,
            model='en-GB_BroadbandModel')
