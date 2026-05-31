import os
import sys
import wave

# Ensure backend root is on the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.speech_liveness.speech_to_text import speech_transcriber

def generate_silent_wav(file_path: str):
    # 1 second of 16kHz 16-bit mono silence
    sample_rate = 16000
    num_frames = sample_rate
    channels = 1
    sampwidth = 2
    
    with wave.open(file_path, "wb") as wav_file:
        wav_file.setnchannels(channels)
        wav_file.setsampwidth(sampwidth)
        wav_file.setframerate(sample_rate)
        # Write silence (all zeros)
        wav_file.writeframes(b"\x00" * (num_frames * sampwidth * channels))

def test_transcribe():
    temp_wav = "test_silence.wav"
    generate_silent_wav(temp_wav)
    print("Created silent wav file.")
    try:
        print("Calling transcribe...")
        result = speech_transcriber.transcribe(temp_wav)
        print("Transcription finished successfully! Result:", result)
    except Exception as e:
        print("Transcription failed with outer exception:", e)
        import traceback
        traceback.print_exc()
    finally:
        if os.path.exists(temp_wav):
            os.remove(temp_wav)

if __name__ == "__main__":
    test_transcribe()
