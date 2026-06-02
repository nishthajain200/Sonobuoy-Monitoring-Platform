import matplotlib.pyplot as plt
import numpy as np
from scipy.fft import fft, fftfreq
import os

def generate_fft(data, sample_rate):
    """
    Generate FFT spectrum and return figure and stats.
    """
    if data.ndim > 1:
        mono = np.mean(data, axis=1)
    else:
        mono = data

    N = len(mono)
    yf = fft(mono)
    xf = fftfreq(N, 1 / sample_rate)[:N//2]
    magnitude = 2.0/N * np.abs(yf[:N//2])

    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(xf, magnitude)
    ax.set_xlabel("Frequency (Hz)")
    ax.set_ylabel("Magnitude")
    ax.set_title("FFT Spectrum")

    dominant_freq = float(xf[np.argmax(magnitude)])
    peaks = np.argsort(magnitude)[-5:][::-1]
    top_freqs = [round(float(xf[p]), 2) for p in peaks]

    stats = {
        "dominant_frequency_hz": round(dominant_freq, 2),
        "top_5_frequencies_hz": top_freqs
    }

    # Save PNG
    os.makedirs("outputs", exist_ok=True)
    fig.savefig("outputs/fft.png", bbox_inches='tight')

    return fig, stats