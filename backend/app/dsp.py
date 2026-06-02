"""DSP utilities: FFT and STFT/LOFARgram computation."""
import numpy as np
from scipy.signal import stft, find_peaks


def compute_fft(signal: np.ndarray, sr: int) -> dict:
    """Compute FFT of a signal, return frequencies and magnitudes."""
    n = len(signal)
    fft_vals = np.fft.rfft(signal)
    magnitudes = np.abs(fft_vals) * 2.0 / n
    frequencies = np.fft.rfftfreq(n, d=1.0 / sr)

    # Find peaks
    peak_indices, properties = find_peaks(magnitudes, height=np.max(magnitudes) * 0.05,
                                          distance=int(sr / 500))
    peaks = [{"frequency": round(float(frequencies[i]), 2),
              "amplitude": round(float(magnitudes[i]), 6)} for i in peak_indices]
    peaks.sort(key=lambda p: p["amplitude"], reverse=True)

    # Downsample for transport (max 4000 points)
    max_pts = 4000
    if len(frequencies) > max_pts:
        step = len(frequencies) // max_pts
        freq_out = frequencies[::step].tolist()
        mag_out = magnitudes[::step].tolist()
    else:
        freq_out = frequencies.tolist()
        mag_out = magnitudes.tolist()

    return {
        "frequencies": freq_out,
        "magnitudes": mag_out,
        "peaks": peaks[:30],
        "sampleRate": sr,
    }


def compute_spectrogram(signal: np.ndarray, sr: int,
                        nperseg: int = 1024, noverlap: int = 768,
                        freq_min: float = 0, freq_max: float = 250) -> dict:
    """Compute STFT-based spectrogram / LOFARgram."""
    f, t, Zxx = stft(signal, fs=sr, nperseg=nperseg, noverlap=noverlap)
    magnitude = np.abs(Zxx)

    # Filter frequency range
    freq_mask = (f >= freq_min) & (f <= freq_max)
    f_filtered = f[freq_mask]
    magnitude_filtered = magnitude[freq_mask, :]

    # Convert to dB
    mag_db = 20 * np.log10(magnitude_filtered + 1e-10)

    # Downsample time axis if too large
    max_time_pts = 500
    if len(t) > max_time_pts:
        step = len(t) // max_time_pts
        t = t[::step]
        mag_db = mag_db[:, ::step]

    return {
        "times": t.tolist(),
        "frequencies": f_filtered.tolist(),
        "magnitudes": mag_db.tolist(),
        "sampleRate": sr,
    }
