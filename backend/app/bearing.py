"""Bearing estimation and polar view data."""
import numpy as np
from scipy.signal import correlate as sp_correlate
from sqlalchemy.orm import Session
from .models import BearingResult
from datetime import datetime

# Use at most this many samples for bearing cross-correlation (≈2 s at 48 kHz)
_MAX_SAMPLES = 96000


def _pair_bearing(sig_a: np.ndarray, sig_b: np.ndarray, sr: int,
                  d_spacing: float = 0.5, c_sound: float = 1500.0) -> tuple[float, float]:
    """Return (bearing_degrees, confidence) for a single channel pair."""
    # Truncate to keep computation fast
    n = min(len(sig_a), len(sig_b), _MAX_SAMPLES)
    a, b = sig_a[:n], sig_b[:n]
    corr = sp_correlate(a, b, mode='full', method='fft')
    lag = np.argmax(corr) - (n - 1)
    delay = lag / sr
    sin_val = np.clip(delay * c_sound / d_spacing, -1, 1)
    bearing = float(np.degrees(np.arcsin(sin_val))) % 360
    confidence = round(min(1.0, 0.5 + abs(delay) * 1000), 2)
    return bearing, confidence


def estimate_bearing(signals: list[np.ndarray], sr: int,
                     sonobuoy_id: str, frequency: float,
                     db: Session | None = None,
                     timestamp: datetime | None = None) -> dict:
    """
    Estimate bearing from multi-channel signals using phase difference.
    For POC, uses simplified TDOA-based bearing estimation.
    """
    if len(signals) < 2:
        return {"sonobuoyId": sonobuoy_id, "bearing": 0,
                "confidence": 0, "frequency": frequency}

    # Cross-correlate channels to find time delays
    ref = signals[0]
    delays = []
    for ch_signal in signals[1:]:
        n = min(len(ref), len(ch_signal), _MAX_SAMPLES)
        corr = sp_correlate(ref[:n], ch_signal[:n], mode='full', method='fft')
        lag = np.argmax(corr) - (n - 1)
        delays.append(lag / sr)

    # Convert average delay to bearing angle (simplified model)
    avg_delay = np.mean(delays) if delays else 0
    # Map delay to bearing: assume hydrophone spacing ~0.5m, speed of sound ~1500 m/s
    d_spacing = 0.5
    c_sound = 1500.0
    sin_val = np.clip(avg_delay * c_sound / d_spacing, -1, 1)
    bearing = float(np.degrees(np.arcsin(sin_val))) % 360

    # Confidence based on correlation strength
    confidence = round(min(1.0, 0.5 + abs(avg_delay) * 1000), 2)

    result = {
        "sonobuoyId": sonobuoy_id,
        "bearing": round(bearing, 1),
        "confidence": confidence,
        "frequency": frequency,
    }

    if db:
        br = BearingResult(
            sonobuoy_id=sonobuoy_id,
            bearing=result["bearing"],
            confidence=confidence,
            frequency=frequency,
            timestamp=timestamp or datetime.utcnow(),
        )
        db.add(br)
        db.commit()

    return result


def estimate_bearing_all_channels(signals: list[np.ndarray], sr: int,
                                  sonobuoy_id: str, frequency: float) -> dict:
    """Compute per-channel-pair and combined bearing from all channels."""
    n = len(signals)
    channel_pairs = []
    all_bearings = []
    all_confidences = []

    for i in range(n):
        for j in range(i + 1, n):
            bearing, confidence = _pair_bearing(signals[i], signals[j], sr)
            channel_pairs.append({
                "channelA": i,
                "channelB": j,
                "label": f"Ch {i}–{j}",
                "bearing": round(bearing, 1),
                "confidence": confidence,
                "frequency": frequency,
            })
            all_bearings.append(bearing)
            all_confidences.append(confidence)

    # Weighted average bearing (weighted by confidence)
    if all_confidences and sum(all_confidences) > 0:
        weights = np.array(all_confidences)
        # Circular mean to handle wrap-around at 360
        rad = np.deg2rad(all_bearings)
        avg_bearing = float(np.degrees(np.arctan2(
            np.average(np.sin(rad), weights=weights),
            np.average(np.cos(rad), weights=weights),
        ))) % 360
        avg_confidence = round(float(np.mean(weights)), 2)
    else:
        avg_bearing = 0.0
        avg_confidence = 0.0

    return {
        "sonobuoyId": sonobuoy_id,
        "frequency": frequency,
        "combined": {
            "bearing": round(avg_bearing, 1),
            "confidence": avg_confidence,
            "frequency": frequency,
        },
        "channelPairs": channel_pairs,
        "totalChannels": n,
    }


def get_bearing_data(sonobuoy_id: str, db: Session) -> list[dict]:
    """Get stored bearing results for a sonobuoy."""
    results = db.query(BearingResult).filter(
        BearingResult.sonobuoy_id == sonobuoy_id
    ).all()
    return [{
        "sonobuoyId": r.sonobuoy_id,
        "bearing": r.bearing,
        "confidence": r.confidence,
        "frequency": r.frequency,
        "timestamp": r.timestamp.isoformat() if r.timestamp else None,
    } for r in results]
