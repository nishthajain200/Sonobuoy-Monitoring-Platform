"""
Multi-Buoy Analysis Module
Processes acoustic data from multiple sonobuoys simultaneously:
  - Time Difference of Arrival (TDOA) computation between all buoy pairs
  - Common frequency detection across buoys
  - Cross-correlation matrix
  - Simplified source localisation estimate
"""
import numpy as np
import pandas as pd
from scipy.signal import correlate
from scipy.fft import fft, fftfreq


def _to_mono_float(data):
    if data.ndim > 1:
        return np.mean(data, axis=1).astype(float)
    return data.astype(float)


def compute_tdoa(signal1, signal2, sample_rate):
    """
    Estimate the Time Difference of Arrival (TDOA) between two signals
    using generalised cross-correlation.

    Returns
    -------
    tdoa_sec     : time delay in seconds (positive = signal2 lags signal1)
    tdoa_samples : corresponding sample lag
    corr_peak    : normalised correlation peak (0-1)
    """
    s1 = _to_mono_float(signal1)
    s2 = _to_mono_float(signal2)

    # Align lengths
    n = min(len(s1), len(s2))
    s1, s2 = s1[:n], s2[:n]

    corr = correlate(s1, s2, mode='full')
    lags = np.arange(-(n - 1), n)

    peak_idx     = int(np.argmax(np.abs(corr)))
    tdoa_samples = int(lags[peak_idx])
    tdoa_sec     = tdoa_samples / sample_rate

    # Normalise peak
    norm = np.sqrt(np.sum(s1 ** 2) * np.sum(s2 ** 2))
    corr_peak = float(np.abs(corr[peak_idx]) / norm) if norm > 0 else 0.0

    return tdoa_sec, tdoa_samples, min(corr_peak, 1.0)


def detect_common_frequencies(signals_data, sample_rates, max_freq=2000.0, top_n=20, tol_hz=2.0):
    """
    Find frequency peaks that appear in ALL supplied buoy signals.

    Returns a sorted list of common frequencies (Hz).
    """
    peak_sets = []
    for data, sr in zip(signals_data, sample_rates):
        mono = _to_mono_float(data)
        N = len(mono)
        yf = fft(mono)
        xf = fftfreq(N, 1.0 / sr)[:N // 2]
        mag = 2.0 / N * np.abs(yf[:N // 2])

        mask = xf <= max_freq
        xf_l = xf[mask]
        mag_l = mag[mask]

        top_idx = np.argsort(mag_l)[-top_n:]
        peak_sets.append({round(float(xf_l[i]), 1) for i in top_idx})

    if not peak_sets:
        return []

    common = peak_sets[0]
    for other in peak_sets[1:]:
        new_common = set()
        for f1 in common:
            for f2 in other:
                if abs(f1 - f2) <= tol_hz:
                    new_common.add(f1)
                    break
        common = new_common

    return sorted(list(common))


def build_correlation_matrix(monos):
    """Return normalised cross-correlation peak matrix (n x n)."""
    n = len(monos)
    mat = np.zeros((n, n))
    for i in range(n):
        mat[i][i] = 1.0
        for j in range(i + 1, n):
            length = min(len(monos[i]), len(monos[j]))
            s1, s2 = monos[i][:length], monos[j][:length]
            corr = correlate(s1, s2, mode='full')
            norm = np.sqrt(np.sum(s1 ** 2) * np.sum(s2 ** 2))
            peak = float(np.max(np.abs(corr)) / norm) if norm > 0 else 0.0
            mat[i][j] = mat[j][i] = min(peak, 1.0)
    return mat


def analyze_multi_buoy(buoy_data_list, labels=None):
    """
    Full multi-buoy analysis pipeline.

    Parameters
    ----------
    buoy_data_list : list of (data_array, sample_rate) tuples (min 2 items)
    labels         : optional list of buoy name strings

    Returns
    -------
    dict with keys:
        labels, tdoa_df, correlation_matrix, common_frequencies_hz, num_buoys
    """
    n = len(buoy_data_list)
    if n < 2:
        return {"error": "Need at least 2 buoys for multi-buoy analysis."}

    if labels is None:
        labels = [f"Buoy-{i + 1}" for i in range(n)]

    monos = [_to_mono_float(d) for d, _ in buoy_data_list]
    sample_rates = [sr for _, sr in buoy_data_list]

    # TDOA for every pair
    tdoa_rows = []
    for i in range(n):
        for j in range(i + 1, n):
            sr = sample_rates[i]
            tdoa_sec, tdoa_samp, corr_peak = compute_tdoa(monos[i], monos[j], sr)
            range_diff_m = round(abs(tdoa_sec) * 1500.0, 2)   # water sound speed ~1500 m/s
            tdoa_rows.append({
                "buoy_pair":            f"{labels[i]}  ↔  {labels[j]}",
                "tdoa_sec":             round(tdoa_sec, 6),
                "tdoa_samples":         tdoa_samp,
                "implied_range_diff_m": range_diff_m,
                "correlation_peak":     round(corr_peak, 4),
                "signal_lead":          labels[i] if tdoa_sec >= 0 else labels[j],
            })

    # Cross-correlation matrix
    corr_mat = build_correlation_matrix(monos)

    # Common frequencies
    common_freqs = detect_common_frequencies(
        [d for d, _ in buoy_data_list],
        sample_rates
    )

    return {
        "labels":                labels,
        "tdoa_df":               pd.DataFrame(tdoa_rows),
        "correlation_matrix":    corr_mat,
        "common_frequencies_hz": common_freqs,
        "num_buoys":             n,
    }
