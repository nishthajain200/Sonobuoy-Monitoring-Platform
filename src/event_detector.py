import pandas as pd
import numpy as np

def detect_events(data, sample_rate, threshold=None):
    """
    Detect acoustic events based on per-window RMS threshold.

    Parameters
    ----------
    threshold : float or None
        If None or 0.0, defaults to mean_rms + 1*std_rms of all windows.
    """
    from src.feature_extractor import extract_features

    df = extract_features(data, sample_rate, 1.0, 50)  # 1 sec windows, 50% overlap

    if df.empty:
        return pd.DataFrame(columns=["event_id", "start_time_sec", "end_time_sec",
                                     "dominant_frequency_hz", "rms", "confidence"])

    mean_rms = df['rms'].mean()
    std_rms = df['rms'].std()
    auto_threshold = mean_rms + std_rms

    # Use auto threshold when slider is at default (0.0) or no explicit value
    if threshold is None or threshold == 0.0:
        effective_threshold = auto_threshold
    else:
        effective_threshold = threshold

    max_rms = df['rms'].max()

    events = []
    event_id = 0
    for _, row in df.iterrows():
        if row['rms'] > effective_threshold:
            # Confidence: normalized distance above threshold, capped at 1.0
            range_above = max_rms - effective_threshold if max_rms > effective_threshold else 1e-9
            confidence = round(float(min((row['rms'] - effective_threshold) / range_above, 1.0)), 4)
            events.append({
                "event_id": event_id,
                "start_time_sec": round(float(row['start_time_sec']), 4),
                "end_time_sec": round(float(row['end_time_sec']), 4),
                "dominant_frequency_hz": round(float(row['dominant_frequency_hz']), 2),
                "rms": round(float(row['rms']), 6),
                "confidence": confidence
            })
            event_id += 1

    return pd.DataFrame(events)