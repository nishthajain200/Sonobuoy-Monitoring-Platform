import pandas as pd
import numpy as np
from scipy.fft import fft, fftfreq

def extract_features(data, sample_rate, window_size_sec, overlap_percent):
    """
    Extract features from signal windows.
    """
    if data.ndim > 1:
        mono = np.mean(data, axis=1)
    else:
        mono = data

    window_samples = int(window_size_sec * sample_rate)
    overlap_samples = int(window_samples * overlap_percent / 100)
    step = window_samples - overlap_samples

    features = []
    for start in range(0, len(mono) - window_samples + 1, step):
        end = start + window_samples
        window = mono[start:end]

        start_time = start / sample_rate
        end_time = end / sample_rate

        rms = np.sqrt(np.mean(window**2))
        peak = np.max(np.abs(window))

        # Dominant frequency
        yf = fft(window)
        xf = fftfreq(len(window), 1 / sample_rate)
        idx = xf >= 0
        xf = xf[idx]
        magnitude = np.abs(yf[idx])
        dom_freq = xf[np.argmax(magnitude)]

        # Band energies
        def band_energy(low, high):
            idx = (xf >= low) & (xf <= high)
            return np.sum(magnitude[idx]**2)

        energy_20_200 = band_energy(20, 200)
        energy_200_1000 = band_energy(200, 1000)
        energy_1000_2000 = band_energy(1000, 2000)

        features.append({
            "start_time_sec": start_time,
            "end_time_sec": end_time,
            "rms": rms,
            "peak_amplitude": peak,
            "dominant_frequency_hz": dom_freq,
            "band_energy_20_200_hz": energy_20_200,
            "band_energy_200_1000_hz": energy_200_1000,
            "band_energy_1000_2000_hz": energy_1000_2000
        })

    return pd.DataFrame(features)