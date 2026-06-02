import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import correlate
import os

def generate_bearing_view(data, sample_rate, sensor_spacing, sound_speed, array_heading, bearing_window, rms_threshold):
    """
    Generate polar bearing view for stereo data using cross-correlation per time window.

    Parameters
    ----------
    sensor_spacing    : distance between sensors in metres
    sound_speed       : speed of sound in m/s (use ~1500 for water)
    array_heading     : compass heading of the array in degrees (added to relative bearing)
    bearing_window    : window length in seconds for each bearing estimate
    rms_threshold     : minimum combined-channel RMS to include a window
    """
    if data.ndim < 2 or data.shape[1] < 2:
        raise ValueError("Stereo data required")

    ch1 = data[:, 0]
    ch2 = data[:, 1]

    window_samples = int(bearing_window * sample_rate)
    step = max(window_samples // 2, 1)  # 50% overlap, minimum 1

    # Guard: effective threshold to avoid div-by-zero in confidence
    eff_threshold = rms_threshold if rms_threshold > 1e-9 else 1e-9

    bearings = []
    for start in range(0, len(ch1) - window_samples + 1, step):
        end = start + window_samples
        seg1 = ch1[start:end]
        seg2 = ch2[start:end]

        combined_rms = float(np.sqrt(np.mean((seg1.astype(np.float64)**2 + seg2.astype(np.float64)**2) / 2)))
        if combined_rms < rms_threshold:
            continue

        # Cross-correlation to estimate inter-sensor delay
        corr = correlate(seg1.astype(np.float64), seg2.astype(np.float64), mode='full')
        lags = np.arange(-(len(seg1) - 1), len(seg1))
        delay_samples = int(lags[np.argmax(np.abs(corr))])
        delay_sec = delay_samples / sample_rate

        # Bearing calculation with clipping to valid asin domain
        arg = np.clip(delay_sec * sound_speed / sensor_spacing, -1.0, 1.0)
        bearing_rel = float(np.degrees(np.arcsin(arg)))
        bearing_abs = (bearing_rel + array_heading) % 360

        mid_time = (start + end) / 2 / sample_rate
        confidence = round(float(min(combined_rms / eff_threshold, 1.0)), 4)

        bearings.append({
            "start_time_sec": round(start / sample_rate, 4),
            "end_time_sec": round(end / sample_rate, 4),
            "mid_time_sec": round(mid_time, 4),
            "delay_sec": round(delay_sec, 6),
            "delay_samples": delay_samples,
            "bearing_relative_deg": round(bearing_rel, 2),
            "bearing_absolute_deg": round(bearing_abs, 2),
            "rms": round(combined_rms, 6),
            "confidence": confidence
        })

    df = pd.DataFrame(bearings)

    # Polar plot — angle in radians from north (theta=0 = north, clockwise)
    fig = plt.figure(figsize=(8, 8))
    ax = fig.add_subplot(111, polar=True)
    ax.set_theta_zero_location('N')  # 0 degrees at top (north)
    ax.set_theta_direction(-1)        # clockwise

    if not df.empty:
        angles = np.radians(df['bearing_absolute_deg'].values)
        radii = df['mid_time_sec'].values
        sizes = np.clip(df['rms'].values * 300, 10, 200)
        colors = df['confidence'].values
        sc = ax.scatter(angles, radii, s=sizes, c=colors, cmap='viridis', alpha=0.8, vmin=0, vmax=1)
        fig.colorbar(sc, ax=ax, label='Confidence', shrink=0.6)

    ax.set_title("Bearing View\n(radius = time [s], angle = bearing)", pad=20)

    # Save PNG
    os.makedirs("outputs", exist_ok=True)
    fig.savefig("outputs/bearing.png", bbox_inches='tight')

    return fig, df