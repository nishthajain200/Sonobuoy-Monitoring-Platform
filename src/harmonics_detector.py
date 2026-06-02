"""
Harmonics and Narrowband Discrete Detector
Detects narrowband spectral lines and identifies harmonic series
(shaft rate, blade rate, machinery tones) from acoustic data.
"""
import numpy as np
import pandas as pd
from scipy.fft import fft, fftfreq
from scipy.signal import find_peaks


def detect_narrowband_discretes(data, sample_rate, max_freq=2000,
                                 threshold_db_above_mean=12.0, num_lines=30):
    """
    Detect narrowband discrete frequency lines in the power spectrum.

    Parameters
    ----------
    data                   : numpy array (mono or multi-channel)
    sample_rate            : int, Hz
    max_freq               : upper frequency limit, Hz
    threshold_db_above_mean: minimum dB above mean spectrum level for a peak to qualify
    num_lines              : maximum number of lines to return

    Returns
    -------
    peaks_df   : DataFrame of detected lines (frequency_hz, magnitude_db, magnitude)
    xf_limited : frequency axis array (Hz), limited to max_freq
    mag_db_lim : magnitude axis array (dB), same length
    """
    if data.ndim > 1:
        mono = np.mean(data, axis=1).astype(float)
    else:
        mono = data.astype(float)

    N = len(mono)
    yf = fft(mono)
    xf = fftfreq(N, 1.0 / sample_rate)[:N // 2]
    magnitude = 2.0 / N * np.abs(yf[:N // 2])
    mag_db = 20.0 * np.log10(magnitude + 1e-12)

    # Limit to max_freq
    mask = xf <= max_freq
    xf_l = xf[mask]
    mag_l = magnitude[mask]
    mag_db_l = mag_db[mask]

    if len(xf_l) == 0:
        return pd.DataFrame(), xf_l, mag_db_l

    mean_db = np.mean(mag_db_l)
    min_dist = max(1, int(len(xf_l) / 300))

    peaks, props = find_peaks(
        mag_db_l,
        height=mean_db + threshold_db_above_mean,
        distance=min_dist,
        prominence=3.0,
    )

    if len(peaks) == 0:
        return pd.DataFrame(), xf_l, mag_db_l

    # Sort by magnitude and take top N
    sorted_idx = np.argsort(mag_l[peaks])[::-1][:num_lines]
    top_peaks = peaks[sorted_idx]

    records = []
    for i in top_peaks:
        records.append({
            "frequency_hz":  round(float(xf_l[i]), 3),
            "magnitude_db":  round(float(mag_db_l[i]), 2),
            "magnitude":     round(float(mag_l[i]), 8),
            "db_above_mean": round(float(mag_db_l[i] - mean_db), 2),
        })

    return pd.DataFrame(records), xf_l, mag_db_l


def detect_harmonics(detected_freq_list, min_fundamental=2.0, max_fundamental=200.0,
                     min_harmonics=3, tolerance_ratio=0.05):
    """
    Identify harmonic series within a list of detected frequencies.

    Parameters
    ----------
    detected_freq_list : list of floats (Hz)
    min_fundamental    : lowest candidate fundamental frequency (Hz)
    max_fundamental    : highest candidate fundamental frequency (Hz)
    min_harmonics      : minimum number of harmonics (including fundamental) to qualify
    tolerance_ratio    : fractional tolerance for harmonic matching (e.g. 0.05 = ±5 %)

    Returns
    -------
    list of dicts, each describing a harmonic series
    """
    if len(detected_freq_list) == 0:
        return []

    all_freqs = np.array(sorted(detected_freq_list), dtype=float)
    candidates = all_freqs[(all_freqs >= min_fundamental) & (all_freqs <= max_fundamental)]

    series_list = []
    used = set()

    for idx, f0 in enumerate(candidates):
        if idx in used:
            continue

        series_freqs = [float(f0)]
        series_idxs  = [idx]
        harmonic_n = 2

        while True:
            target = f0 * harmonic_n
            if target > all_freqs.max() * 1.05:
                break
            tol = target * tolerance_ratio
            diffs = np.abs(all_freqs - target)
            if diffs.min() <= tol:
                j = int(np.argmin(diffs))
                series_freqs.append(float(all_freqs[j]))
                series_idxs.append(j)
            harmonic_n += 1
            if harmonic_n > 20:
                break

        if len(series_freqs) >= min_harmonics:
            series_list.append({
                "fundamental_hz":         round(f0, 3),
                "harmonics_count":        len(series_freqs),
                "harmonic_frequencies_hz": [round(f, 2) for f in series_freqs],
                "inferred_type":          _infer_series_type(f0),
            })
            used.update(series_idxs)

    return series_list


def _infer_series_type(fundamental_hz):
    if fundamental_hz < 6:
        return "Shaft Rate"
    elif fundamental_hz < 25:
        return "Blade Rate / Low-freq"
    elif fundamental_hz < 100:
        return "Blade Tone / Mid-freq"
    else:
        return "Machinery / High-freq"
