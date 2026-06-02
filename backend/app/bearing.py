"""Bearing estimation and polar view data."""
import numpy as np
from sqlalchemy.orm import Session
from .models import BearingResult
from datetime import datetime


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
        min_len = min(len(ref), len(ch_signal))
        corr = np.correlate(ref[:min_len], ch_signal[:min_len], mode='full')
        lag = np.argmax(corr) - (min_len - 1)
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
