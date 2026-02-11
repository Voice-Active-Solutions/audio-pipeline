#!/usr/bin/env python3

import json
from ibm_watson import SpeechToTextV1
from ibm_cloud_sdk_core.authenticators import IAMAuthenticator
from ibm_watson.websocket import RecognizeCallback, AudioSource


class BatchASR_IBMWatson:
    """
    A class for batch speech-to-text processing using IBM Watson Speech to Text service.
    
    Attributes:
        api_key (str): IBM Watson API key for authentication
        service_url (str): IBM Watson service URL endpoint
        speech_to_text (SpeechToTextV1): Watson Speech to Text client instance
    """
    
    def __init__(self, api_key, service_url):
        """
        Initialize the BatchASR object with API credentials.
        
        Args:
            api_key (str): IBM Watson API key
            service_url (str): IBM Watson service URL
        """
        self.api_key = api_key
        self.service_url = service_url
        
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
            callback (RecognizeCallback): Custom callback handler (default: None, uses ASRCallback)
        
        Returns:
            None
        """
        # Use custom callback if provided, otherwise use default
        if callback is None:
            callback = self.ASRCallback()
        
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
    # Initialize the BatchASR object with your credentials
    WATSON_ASR_API_KEY = "ZYBXe-YjIkeaOSS272kN5nbJY-QsCny7QFsXNKT3_adx"
    WATSON_ASR_URL = "https://api.eu-gb.speech-to-text.watson.cloud.ibm.com/instances/57bf3a5e-6986-4115-b0b6-127b2b66fc4a"
    
    asr = BatchASR_IBMWatson(api_key=WATSON_ASR_API_KEY, service_url=WATSON_ASR_URL)
    
    # Recognize audio from a file
    asr.recognize_audio('test.wav')
