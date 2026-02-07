# pip install llvmlite==0.43.0 numba==0.60.0 librosa
import librosa 
import numpy as np

def get_waveform(audio_path: str):
    y, sr = librosa.load(audio_path)
    return y.tolist(), sr
