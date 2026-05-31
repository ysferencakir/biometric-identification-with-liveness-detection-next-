import logging
import threading
from typing import Tuple, Optional
from config import settings

logger = logging.getLogger(__name__)

class SpeechToTextTranscriber:
    """
    Thread-safe, lazy-loaded wrapper for faster-whisper.
    Loads and runs the Whisper model on the configured device (defaults to CPU for stability).
    """
    def __init__(self, model_size: Optional[str] = None):
        self.model_size = model_size or settings.WHISPER_MODEL_SIZE
        self._model = None
        self._lock = threading.Lock()
        self.current_device = None

    def get_model(self):
        """Loads and returns the WhisperModel instance (thread-safe, lazy-loaded)."""
        if self._model is not None:
            return self._model
            
        with self._lock:
            # Double check inside lock
            if self._model is not None:
                return self._model
                
            # Imports are placed inside the loader to speed up module import times
            from faster_whisper import WhisperModel
            
            device = settings.WHISPER_DEVICE
            compute_type = settings.WHISPER_COMPUTE_TYPE
            
            logger.info("Initializing faster-whisper model '%s' on %s (%s)...", self.model_size, device, compute_type)
            try:
                self._model = WhisperModel(
                    self.model_size, 
                    device=device, 
                    compute_type=compute_type
                )
                self.current_device = device
                logger.info("faster-whisper model '%s' loaded on %s successfully.", self.model_size, device)
            except Exception as e:
                logger.warning(
                    "Failed to initialize faster-whisper on %s: %s. "
                    "Falling back to CPU with int8 quantization.", device, e
                )
                try:
                    self._model = WhisperModel(
                        self.model_size, 
                        device="cpu", 
                        compute_type="int8"
                    )
                    self.current_device = "cpu"
                    logger.info("faster-whisper model '%s' loaded on CPU successfully.", self.model_size)
                except Exception as e2:
                    logger.error("Critical: Failed to load faster-whisper model on CPU: %s", e2)
                    raise e2
            return self._model

    def transcribe(self, file_path: str, initial_prompt: Optional[str] = None) -> str:
        """
        Transcribes the given audio file using the underlying faster-whisper engine.
        Enforces Turkish language ("tr") for optimal accuracy.
        Applies target phrase context via `initial_prompt` to guide and dramatically improve accuracy.
        Handles runtime CUDA failures (like missing cublas DLLs) by falling back to CPU dynamically.
        """
        try:
            model = self.get_model()
            logger.info(
                "Transcribing audio file on %s (prompt: '%s'): %s", 
                self.current_device or "unknown", 
                initial_prompt or "None", 
                file_path
            )
            segments, info = model.transcribe(
                file_path, 
                language="tr", 
                beam_size=5, 
                initial_prompt=initial_prompt
            )
            transcript_parts = []
            for segment in segments:
                transcript_parts.append(segment.text)
            transcript = " ".join(transcript_parts).strip()
            logger.info("Transcription finished. Result: '%s'", transcript)
            return transcript
        except Exception as e:
            # If the model was running on CUDA, we immediately attempt to fall back to CPU
            if self.current_device == "cuda":
                logger.warning(
                    "Transcription failed on CUDA: %s. Re-initializing model on CPU as a fallback...", e
                )
                with self._lock:
                    from faster_whisper import WhisperModel
                    try:
                        self._model = WhisperModel(
                            self.model_size,
                            device="cpu",
                            compute_type="int8"
                        )
                        self.current_device = "cpu"
                        logger.info("faster-whisper model '%s' successfully re-loaded on CPU.", self.model_size)
                        
                        # Retry transcription on CPU
                        logger.info("Retrying transcription on CPU: %s", file_path)
                        segments, info = self._model.transcribe(
                            file_path, 
                            language="tr", 
                            beam_size=5, 
                            initial_prompt=initial_prompt
                        )
                        transcript_parts = []
                        for segment in segments:
                            transcript_parts.append(segment.text)
                        transcript = " ".join(transcript_parts).strip()
                        logger.info("Transcription succeeded on CPU fallback. Result: '%s'", transcript)
                        return transcript
                    except Exception as e_cpu:
                        logger.error("Critical: Failed to transcribe even on CPU fallback: %s", e_cpu)
                        raise e_cpu
            else:
                logger.error("Transcription failed on CPU: %s", e)
                raise e

# Global transcriber instance (reads configuration model size dynamically from central settings)
speech_transcriber = SpeechToTextTranscriber()
