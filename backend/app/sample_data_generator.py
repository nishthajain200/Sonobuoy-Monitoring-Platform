"""Synthetic sample data generator – Bay of Bengal submarine detection scenario.

Scenario: 25 May 2026, Mandarmani coast (West Bengal), Bay of Bengal.
Eight AN/SSQ-53F DIFAR sonobuoys deployed in a barrier/search pattern
15–25 km offshore to detect a diesel-electric submarine transiting the area.

Estimated hostile submarine position: 21.51°N, 87.76°E
Platform signature: Kilo-class (Project 877EKM) diesel-electric submarine
  - Diesel-generator tonal: 50 Hz fundamental
  - Blade-rate frequency: 8 Hz (7-blade fixed-pitch propeller ≈ 1.14 rps)
  - Harmonics: 100 Hz, 150 Hz, 200 Hz (engine harmonics)
  - Auxiliary machinery tonal: ~120 Hz
"""
import os
import json
import csv
import math
import numpy as np
import soundfile as sf
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from .database import WAV_DIR, SessionLocal, init_db
from .models import (Sonobuoy, Detection, BearingResult, LofarSignature,
                     MissionEvent, LofarMatch, Correlation)
from .lofar_matching import seed_lofar_database

# ── Submarine target definition ──────────────────────────────────────────────
SUB_POSITION = (21.510, 87.760)   # estimated hostile position

# ── Sonobuoy deployment pattern: barrier arc, Mandarmani offshore ────────────
#    Bearings are computed towards SUB_POSITION
SONOBUOYS = [
    {"id": "SB001", "name": "Barrier North-West",  "lat": 21.550, "lon": 87.600},
    {"id": "SB002", "name": "Barrier West",         "lat": 21.530, "lon": 87.680},
    {"id": "SB003", "name": "Barrier Centre",       "lat": 21.500, "lon": 87.750},
    {"id": "SB004", "name": "Barrier East",          "lat": 21.520, "lon": 87.820},
    {"id": "SB005", "name": "Barrier South-East",   "lat": 21.550, "lon": 87.900},
    {"id": "SB006", "name": "Search South-West",    "lat": 21.480, "lon": 87.650},
    {"id": "SB007", "name": "Search South",          "lat": 21.460, "lon": 87.780},
    {"id": "SB008", "name": "Datum Buoy",            "lat": 21.505, "lon": 87.770},
]

# ── Acoustic signature – Kilo-class diesel-electric ──────────────────────────
#    All buoys detect the SAME submarine → same fundamental frequency
FUND_FREQ = 50          # Hz – diesel-generator main tonal
HARMONICS = [100, 150, 200]  # 2nd, 3rd, 4th harmonics
BLADE_RATE = 8          # Hz – propeller blade rate (subtle)
AUX_FREQ = 120          # Hz – auxiliary machinery

NUM_CHANNELS = 4
SAMPLE_RATE = 48000
DURATION = 30           # seconds per buoy recording
DEFAULT_BASE_TIME = datetime(2026, 5, 25, 4, 12, 0)  # 25 May 2026, 04:12 IST


def _bearing_to_target(lat1: float, lon1: float) -> float:
    """Compute bearing (degrees, clockwise from North) from buoy to submarine."""
    lat2, lon2 = SUB_POSITION
    d_lat = lat2 - lat1
    d_lon = (lon2 - lon1) * math.cos(math.radians(lat1))
    bearing = math.degrees(math.atan2(d_lon, d_lat)) % 360
    return round(bearing, 1)


def _distance_km(lat1: float, lon1: float) -> float:
    """Approx distance in km from buoy to submarine (Haversine)."""
    lat2, lon2 = SUB_POSITION
    R = 6371
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = (math.sin(d_lat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(d_lon / 2) ** 2)
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def generate_wav(sb: dict, sr: int = SAMPLE_RATE, duration: float = DURATION):
    """Generate a 4-channel WAV simulating passive sonar reception.

    Closer buoys receive a louder signal; farther buoys receive more noise.
    Channel delays simulate DIFAR hydrophone array geometry.
    """
    n_samples = int(sr * duration)
    t = np.linspace(0, duration, n_samples, endpoint=False)
    rng = np.random.default_rng(hash(sb["id"]) & 0xFFFFFFFF)

    dist = _distance_km(sb["lat"], sb["lon"])
    # Signal-to-noise ratio decreases with distance (cylindrical spreading)
    snr_linear = max(0.08, 1.0 / (1.0 + dist * 0.6))  # closer → louder

    channels = []
    for ch in range(NUM_CHANNELS):
        signal = np.zeros(n_samples, dtype=np.float64)

        # ── Submarine tonals ─────────────────────────────────────────────
        delay = ch * 0.00015  # DIFAR inter-element delay (~0.15 ms)
        phase_jitter = rng.uniform(-0.5, 0.5)

        # Diesel-generator fundamental
        amp_fund = snr_linear * (0.35 + 0.05 * ch)
        signal += amp_fund * np.sin(2 * np.pi * FUND_FREQ * (t - delay) + phase_jitter)

        # Engine harmonics (decreasing amplitude)
        for i, h in enumerate(HARMONICS):
            h_amp = amp_fund * (0.45 / (i + 1))
            signal += h_amp * np.sin(2 * np.pi * h * (t - delay) + rng.uniform(-0.3, 0.3))

        # Blade-rate tonal (low-level)
        signal += snr_linear * 0.12 * np.sin(2 * np.pi * BLADE_RATE * (t - delay))

        # Auxiliary machinery
        signal += snr_linear * 0.15 * np.sin(2 * np.pi * AUX_FREQ * (t - delay) + rng.uniform(0, 1))

        # ── Slow amplitude modulation (sub moves, scintillation) ─────────
        am = 1.0 + 0.10 * np.sin(2 * np.pi * 0.08 * t + rng.uniform(0, 6.28))
        signal *= am

        # ── Ocean ambient noise ──────────────────────────────────────────
        # Low-freq ocean rumble (Knudsen spectrum approximation)
        ocean_noise = rng.normal(0, 0.06, n_samples)
        # band-limit: weight low frequencies
        from scipy.signal import butter, sosfilt
        sos_lp = butter(4, 200, btype='low', fs=sr, output='sos')
        ocean_noise = sosfilt(sos_lp, ocean_noise).astype(np.float64)
        signal += ocean_noise

        # Broadband white noise (self-noise, flow noise)
        signal += rng.normal(0, 0.015, n_samples)

        # ── Occasional biological transient (snapping shrimp click) ──────
        n_clicks = rng.integers(2, 8)
        for _ in range(n_clicks):
            click_pos = rng.integers(0, n_samples - 500)
            click = rng.normal(0, 0.25, 200) * np.exp(-np.linspace(0, 6, 200))
            signal[click_pos:click_pos + 200] += click

        # Normalize
        signal = signal / (np.max(np.abs(signal)) + 1e-8) * 0.85
        channels.append(signal.astype(np.float32))

    multi = np.column_stack(channels)
    path = os.path.join(WAV_DIR, f"{sb['id']}.wav")
    sf.write(path, multi, sr, subtype="PCM_16")
    return path


def generate_all_data(from_datetime: datetime = None, to_datetime: datetime = None):
    """Generate all sample data: WAVs, metadata, and database records.
    
    Args:
        from_datetime: Start of the time range for generated data.
        to_datetime: End of the time range for generated data.
    """
    init_db()
    db = SessionLocal()

    base_time = from_datetime or DEFAULT_BASE_TIME
    end_time = to_datetime or (base_time + timedelta(minutes=15))
    total_span = (end_time - base_time).total_seconds()
    # Aircraft drops sonobuoys in rapid succession (~15s apart)
    sb_interval = 15  # seconds between each buoy drop
    # Each buoy records from deployment until mission end
    mission_duration = max(30, total_span - sb_interval * (len(SONOBUOYS) - 1))

    try:
        # Clear all existing data for a clean regeneration
        db.query(MissionEvent).delete()
        db.query(Correlation).delete()
        db.query(LofarMatch).delete()
        db.query(BearingResult).delete()
        db.query(Detection).delete()
        db.query(Sonobuoy).delete()
        db.commit()

        # Seed LOFAR database (clear old signatures first)
        db.query(LofarSignature).delete()
        db.commit()
        seed_lofar_database(db)

        data_dir = os.path.dirname(WAV_DIR)

        for i, sb_def in enumerate(SONOBUOYS):
            deploy_time = base_time + timedelta(seconds=i * sb_interval)

            # Compute bearing and distance to submarine
            bearing = _bearing_to_target(sb_def["lat"], sb_def["lon"])
            dist = _distance_km(sb_def["lat"], sb_def["lon"])
            # Confidence scales inversely with distance
            base_conf = max(0.55, min(0.97, 1.0 - dist * 0.04))

            # Compute per-buoy recording duration (from deploy to mission end)
            buoy_duration = max(30, total_span - i * sb_interval)

            # Create sonobuoy record
            sb = Sonobuoy(
                id=sb_def["id"],
                name=sb_def["name"],
                latitude=sb_def["lat"],
                longitude=sb_def["lon"],
                deployment_time=deploy_time,
                number_of_channels=NUM_CHANNELS,
                sample_rate=SAMPLE_RATE,
                recording_duration=buoy_duration,
                status="Active",
                wav_file=os.path.join(WAV_DIR, f"{sb_def['id']}.wav"),
            )
            db.add(sb)

            # Generate WAV (capped at 60s to keep file sizes small)
            wav_path = generate_wav(sb_def, duration=min(60, buoy_duration))
            print(f"  Generated {wav_path}  (dist={dist:.1f}km, bearing={bearing}°)")

            # Create detection records – all buoys detect the same submarine
            for ch in range(NUM_CHANNELS):
                confidence = round(base_conf + np.random.uniform(-0.03, 0.05), 2)
                det = Detection(
                    sonobuoy_id=sb_def["id"],
                    channel=ch,
                    fundamental_frequency=FUND_FREQ,
                    harmonics=HARMONICS,
                    confidence=float(confidence),
                    timestamp=deploy_time + timedelta(seconds=5 + np.random.uniform(0, 10)),
                )
                db.add(det)

            # Bearing record – bearing from buoy to submarine
            br = BearingResult(
                sonobuoy_id=sb_def["id"],
                bearing=bearing,
                confidence=round(base_conf + np.random.uniform(-0.02, 0.06), 2),
                frequency=FUND_FREQ,
                timestamp=deploy_time + timedelta(seconds=8),
            )
            db.add(br)

            # LOFAR match – Kilo-class
            lm = LofarMatch(
                sonobuoy_id=sb_def["id"],
                channel=0,
                signature_id="SIG001",
                confidence=round(base_conf + np.random.uniform(0, 0.05), 2),
                timestamp=deploy_time + timedelta(seconds=12),
            )
            db.add(lm)

            # Mission event
            evt_desc = (
                f"Acoustic contact bearing {bearing}° at {dist:.1f} km. "
                f"Diesel-generator tonal {FUND_FREQ} Hz with harmonics at "
                f"{', '.join(str(h) for h in HARMONICS)} Hz. "
                f"Blade-rate {BLADE_RATE} Hz. LOFAR match: Kilo-class submarine."
            )
            evt = MissionEvent(
                id=f"EVT{i+1:03d}",
                sonobuoy_id=sb_def["id"],
                timestamp=deploy_time + timedelta(seconds=12),
                channel=0,
                event_type="submarine_contact",
                fundamental_frequency=FUND_FREQ,
                harmonics=HARMONICS,
                bearing=bearing,
                confidence=round(base_conf + np.random.uniform(0, 0.05), 2),
                lofar_match="Kilo-class Submarine (Project 877EKM)",
                description=evt_desc,
            )
            db.add(evt)

        db.commit()

        # Generate mission_metadata.json
        metadata = {
            "missionId": "BOBP-2026-0525",
            "missionName": "Bay of Bengal ASW Patrol – Mandarmani Sector",
            "areaOfOperations": "Mandarmani coast, West Bengal, Bay of Bengal",
            "targetClassification": "Diesel-Electric Submarine (Kilo-class, Project 877EKM)",
            "estimatedTargetPosition": {"latitude": SUB_POSITION[0], "longitude": SUB_POSITION[1]},
            "startTime": base_time.isoformat() + "Z",
            "endTime": end_time.isoformat() + "Z",
            "sonobuoys": [
                {
                    "id": s["id"], "name": s["name"],
                    "latitude": s["lat"], "longitude": s["lon"],
                    "bearingToTarget": _bearing_to_target(s["lat"], s["lon"]),
                    "distanceToTarget_km": round(_distance_km(s["lat"], s["lon"]), 1),
                } for s in SONOBUOYS
            ],
        }
        with open(os.path.join(data_dir, "mission_metadata.json"), "w") as f:
            json.dump(metadata, f, indent=2)

        # Generate sonobuoy_manifest.csv
        with open(os.path.join(data_dir, "sonobuoy_manifest.csv"), "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["id", "name", "latitude", "longitude", "deploymentTime",
                         "numberOfChannels", "sampleRate", "recordingDuration", "status",
                         "bearingToTarget", "distanceToTarget_km"])
            for i, s in enumerate(SONOBUOYS):
                dt = (base_time + timedelta(seconds=i * sb_interval)).isoformat() + "Z"
                dur = max(30, total_span - i * sb_interval)
                w.writerow([s["id"], s["name"], s["lat"], s["lon"], dt,
                            NUM_CHANNELS, SAMPLE_RATE, int(dur), "Active",
                            _bearing_to_target(s["lat"], s["lon"]),
                            round(_distance_km(s["lat"], s["lon"]), 1)])

        # Generate bearing_metadata.csv
        with open(os.path.join(data_dir, "bearing_metadata.csv"), "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["sonobuoyId", "bearing", "confidence", "frequency"])
            for s in SONOBUOYS:
                bearing = _bearing_to_target(s["lat"], s["lon"])
                dist = _distance_km(s["lat"], s["lon"])
                conf = round(max(0.55, 1.0 - dist * 0.04) + np.random.uniform(-0.02, 0.06), 2)
                w.writerow([s["id"], bearing, conf, FUND_FREQ])

        # Generate lofar_signature_database.csv
        with open(os.path.join(data_dir, "lofar_signature_database.csv"), "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["signatureId", "platformType", "fundamentalFrequency", "harmonics", "description"])
            sigs = [
                ("SIG001", "Kilo-class Submarine (877EKM)", 50, "[100,150,200]",
                 "Diesel-electric submarine, diesel-generator tonal at 50 Hz, blade-rate 8 Hz"),
                ("SIG002", "Scorpene-class Submarine", 45, "[90,135,180]",
                 "Diesel-electric submarine, low-speed transit, AIP mode"),
                ("SIG003", "Merchant Vessel (bulk carrier)", 72, "[144]",
                 "Large merchant vessel, single-screw, slow-speed"),
                ("SIG004", "SSN Nuclear Submarine", 42, "[84,126,168]",
                 "Nuclear submarine, reactor coolant pump tonal"),
                ("SIG005", "Fishing Trawler", 60, "[120,180,240]",
                 "Commercial fishing vessel with active trawl winch"),
            ]
            for sig in sigs:
                w.writerow(sig)

        print("Sample data generation complete.")
        return {
            "status": "ok",
            "sonobuoys": len(SONOBUOYS),
            "wavFiles": len(SONOBUOYS),
            "fromDatetime": base_time.isoformat() + "Z",
            "toDatetime": end_time.isoformat() + "Z",
        }

    finally:
        db.close()


if __name__ == "__main__":
    generate_all_data()
