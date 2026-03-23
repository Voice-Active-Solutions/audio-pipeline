#!/usr/bin/env python3

from asyncio.log import logger
import json
import os
import threading

from dotenv import load_dotenv
from ibm_cloud_sdk_core.authenticators import IAMAuthenticator
from ibm_watson import ApiException, SpeechToTextV1
from ibm_watson.websocket import AudioSource, RecognizeCallback


class DefaultASRCallback(RecognizeCallback):
    """Callback handler for ASR recognition events."""

    def __init__(self):
        RecognizeCallback.__init__(self)
        self.end_event = threading.Event()

    def on_data(self, data):
        """Called when recognition data is received."""
        print("Customised ASR batch job completed: %s",
                         json.dumps(data, indent=2))
        self.end_event.set()

    def on_error(self, error):
        """Called when an error occurs."""
        print('Error received: %s', error)
        self.end_event.set()

    def on_inactivity_timeout(self, error):
        """Called when inactivity timeout occurs."""
        print('ASR batch job timed out: %s', error)
        self.end_event.set()


class BatchASR:
    """
    A class for batch speech-to-text processing using IBM Watson Speech to Text service.
    
    Attributes:
        api_key (str): IBM Watson API key for authentication
        service_url (str): IBM Watson service URL endpoint
        callback (RecognizeCallback): Callback handler for ASR events
    """
    

    def __init__(self, api_key, service_url, callback=None):
        """
        Initialize the BatchASR object with API credentials.
        
        Args:
            api_key (str): IBM Watson API key
            service_url (str): IBM Watson service URL
            callback (RecognizeCallback): Optional callback handler (default: None, uses ASRCallback)
        """
        self.api_key = api_key
        self.service_url = service_url
        self._callback = callback
        
        # Initialize the Watson Speech to Text client
        authenticator = IAMAuthenticator(self.api_key)
        self.speech_to_text = SpeechToTextV1(authenticator=authenticator)
        self.speech_to_text.set_service_url(self.service_url)
    
    
    def recognize_audio(self, audio_file_path, content_type='audio/wav',
                        model='en-GB_BroadbandModel'):
        """
        Recognize speech from an audio file using websocket connection.
        
        Args:
            audio_file_path (str): Path to the audio file
            content_type (str): MIME type of the audio file (default: 'audio/wav')
            model (str): Watson ASR model to use (default: 'en-GB_BroadbandModel')
        Returns:
            None
        """
        # Priority: method parameter > object property > default ASRCallback
        if self._callback is None:
            raise ValueError("Callback is not initialized")

        with open(audio_file_path, 'rb') as audio_file:
            audio_source = AudioSource(audio_file)
            self.speech_to_text.recognize_using_websocket(
                audio=audio_source,
                content_type=content_type,
                recognize_callback=self._callback,
                model=model
            )


    @property
    def callback(self):
        print("getter method called")
        return self._callback

    @callback.setter
    def callback(self, cb):
        print("setter method called")
        self._callback = cb


# Example usage
if __name__ == "__main__":
    load_dotenv()

    WATSON_API_KEY = os.getenv("WATSON_ASR_API_KEY")
    WATSON_ASR_URL = os.getenv("WATSON_ASR_URL")

    if not WATSON_API_KEY or not WATSON_ASR_URL:
        raise ValueError("Environment variables not set")
    local_wav_filename = '../audio/test1.wav'

    cb = DefaultASRCallback()

    # Initialize the BatchASR object with your credentials
    try:
        asr = BatchASR(WATSON_API_KEY, WATSON_ASR_URL, cb)
        asr.recognize_audio(local_wav_filename)
        cb.end_event.wait()
    except ValueError as ve:
        print("Initialization error: " + str(ve))
    except ApiException as ex:
        print(f"Method failed with status code {ex.code}: {ex.message}")
