"""WAV file ingestion and channel extraction."""
import os
import soundfile as sf
import numpy as np
from datetime import datetime
from sqlalchemy.orm import Session
from .models import Sonobuoy
from .database import WAV_DIR


def ingest_wav(file_path: str, sonobuoy_id: str, db: Session) -> dict:
    """Ingest a multi-channel WAV file and store metadata."""
    info = sf.info(file_path)
    data, sr = sf.read(file_path, dtype="float32")

    if data.ndim == 1:
        data = data.reshape(-1, 1)

    num_channels = data.shape[1]
    duration = data.shape[0] / sr

    dest = os.path.join(WAV_DIR, f"{sonobuoy_id}.wav")
    if os.path.abspath(file_path) != os.path.abspath(dest):
        sf.write(dest, data, sr, subtype="PCM_16")

    sb = db.query(Sonobuoy).filter(Sonobuoy.id == sonobuoy_id).first()
    if sb:
        sb.number_of_channels = num_channels
        sb.sample_rate = sr
        sb.recording_duration = duration
        sb.wav_file = dest
    db.commit()

    return {
        "sonobuoyId": sonobuoy_id,
        "channels": num_channels,
        "sampleRate": sr,
        "duration": round(duration, 2),
        "filePath": dest,
    }


def read_channel(sonobuoy_id: str, channel: int, start_time: float = 0,
                 end_time: float | None = None) -> tuple[np.ndarray, int]:
    """Read a single channel from a sonobuoy WAV file."""
    path = os.path.join(WAV_DIR, f"{sonobuoy_id}.wav")
    data, sr = sf.read(path, dtype="float32")
    if data.ndim == 1:
        data = data.reshape(-1, 1)

    ch_data = data[:, channel]

    start_sample = int(start_time * sr)
    end_sample = int(end_time * sr) if end_time else len(ch_data)
    start_sample = max(0, min(start_sample, len(ch_data)))
    end_sample = max(start_sample, min(end_sample, len(ch_data)))

    return ch_data[start_sample:end_sample], sr


def read_all_channels(sonobuoy_id: str, start_time: float = 0,
                      end_time: float | None = None) -> tuple[np.ndarray, int]:
    """Read all channels from a sonobuoy WAV file."""
    path = os.path.join(WAV_DIR, f"{sonobuoy_id}.wav")
    data, sr = sf.read(path, dtype="float32")
    if data.ndim == 1:
        data = data.reshape(-1, 1)

    start_sample = int(start_time * sr)
    end_sample = int(end_time * sr) if end_time else data.shape[0]
    start_sample = max(0, min(start_sample, data.shape[0]))
    end_sample = max(start_sample, min(end_sample, data.shape[0]))

    return data[start_sample:end_sample], sr
