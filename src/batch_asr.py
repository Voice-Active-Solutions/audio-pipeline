#!/usr/bin/env python3
"""
Multi-provider Batch ASR module.

Supports IBM Watson only for now.
Architecture: Abstract Base Class (ABC) with per-provider subclasses.
"""

import logging
import os
from abc import ABC, abstractmethod

from dotenv import load_dotenv

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Abstract Base Class
# ---------------------------------------------------------------------------

class BaseASR(ABC):
    """
    Abstract base class for all ASR providers.

    Subclasses MUST implement `recognize_audio`. Attempting to instantiate
    a subclass that doesn't will raise TypeError at runtime.

    Shared utilities (file validation, transcript joining) can live here so
    every provider benefits without duplicating code.
    """

    def _validate_file(self, path: str) -> None:
        """Shared pre-flight check used by all providers."""
        if not os.path.exists(path):
            logger.error("Audio file not found: %s", path)
            raise FileNotFoundError(f"Audio file not found: {path}")
        if os.path.getsize(path) == 0:
            logger.error("Audio file is empty: %s", path)
            raise ValueError(f"Audio file is empty: {path}")
        logger.debug("Audio file validated: %s", path)

    @abstractmethod
    def recognize_audio(self, audio_file_path: str, **kwargs) -> str:
        """
        Transcribe an audio file to text.

        Args:
            audio_file_path: Path to the audio file on disk.
            **kwargs: Provider-specific options (model, language, etc.)

        Returns:
            Transcribed text as a single string.
        """
        ...



# ---------------------------------------------------------------------------
# IBM Watson provider
# ---------------------------------------------------------------------------

class IBMWatsonASR(BaseASR):
    """IBM Watson Speech to Text provider."""

    DEFAULT_MODEL = "en-GB_BroadbandModel"
    DEFAULT_CONTENT_TYPE = "audio/wav"

    def __init__(self, api_key: str, service_url: str):
        from ibm_cloud_sdk_core.authenticators import IAMAuthenticator
        from ibm_watson import SpeechToTextV1

        logger.debug("Initialising IBM Watson ASR client")
        authenticator = IAMAuthenticator(api_key)
        self._client = SpeechToTextV1(authenticator=authenticator)
        self._client.set_service_url(service_url)

    def recognize_audio(self, audio_file_path: str, **kwargs) -> str:
        """
        Kwargs:
            content_type (str): MIME type, e.g. 'audio/wav'. Default: 'audio/wav'.
            model (str): Watson model ID. Default: 'en-GB_BroadbandModel'.
        """
        from ibm_watson import ApiException

        self._validate_file(audio_file_path)
        content_type = kwargs.get("content_type", self.DEFAULT_CONTENT_TYPE)
        model = kwargs.get("model", self.DEFAULT_MODEL)
        logger.info("IBM Watson: transcribing '%s' with model '%s'", audio_file_path, model)

        try:
            with open(audio_file_path, "rb") as f:
                response = self._client.recognize(
                    audio=f,
                    content_type=content_type,
                    speaker_labels=True,
                    model=model,
                    inactivity_timeout=-1,
                ).get_result()
        except ApiException as e:
            logger.error("IBM Watson API error (status %s): %s", e.code, e.message)
            raise ValueError("IBM Watson API error") from e

        results = response.get("results", [])
        if not results:
            logger.warning("IBM Watson: no results returned for '%s'", audio_file_path)
            return ""

        transcript = " ".join(
            result["alternatives"][0]["transcript"] for result in results
        )
        logger.info("IBM Watson: transcription complete (%d characters)", len(transcript))
        return transcript


# Example usage
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )

    load_dotenv()

    AUDIO_FILE = "../audio/test1.wav"

    asrInitialised = False
    try:
        asr = IBMWatsonASR(
            api_key=os.getenv("WATSON_ASR_API_KEY"),
            service_url=os.getenv("WATSON_ASR_URL"),
        )
        asrInitialised = True
    except Exception as e:
        logger.error("Failed to initialise IBM Watson client: %s", e)

    if asrInitialised:
        try:
            transcript = asr.recognize_audio(AUDIO_FILE)
            print(transcript)
        except ValueError as e:
            logger.error("Error occurred while processing audio file: %s", e)


