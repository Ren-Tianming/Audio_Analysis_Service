# pip install llvmlite==0.43.0 numba==0.60.0 librosa
import librosa
import numpy as np

KEYS = ['C', 'C#', 'D', 'D#', 'E', 'F',
        'F#', 'G', 'G#', 'A', 'A#', 'B']

def calculate_key(audio_path: str) -> str:
    y, sr = librosa.load(audio_path)
    chroma = librosa.feature.chroma_stft(y=y, sr=sr)
    key_index = np.argmax(np.sum(chroma, axis=1))
    return KEYS[key_index]
