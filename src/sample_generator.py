import numpy as np
from scipy.io import wavfile
import os
import json


def _vessel_signal(t, shaft_hz, blade_count, machinery_hz_list, amplitude=0.35):
    """
    Synthesise a vessel acoustic signature with shaft harmonics,
    blade-rate harmonics, and machinery tones.
    """
    sig = np.zeros_like(t)
    # Shaft-rate harmonics (up to 5th)
    for h in range(1, 6):
        sig += (amplitude / h) * np.sin(2 * np.pi * shaft_hz * h * t)
    # Blade-rate harmonics (up to 4th)
    blade_hz = shaft_hz * blade_count
    for h in range(1, 5):
        sig += (amplitude * 0.75 / h) * np.sin(2 * np.pi * blade_hz * h * t)
    # Machinery / line tones
    for mf in machinery_hz_list:
        sig += amplitude * 0.4 * np.sin(2 * np.pi * mf * t)
    return sig


def generate_sample_data():
    """
    Generate three synthetic sonobuoy WAV files that showcase all
    analysis features (waveform, FFT, LOFARgram, harmonics, LOFAR correlation,
    bearing, multi-buoy).

    Files written to sample_data/ :
      vessel_merchant_mono.wav    – Surface Merchant Type-A (matches VES-001 in DB)
      vessel_merchant_stereo.wav  – Same signal, stereo with 1 ms TDOA for bearing demo
      multi_vessel_scenario.wav   – Merchant + Warship overlapping (matches VES-001 & VES-002)
      metadata.json               – DIFAR sonobuoy metadata for the merchant file
    """
    sample_rate = 8000   # 8 kHz — typical sonobuoy recording rate
    duration    = 30     # 30 s for a good LOFARgram and feature extraction
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)

    rng = np.random.default_rng(42)

    # ── Vessel A — Surface Merchant Type-A (VES-001 in DB) ───────────────────
    # shaft=5 Hz, blades=4, blade_rate=20 Hz, machinery=[120, 240] Hz
    vessel_a = _vessel_signal(t, shaft_hz=5.0, blade_count=4,
                              machinery_hz_list=[120.0, 240.0], amplitude=0.40)

    # Broadband ocean noise
    noise = 0.04 * rng.standard_normal(len(t))

    # Transient acoustic event at t = 12–14 s (e.g. active sonar ping echo)
    ev_s = int(12 * sample_rate)
    ev_e = int(14 * sample_rate)
    vessel_a[ev_s:ev_e] += 0.35 * np.sin(2 * np.pi * 300 * t[ev_s:ev_e])

    mono_a = vessel_a + noise
    mono_a = mono_a / np.max(np.abs(mono_a)) * 0.80

    # ── Vessel B — Surface Warship Type-B (VES-002 in DB) ────────────────────
    # shaft=8 Hz, blades=5, blade_rate=40 Hz, machinery=[400] Hz
    vessel_b = _vessel_signal(t, shaft_hz=8.0, blade_count=5,
                              machinery_hz_list=[400.0], amplitude=0.25)

    # ── File 1: Mono merchant ─────────────────────────────────────────────────
    os.makedirs("sample_data", exist_ok=True)
    wavfile.write(
        "sample_data/vessel_merchant_mono.wav",
        sample_rate,
        (mono_a * 32767).astype(np.int16)
    )

    # ── File 2: Stereo merchant (1 ms TDOA for bearing demo) ─────────────────
    stereo = np.zeros((len(t), 2))
    delay_samples = int(0.001 * sample_rate)   # 1 ms → bearing ~90° for d=0.75 m
    stereo[:, 0] = mono_a
    stereo[delay_samples:, 1] = mono_a[:-delay_samples]
    wavfile.write(
        "sample_data/vessel_merchant_stereo.wav",
        sample_rate,
        (stereo * 32767).astype(np.int16)
    )

    # ── File 3: Multi-vessel (Merchant + Warship) ─────────────────────────────
    multi = vessel_a + vessel_b + noise
    multi = multi / np.max(np.abs(multi)) * 0.80
    wavfile.write(
        "sample_data/multi_vessel_scenario.wav",
        sample_rate,
        (multi * 32767).astype(np.int16)
    )

    # ── Metadata JSON ─────────────────────────────────────────────────────────
    metadata = {
        "recording_id":    "REC-DISC14-001",
        "buoy_id":         "SB-DISC14-01",
        "channel":         1,
        "sample_rate_hz":  sample_rate,
        "bit_depth":       16,
        "start_time_utc":  "2026-05-26T10:00:00Z",
        "sensor_type":     "DIFAR",
        "deployment_lat":  12.50,
        "deployment_lon":  76.30,
        "depth_m":         30,
        "analyst":         "AUTO",
        "mission":         "P8I-DISC14-DEMO",
        "notes":           "Synthetic Surface Merchant Type-A signature — matches VES-001 in LOFAR DB"
    }
    with open("sample_data/metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)