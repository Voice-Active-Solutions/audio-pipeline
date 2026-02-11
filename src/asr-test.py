#!/usr/bin/env python3

import json
from ibm_watson import SpeechToTextV1
from ibm_cloud_sdk_core.authenticators import IAMAuthenticator
from ibm_watson.websocket import RecognizeCallback, AudioSource


WATSON_ASR_API_KEY = "ZYBXe-YjIkeaOSS272kN5nbJY-QsCny7QFsXNKT3_adx"
WATSON_ASR_URL = "https://api.eu-gb.speech-to-text.watson.cloud.ibm.com/instances/57bf3a5e-6986-4115-b0b6-127b2b66fc4a"

# initialise the Watson Speech to Text client
authenticator = IAMAuthenticator(WATSON_ASR_API_KEY)
speech_to_text = SpeechToTextV1(authenticator=authenticator)
speech_to_text.set_service_url(WATSON_ASR_URL)

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

asr_cb = ASRCallback()


with open('test.wav', 'rb') as audio_file:
    audio_source = AudioSource(audio_file)
    speech_to_text.recognize_using_websocket(
        audio=audio_source,
        content_type='audio/wav',
        recognize_callback=asr_cb,
        model='en-GB_BroadbandModel')