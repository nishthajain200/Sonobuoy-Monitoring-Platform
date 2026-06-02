"""
LOFAR Correlation Engine
Matches a list of detected frequency peaks against all vessel signatures in the DB
and returns ranked match candidates with confidence scores.
"""
import numpy as np
import pandas as pd
from src.lofar_db import init_db, _connect


def correlate_frequencies(detected_peaks, tolerance_hz=2.0, min_match_ratio=0.25):
    """
    Match detected frequency peaks against the LOFAR signature database.

    Parameters
    ----------
    detected_peaks   : list/array of detected frequency values in Hz
    tolerance_hz     : maximum frequency deviation to count as a match (Hz)
    min_match_ratio  : minimum fraction of DB lines that must match to include a result

    Returns
    -------
    DataFrame with match results sorted by confidence_score descending,
    or empty DataFrame if no matches.
    """
    init_db()
    conn = _connect()
    lines_df = pd.read_sql(
        """SELECT fl.*, v.vessel_name, v.vessel_class, v.description, v.shaft_rate_hz, v.blade_count
           FROM frequency_lines fl
           JOIN vessels v ON fl.vessel_id = v.vessel_id""",
        conn
    )
    conn.close()

    if lines_df.empty or len(detected_peaks) == 0:
        return pd.DataFrame()

    detected_arr = np.array(detected_peaks, dtype=float)
    results = []

    for vessel_id, group in lines_df.groupby("vessel_id"):
        vessel_name  = group["vessel_name"].iloc[0]
        vessel_class = group["vessel_class"].iloc[0]
        description  = group["description"].iloc[0]
        shaft_rate   = group["shaft_rate_hz"].iloc[0]
        blade_count  = group["blade_count"].iloc[0]

        db_freqs = group["freq_hz"].values
        db_amps  = group["relative_amplitude"].values

        matched_count  = 0
        matched_freqs  = []
        matched_weight = 0.0

        for j, db_f in enumerate(db_freqs):
            diffs = np.abs(detected_arr - db_f)
            if diffs.min() <= tolerance_hz:
                matched_count += 1
                matched_freqs.append(round(float(db_f), 2))
                matched_weight += float(db_amps[j])

        match_ratio = matched_count / len(db_freqs)
        if match_ratio < min_match_ratio:
            continue

        # Confidence: weighted match vs total possible amplitude weight
        confidence = round(matched_weight / float(db_amps.sum()), 3)

        results.append({
            "vessel_id":             vessel_id,
            "vessel_name":           vessel_name,
            "vessel_class":          vessel_class,
            "description":           description,
            "shaft_rate_hz":         shaft_rate,
            "blade_count":           blade_count,
            "db_lines":              int(len(db_freqs)),
            "matched_lines":         int(matched_count),
            "match_ratio":           round(match_ratio, 3),
            "confidence_score":      confidence,
            "matched_frequencies_hz": matched_freqs,
        })

    if not results:
        return pd.DataFrame()

    return pd.DataFrame(results).sort_values("confidence_score", ascending=False).reset_index(drop=True)
