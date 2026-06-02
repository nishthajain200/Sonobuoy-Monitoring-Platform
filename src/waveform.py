import matplotlib.pyplot as plt
import numpy as np
import os

def generate_waveform(data, sample_rate):
    """
    Generate waveform plot and return figure and stats.
    """
    if data.ndim > 1:
        mono = np.mean(data, axis=1)
    else:
        mono = data

    time = np.arange(len(mono)) / sample_rate
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(time, mono)
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Amplitude")
    ax.set_title("Waveform")

    rms = float(np.sqrt(np.mean(mono**2)))
    peak = float(np.max(np.abs(mono)))
    stats = {
        "duration_sec": round(len(mono) / sample_rate, 4),
        "rms": round(rms, 6),
        "peak_amplitude": round(peak, 6),
        "min_amplitude": round(float(np.min(mono)), 6),
        "max_amplitude": round(float(np.max(mono)), 6)
    }

    # Save PNG
    os.makedirs("outputs", exist_ok=True)
    fig.savefig("outputs/waveform.png", bbox_inches='tight')

    return fig, stats