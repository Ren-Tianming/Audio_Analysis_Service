# pip install llvmlite==0.43.0 numba==0.60.0 librosa
import librosa
import numpy as np

def get_spectrogram(audio_path: str):
    y, sr = librosa.load(audio_path)
    spec = librosa.stft(y)
    spec_db = librosa.amplitude_to_db(abs(spec))
    return spec_db.tolist()
