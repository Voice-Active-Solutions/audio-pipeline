#!/usr/bin/env python3

import json
import os

from dotenv import load_dotenv
from ibm_cloud_sdk_core.authenticators import IAMAuthenticator
from ibm_watson import ApiException, SpeechToTextV1


class BatchASR:
    """
    A class for batch speech-to-text processing using the
    IBM Watson Speech to Text service.
    
    Attributes:
        api_key (str): IBM Watson API key for authentication
        service_url (str): IBM Watson service URL endpoint
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
    
    
    def recognize_audio(self, audio_file_path, content_type='audio/wav',
                        model='en-GB_BroadbandModel'):
        """
        Recognize speech from an audio file using websocket connection.
        
        Args:
            audio_file_path (str): Path to the audio file
            content_type (str): MIME type of the audio file (default: 'audio/wav')
            model (str): Watson Speech to Text model to use (default: 'en-GB_BroadbandModel')
        Returns:
            asr_response (dict): The JSON response from the Watson Speech to Text service
        """
        with open(audio_file_path, 'rb') as audio_file:
            asr_response = self.speech_to_text.recognize(audio=audio_file,
                                                         content_type=content_type,
                                                         speaker_labels=True,
                                                         model=model,
                                                         inactivity_timeout=-1).get_result()

        return asr_response['results']


# Example usage
if __name__ == "__main__":
    load_dotenv()

    WATSON_API_KEY = os.getenv("WATSON_ASR_API_KEY")
    WATSON_ASR_URL = os.getenv("WATSON_ASR_URL")

    if not WATSON_API_KEY or not WATSON_ASR_URL:
        raise ValueError("Environment variables not set")
    local_wav_filename = '../audio/medium-1.wav'

    # Initialize the BatchASR object with your credentials
    try:
        asr = BatchASR(WATSON_API_KEY, WATSON_ASR_URL)
        transcript_json = asr.recognize_audio(local_wav_filename)
        transcripts = [result['alternatives'][0]['transcript'] for result in transcript_json]
        transcript = " ".join(x for x in transcripts)
        print(transcript)
    except ValueError as ve:
        print("Initialization error: " + str(ve))
    except ApiException as ex:
        print(f"Method failed with status code {ex.code}: {ex.message}")
