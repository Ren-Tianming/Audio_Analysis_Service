# pip install llvmlite==0.43.0 numba==0.60.0 librosa
import librosa

def calculate_bpm(audio_path: str) -> float:
    y, sr = librosa.load(audio_path)
    tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
    return float(tempo)
