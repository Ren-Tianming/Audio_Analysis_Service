import numpy as np


def get_waveform(y: np.ndarray, max_points: int = 1200) -> list[float]:
    """描画用に波形を縮約して返す。"""
    if len(y) <= max_points:
        return np.round(y, 5).tolist()
    frames = np.array_split(y, max_points)
    return [round(float(np.mean(frame)), 5) for frame in frames]
