#!/usr/bin/env python3

import json
from ibm_watson import SpeechToTextV1
from ibm_cloud_sdk_core.authenticators import IAMAuthenticator
from ibm_watson.websocket import RecognizeCallback, AudioSource
from dotenv import load_dotenv
import os

class BatchASR:
    """
    A class for batch speech-to-text processing using IBM Watson Speech to Text service.
    
    Attributes:
        api_key (str): IBM Watson API key for authentication
        service_url (str): IBM Watson service URL endpoint
        speech_to_text (SpeechToTextV1): Watson Speech to Text client instance
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
        self.callback = callback  # Store callback as a property
        
        # Initialize the Watson Speech to Text client
        authenticator = IAMAuthenticator(self.api_key)
        self.speech_to_text = SpeechToTextV1(authenticator=authenticator)
        self.speech_to_text.set_service_url(self.service_url)
    
    class ASRCallback(RecognizeCallback):
        """Callback handler for ASR recognition events."""
        
        def __init__(self):
            RecognizeCallback.__init__(self)
        
        def on_data(self, data):
            """Called when recognition data is received."""
            print("ASR job has completed!")
            print(json.dumps(data, indent=2))
        
        def on_error(self, error):
            """Called when an error occurs."""
            print('Error received: {}'.format(error))
        
        def on_inactivity_timeout(self, error):
            """Called when inactivity timeout occurs."""
            print('Inactivity timeout: {}'.format(error))
    
    def recognize_audio(self, audio_file_path, content_type='audio/wav',
                        model='en-GB_BroadbandModel', callback=None):
        """
        Recognize speech from an audio file using websocket connection.
        
        Args:
            audio_file_path (str): Path to the audio file
            content_type (str): MIME type of the audio file (default: 'audio/wav')
            model (str): Watson ASR model to use (default: 'en-GB_BroadbandModel')
            callback (RecognizeCallback): Custom callback handler (default: None, uses object's callback property)
        
        Returns:
            None
        """
        # Priority: method parameter > object property > default ASRCallback
        if callback is None:
            callback = self.callback if self.callback is not None else self.ASRCallback()
        
        with open(audio_file_path, 'rb') as audio_file:
            audio_source = AudioSource(audio_file)
            self.speech_to_text.recognize_using_websocket(
                audio=audio_source,
                content_type=content_type,
                recognize_callback=callback,
                model=model
            )


# Example usage
if __name__ == "__main__":
    load_dotenv()

    WATSON_API_KEY = os.getenv("WATSON_ASR_API_KEY")
    WATSON_ASR_URL = os.getenv("WATSON_ASR_URL")

    if not WATSON_API_KEY or not WATSON_ASR_URL:
        raise ValueError("Environment variables not set")
    
    local_wav_filename = '../../audio/recording.wav'    

    # Initialize the BatchASR object with your credentials
    asr = BatchASR(api_key=WATSON_API_KEY, service_url=WATSON_ASR_URL)
    asr.callback = BatchASR.ASRCallback()  # Set callback property
    asr.recognize_audio(local_wav_filename)
