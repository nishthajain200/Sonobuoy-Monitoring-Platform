"""Harmonic detection engine."""
import numpy as np
from scipy.signal import find_peaks
from datetime import datetime
from sqlalchemy.orm import Session
from .models import Detection


def detect_harmonics(signal: np.ndarray, sr: int, sonobuoy_id: str,
                     channel: int, db: Session | None = None,
                     timestamp: datetime | None = None) -> dict:
    """Detect fundamental frequency and harmonics from a signal."""
    n = len(signal)
    fft_vals = np.fft.rfft(signal)
    magnitudes = np.abs(fft_vals) * 2.0 / n
    frequencies = np.fft.rfftfreq(n, d=1.0 / sr)

    # Focus on low-frequency range (10-500 Hz)
    mask = (frequencies >= 10) & (frequencies <= 500)
    freq_sub = frequencies[mask]
    mag_sub = magnitudes[mask]

    if len(mag_sub) == 0:
        return {"sonobuoyId": sonobuoy_id, "channel": channel,
                "fundamentalFrequency": 0, "harmonics": [], "confidence": 0}

    # Find peaks
    peak_indices, props = find_peaks(mag_sub, height=np.max(mag_sub) * 0.08,
                                     distance=max(1, int(5 * n / sr)))
    if len(peak_indices) == 0:
        return {"sonobuoyId": sonobuoy_id, "channel": channel,
                "fundamentalFrequency": 0, "harmonics": [], "confidence": 0}

    peak_freqs = freq_sub[peak_indices]
    peak_amps = mag_sub[peak_indices]

    # Try candidate fundamentals
    best_fundamental = 0
    best_harmonics = []
    best_score = 0

    for idx in range(min(10, len(peak_freqs))):
        f0_candidate = peak_freqs[idx]
        if f0_candidate < 10:
            continue

        harmonics_found = []
        total_energy = 0

        for h in range(2, 8):
            expected = f0_candidate * h
            tolerance = f0_candidate * 0.05
            matches = np.where(np.abs(peak_freqs - expected) < tolerance)[0]
            if len(matches) > 0:
                best_match = matches[np.argmax(peak_amps[matches])]
                harmonics_found.append(round(float(peak_freqs[best_match])))
                total_energy += peak_amps[best_match]

        score = (len(harmonics_found) / 6.0) * 0.6 + min(1.0, total_energy / np.max(peak_amps)) * 0.4
        if score > best_score:
            best_score = score
            best_fundamental = round(float(f0_candidate))
            best_harmonics = harmonics_found

    confidence = float(round(min(1.0, best_score), 2))

    result = {
        "sonobuoyId": sonobuoy_id,
        "channel": int(channel),
        "fundamentalFrequency": int(best_fundamental),
        "harmonics": [int(h) for h in best_harmonics],
        "confidence": confidence,
    }

    if db and best_fundamental > 0:
        detection = Detection(
            sonobuoy_id=sonobuoy_id,
            channel=int(channel),
            fundamental_frequency=float(best_fundamental),
            harmonics=[int(h) for h in best_harmonics],
            confidence=float(confidence),
            timestamp=timestamp or datetime.utcnow(),
        )
        db.add(detection)
        db.commit()

    return result
