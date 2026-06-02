import matplotlib.pyplot as plt
from scipy.signal import spectrogram
import numpy as np
import os

def generate_lofargram(data, sample_rate, max_freq, window_size, overlap):
    """
    Generate LOFARgram (spectrogram) and return figure.
    Overlap must be less than window_size; it is clamped automatically.
    """
    if data.ndim > 1:
        mono = np.mean(data, axis=1)
    else:
        mono = data

    # Ensure overlap is strictly less than window_size
    overlap = min(overlap, window_size - 1)

    f, t, Sxx = spectrogram(mono, fs=sample_rate, nperseg=window_size, noverlap=overlap)
    Sxx_db = 10 * np.log10(Sxx + 1e-10)  # avoid log(0)

    # Limit to max_freq
    idx = f <= max_freq
    f = f[idx]
    Sxx_db = Sxx_db[idx]

    fig, ax = plt.subplots(figsize=(10, 6))
    mesh = ax.pcolormesh(t, f, Sxx_db, shading='gouraud', cmap='inferno')
    ax.set_ylabel('Frequency [Hz]')
    ax.set_xlabel('Time [sec]')
    ax.set_title('LOFARgram')
    fig.colorbar(mesh, ax=ax, label='Magnitude [dB]')

    # Save PNG
    os.makedirs("outputs", exist_ok=True)
    fig.savefig("outputs/lofargram.png", bbox_inches='tight')

    return fig