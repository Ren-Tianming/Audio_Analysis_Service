from app.audio.waveform import get_waveform
from app.audio.spectrogram import get_spectrogram
from app.audio.bpm import calculate_bpm
from app.audio.key import calculate_key

def analyze_audio(path: str):
    return {
        "bpm": calculate_bpm(path),
        "key": calculate_key(path),
        "waveform": get_waveform(path),
        "spectrogram": get_spectrogram(path)
    }
