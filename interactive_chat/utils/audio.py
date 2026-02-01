"""Utility functions for audio processing."""
import numpy as np


def float32_to_int16(audio: np.ndarray) -> np.ndarray:
    """Convert float32 audio to int16."""
    audio = np.clip(audio, -1.0, 1.0)
    return (audio * 32767).astype(np.int16)


def int16_to_float32(audio: np.ndarray) -> np.ndarray:
    """Convert int16 audio to float32."""
    return audio.astype(np.float32) / 32767.0


def chunk_audio(audio: np.ndarray, chunk_size: int, sample_rate: int) -> list:
    """Split audio into chunks by time duration."""
    samples_per_chunk = int(sample_rate * chunk_size / 1000)
    return [
        audio[i:i + samples_per_chunk]
        for i in range(0, len(audio), samples_per_chunk)
    ]
