"""FastAPI main application – Sonobuoy Acoustic Analysis System."""
import os
import io
import csv
import json
import shutil
import tempfile
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session

from .database import get_db, init_db, WAV_DIR
from .models import (Sonobuoy, Detection, BearingResult, LofarSignature,
                     LofarMatch, MissionEvent, Correlation)
from .ingestion import ingest_wav, read_channel, read_all_channels
from .dsp import compute_fft, compute_spectrogram
from .harmonic_detection import detect_harmonics
from .lofar_matching import seed_lofar_database, match_signature, store_match
from .bearing import estimate_bearing, get_bearing_data
from .correlation import correlate_sonobuoys
from .sample_data_generator import generate_all_data

import numpy as np
import soundfile as sf


def _parse_dt(s: Optional[str]) -> Optional[datetime]:
    """Parse an ISO datetime string, return None if empty."""
    if not s:
        return None
    return datetime.fromisoformat(s.replace("Z", "+00:00").replace("+00:00", ""))

app = FastAPI(title="Sonobuoy Acoustic Analysis System", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    init_db()


# ── Pydantic schemas ─────────────────────────────────────────────────────────

class SonobuoyCreate(BaseModel):
    id: str
    name: str
    latitude: float
    longitude: float
    deploymentTime: str
    numberOfChannels: int = 4
    sampleRate: int = 48000
    recordingDuration: float = 600
    status: str = "Active"


class SonobuoyUpdate(BaseModel):
    name: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    status: Optional[str] = None


# ── Sample Data ───────────────────────────────────────────────────────────────

class GenerateSampleRequest(BaseModel):
    fromDatetime: Optional[str] = None
    toDatetime: Optional[str] = None


@app.post("/api/generate-sample-data")
def api_generate_sample_data(body: GenerateSampleRequest = GenerateSampleRequest()):
    from_dt = _parse_dt(body.fromDatetime)
    to_dt = _parse_dt(body.toDatetime)
    result = generate_all_data(from_datetime=from_dt, to_datetime=to_dt)
    return result


# ── Sonobuoy CRUD ─────────────────────────────────────────────────────────────

@app.get("/api/sonobuoys")
def list_sonobuoys(db: Session = Depends(get_db)):
    sbs = db.query(Sonobuoy).all()
    return [_sb_dict(s) for s in sbs]


@app.get("/api/sonobuoys/{sb_id}")
def get_sonobuoy(sb_id: str, db: Session = Depends(get_db)):
    sb = db.query(Sonobuoy).filter(Sonobuoy.id == sb_id).first()
    if not sb:
        raise HTTPException(404, "Sonobuoy not found")
    return _sb_dict(sb)


@app.post("/api/sonobuoys")
def create_sonobuoy(data: SonobuoyCreate, db: Session = Depends(get_db)):
    existing = db.query(Sonobuoy).filter(Sonobuoy.id == data.id).first()
    if existing:
        raise HTTPException(409, "Sonobuoy ID already exists")
    sb = Sonobuoy(
        id=data.id, name=data.name, latitude=data.latitude,
        longitude=data.longitude,
        deployment_time=datetime.fromisoformat(data.deploymentTime.replace("Z", "+00:00")),
        number_of_channels=data.numberOfChannels,
        sample_rate=data.sampleRate,
        recording_duration=data.recordingDuration,
        status=data.status,
    )
    db.add(sb)
    db.commit()
    return _sb_dict(sb)


@app.put("/api/sonobuoys/{sb_id}")
def update_sonobuoy(sb_id: str, data: SonobuoyUpdate, db: Session = Depends(get_db)):
    sb = db.query(Sonobuoy).filter(Sonobuoy.id == sb_id).first()
    if not sb:
        raise HTTPException(404, "Sonobuoy not found")
    if data.name is not None:
        sb.name = data.name
    if data.latitude is not None:
        sb.latitude = data.latitude
    if data.longitude is not None:
        sb.longitude = data.longitude
    if data.status is not None:
        sb.status = data.status
    db.commit()
    return _sb_dict(sb)


@app.delete("/api/sonobuoys/{sb_id}")
def delete_sonobuoy(sb_id: str, db: Session = Depends(get_db)):
    sb = db.query(Sonobuoy).filter(Sonobuoy.id == sb_id).first()
    if not sb:
        raise HTTPException(404, "Sonobuoy not found")
    db.delete(sb)
    db.commit()
    return {"status": "deleted"}


def _sb_dict(sb: Sonobuoy) -> dict:
    return {
        "id": sb.id,
        "name": sb.name,
        "latitude": sb.latitude,
        "longitude": sb.longitude,
        "deploymentTime": sb.deployment_time.isoformat() + "Z" if sb.deployment_time else None,
        "numberOfChannels": sb.number_of_channels,
        "sampleRate": sb.sample_rate,
        "recordingDuration": sb.recording_duration,
        "status": sb.status,
        "wavFile": sb.wav_file,
    }


# ── Data Ingestion ────────────────────────────────────────────────────────────

@app.post("/api/ingest/{sb_id}")
async def ingest_file(sb_id: str, file: UploadFile = File(...),
                      timestamp: Optional[str] = None,
                      db: Session = Depends(get_db)):
    sb = db.query(Sonobuoy).filter(Sonobuoy.id == sb_id).first()
    if not sb:
        raise HTTPException(404, "Sonobuoy not found")

    # Update deployment time if provided
    if timestamp:
        dt = _parse_dt(timestamp)
        if dt:
            sb.deployment_time = dt
            db.commit()

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
    try:
        contents = await file.read()
        tmp.write(contents)
        tmp.close()
        result = ingest_wav(tmp.name, sb_id, db)
        result["timestamp"] = sb.deployment_time.isoformat() + "Z" if sb.deployment_time else None
        return result
    finally:
        if os.path.exists(tmp.name):
            os.unlink(tmp.name)


# ── Waveform ──────────────────────────────────────────────────────────────────

@app.get("/api/waveform/{sb_id}")
def get_waveform(sb_id: str,
                 channels: str = "0,1,2,3",
                 start: float = 0,
                 end: Optional[float] = None,
                 max_points: int = 5000,
                 db: Session = Depends(get_db)):
    sb = db.query(Sonobuoy).filter(Sonobuoy.id == sb_id).first()
    if not sb:
        raise HTTPException(404, "Sonobuoy not found")

    channel_list = [int(c.strip()) for c in channels.split(",")]
    data, sr = read_all_channels(sb_id, start, end)
    deploy_iso = sb.deployment_time.isoformat() + "Z" if sb.deployment_time else None
    result = {"sampleRate": sr, "deploymentTime": deploy_iso, "channels": {}}

    for ch in channel_list:
        if ch >= data.shape[1]:
            continue
        ch_raw = data[:, ch]
        # Downsample for transport
        step = 1
        if len(ch_raw) > max_points:
            step = len(ch_raw) // max_points
        ch_data = ch_raw[::step]
        duration = len(ch_raw) / sr
        time_axis = np.linspace(start, start + duration, len(ch_data))
        result["channels"][str(ch)] = {
            "time": time_axis.tolist(),
            "amplitude": ch_data.tolist(),
        }

    return result


# ── FFT ───────────────────────────────────────────────────────────────────────

@app.get("/api/fft/{sb_id}")
def get_fft(sb_id: str, channel: int = 0, start: float = 0,
            end: Optional[float] = None, db: Session = Depends(get_db)):
    sb = db.query(Sonobuoy).filter(Sonobuoy.id == sb_id).first()
    if not sb:
        raise HTTPException(404, "Sonobuoy not found")
    ch_data, sr = read_channel(sb_id, channel, start, end)
    return compute_fft(ch_data, sr)


# ── LOFARgram / Spectrogram ──────────────────────────────────────────────────

@app.get("/api/lofargram/{sb_id}")
def get_lofargram(sb_id: str, channel: int = 0,
                  start: float = 0, end: Optional[float] = None,
                  freq_min: float = 0, freq_max: float = 250,
                  db: Session = Depends(get_db)):
    sb = db.query(Sonobuoy).filter(Sonobuoy.id == sb_id).first()
    if not sb:
        raise HTTPException(404, "Sonobuoy not found")
    ch_data, sr = read_channel(sb_id, channel, start, end)
    result = compute_spectrogram(ch_data, sr, freq_min=freq_min, freq_max=freq_max)
    result["deploymentTime"] = sb.deployment_time.isoformat() + "Z" if sb.deployment_time else None
    return result


# ── Harmonic Detection ───────────────────────────────────────────────────────

@app.get("/api/harmonics/{sb_id}")
def get_harmonics(sb_id: str, channel: int = 0,
                  start: float = 0, end: Optional[float] = None,
                  db: Session = Depends(get_db)):
    sb = db.query(Sonobuoy).filter(Sonobuoy.id == sb_id).first()
    if not sb:
        raise HTTPException(404, "Sonobuoy not found")
    ch_data, sr = read_channel(sb_id, channel, start, end)
    return detect_harmonics(ch_data, sr, sb_id, channel, db)


@app.get("/api/detections")
def list_detections(sonobuoy_id: Optional[str] = None,
                    from_datetime: Optional[str] = None,
                    to_datetime: Optional[str] = None,
                    db: Session = Depends(get_db)):
    q = db.query(Detection)
    if sonobuoy_id:
        q = q.filter(Detection.sonobuoy_id == sonobuoy_id)
    dt_from = _parse_dt(from_datetime)
    dt_to = _parse_dt(to_datetime)
    if dt_from:
        q = q.filter(Detection.timestamp >= dt_from)
    if dt_to:
        q = q.filter(Detection.timestamp <= dt_to)
    dets = q.all()
    return [{
        "id": d.id,
        "sonobuoyId": d.sonobuoy_id,
        "channel": d.channel,
        "fundamentalFrequency": d.fundamental_frequency,
        "harmonics": d.harmonics,
        "confidence": d.confidence,
        "timestamp": d.timestamp.isoformat() + "Z" if d.timestamp else None,
    } for d in dets]


# ── LOFAR Matching ────────────────────────────────────────────────────────────

@app.get("/api/lofar-signatures")
def list_signatures(db: Session = Depends(get_db)):
    sigs = db.query(LofarSignature).all()
    return [{
        "id": s.id, "platformType": s.platform_type,
        "fundamentalFrequency": s.fundamental_frequency,
        "harmonics": s.harmonics, "description": s.description,
    } for s in sigs]


@app.post("/api/lofar-match/{sb_id}")
def run_lofar_match(sb_id: str, channel: int = 0,
                    db: Session = Depends(get_db)):
    sb = db.query(Sonobuoy).filter(Sonobuoy.id == sb_id).first()
    if not sb:
        raise HTTPException(404, "Sonobuoy not found")

    ch_data, sr = read_channel(sb_id, channel)
    det = detect_harmonics(ch_data, sr, sb_id, channel)
    matches = match_signature(det, db)

    if matches:
        store_match(sb_id, channel, matches[0]["signatureId"],
                    matches[0]["confidence"], db)

    return {"detection": det, "matches": matches}


@app.get("/api/lofar-matches")
def list_lofar_matches(sonobuoy_id: Optional[str] = None,
                       from_datetime: Optional[str] = None,
                       to_datetime: Optional[str] = None,
                       db: Session = Depends(get_db)):
    q = db.query(LofarMatch)
    if sonobuoy_id:
        q = q.filter(LofarMatch.sonobuoy_id == sonobuoy_id)
    dt_from = _parse_dt(from_datetime)
    dt_to = _parse_dt(to_datetime)
    if dt_from:
        q = q.filter(LofarMatch.timestamp >= dt_from)
    if dt_to:
        q = q.filter(LofarMatch.timestamp <= dt_to)
    matches = q.all()
    return [{
        "id": m.id,
        "sonobuoyId": m.sonobuoy_id,
        "channel": m.channel,
        "signatureId": m.signature_id,
        "confidence": m.confidence,
        "timestamp": m.timestamp.isoformat() + "Z" if m.timestamp else None,
    } for m in matches]


# ── Bearing ───────────────────────────────────────────────────────────────────

@app.get("/api/bearing/{sb_id}")
def get_bearing(sb_id: str, db: Session = Depends(get_db)):
    sb = db.query(Sonobuoy).filter(Sonobuoy.id == sb_id).first()
    if not sb:
        raise HTTPException(404, "Sonobuoy not found")
    results = get_bearing_data(sb_id, db)
    if not results:
        # Compute from WAV
        data, sr = read_all_channels(sb_id)
        signals = [data[:, ch] for ch in range(data.shape[1])]
        det = detect_harmonics(signals[0], sr, sb_id, 0)
        freq = det["fundamentalFrequency"] or 48
        result = estimate_bearing(signals, sr, sb_id, freq, db)
        return [result]
    return results


# ── Correlation ───────────────────────────────────────────────────────────────

@app.post("/api/correlate")
def run_correlation(sonobuoy_ids: list[str], db: Session = Depends(get_db)):
    if len(sonobuoy_ids) < 2:
        raise HTTPException(400, "Need at least 2 sonobuoy IDs")
    return correlate_sonobuoys(sonobuoy_ids, db)


@app.get("/api/correlations")
def list_correlations(from_datetime: Optional[str] = None,
                      to_datetime: Optional[str] = None,
                      db: Session = Depends(get_db)):
    q = db.query(Correlation)
    dt_from = _parse_dt(from_datetime)
    dt_to = _parse_dt(to_datetime)
    if dt_from:
        q = q.filter(Correlation.timestamp >= dt_from)
    if dt_to:
        q = q.filter(Correlation.timestamp <= dt_to)
    corrs = q.all()
    return [{
        "id": c.id,
        "sonobuoyA": c.sonobuoy_id_a,
        "sonobuoyB": c.sonobuoy_id_b,
        "correlationScore": c.correlation_score,
        "commonFrequencies": c.common_frequencies,
        "timestamp": c.timestamp.isoformat() + "Z" if c.timestamp else None,
    } for c in corrs]


# ── Mission Events / Timeline ────────────────────────────────────────────────

@app.get("/api/events")
def list_events(sonobuoy_id: Optional[str] = None,
                min_confidence: Optional[float] = None,
                frequency: Optional[float] = None,
                from_datetime: Optional[str] = None,
                to_datetime: Optional[str] = None,
                db: Session = Depends(get_db)):
    q = db.query(MissionEvent)
    if sonobuoy_id:
        q = q.filter(MissionEvent.sonobuoy_id == sonobuoy_id)
    if min_confidence is not None:
        q = q.filter(MissionEvent.confidence >= min_confidence)
    if frequency is not None:
        q = q.filter(MissionEvent.fundamental_frequency == frequency)
    dt_from = _parse_dt(from_datetime)
    dt_to = _parse_dt(to_datetime)
    if dt_from:
        q = q.filter(MissionEvent.timestamp >= dt_from)
    if dt_to:
        q = q.filter(MissionEvent.timestamp <= dt_to)
    events = q.order_by(MissionEvent.timestamp).all()
    return [{
        "eventId": e.id,
        "sonobuoyId": e.sonobuoy_id,
        "timestamp": e.timestamp.isoformat() + "Z" if e.timestamp else None,
        "channel": e.channel,
        "eventType": e.event_type,
        "fundamentalFrequency": e.fundamental_frequency,
        "harmonics": e.harmonics,
        "bearing": e.bearing,
        "confidence": e.confidence,
        "lofarMatch": e.lofar_match,
        "description": e.description,
    } for e in events]


# ── Dashboard ─────────────────────────────────────────────────────────────────

@app.get("/api/dashboard")
def get_dashboard(from_datetime: Optional[str] = None,
                  to_datetime: Optional[str] = None,
                  db: Session = Depends(get_db)):
    dt_from = _parse_dt(from_datetime)
    dt_to = _parse_dt(to_datetime)

    sb_q = db.query(Sonobuoy)
    det_q = db.query(Detection)
    lm_q = db.query(LofarMatch)
    corr_q = db.query(Correlation)

    if dt_from:
        sb_q = sb_q.filter(Sonobuoy.deployment_time >= dt_from)
        det_q = det_q.filter(Detection.timestamp >= dt_from)
        lm_q = lm_q.filter(LofarMatch.timestamp >= dt_from)
        corr_q = corr_q.filter(Correlation.timestamp >= dt_from)
    if dt_to:
        sb_q = sb_q.filter(Sonobuoy.deployment_time <= dt_to)
        det_q = det_q.filter(Detection.timestamp <= dt_to)
        lm_q = lm_q.filter(LofarMatch.timestamp <= dt_to)
        corr_q = corr_q.filter(Correlation.timestamp <= dt_to)

    sonobuoys = sb_q.all()
    detections = det_q.all()
    lofar_matches = lm_q.all()
    correlations = corr_q.all()

    total_channels = sum(s.number_of_channels or 0 for s in sonobuoys)
    active = sum(1 for s in sonobuoys if s.status == "Active")

    best_match = None
    if lofar_matches:
        best = max(lofar_matches, key=lambda m: m.confidence)
        sig = db.query(LofarSignature).filter(LofarSignature.id == best.signature_id).first()
        best_match = {
            "sonobuoyId": best.sonobuoy_id,
            "signatureId": best.signature_id,
            "platformType": sig.platform_type if sig else "Unknown",
            "confidence": best.confidence,
        }

    avg_corr = 0
    if correlations:
        avg_corr = round(sum(c.correlation_score for c in correlations) / len(correlations), 1)

    return {
        "totalSonobuoys": len(sonobuoys),
        "totalChannels": total_channels,
        "activeRecordings": active,
        "detectedContacts": len(set(d.sonobuoy_id for d in detections)),
        "highestConfidenceMatch": best_match,
        "averageCorrelationScore": avg_corr,
        "totalDetections": len(detections),
        "totalLofarMatches": len(lofar_matches),
    }


# ── Reports / Export ──────────────────────────────────────────────────────────

@app.get("/api/reports/detections")
def export_detections_csv(db: Session = Depends(get_db)):
    from fastapi.responses import StreamingResponse
    dets = db.query(Detection).all()
    output = io.StringIO()
    w = csv.writer(output)
    w.writerow(["id", "sonobuoyId", "channel", "fundamentalFrequency", "harmonics", "confidence", "timestamp"])
    for d in dets:
        w.writerow([d.id, d.sonobuoy_id, d.channel, d.fundamental_frequency,
                     json.dumps(d.harmonics), d.confidence,
                     d.timestamp.isoformat() if d.timestamp else ""])
    output.seek(0)
    return StreamingResponse(io.BytesIO(output.getvalue().encode()),
                             media_type="text/csv",
                             headers={"Content-Disposition": "attachment; filename=detections.csv"})


@app.get("/api/reports/sonobuoys")
def export_sonobuoys_csv(db: Session = Depends(get_db)):
    from fastapi.responses import StreamingResponse
    sbs = db.query(Sonobuoy).all()
    output = io.StringIO()
    w = csv.writer(output)
    w.writerow(["id", "name", "latitude", "longitude", "deploymentTime",
                 "numberOfChannels", "sampleRate", "recordingDuration", "status"])
    for s in sbs:
        w.writerow([s.id, s.name, s.latitude, s.longitude,
                     s.deployment_time.isoformat() if s.deployment_time else "",
                     s.number_of_channels, s.sample_rate, s.recording_duration, s.status])
    output.seek(0)
    return StreamingResponse(io.BytesIO(output.getvalue().encode()),
                             media_type="text/csv",
                             headers={"Content-Disposition": "attachment; filename=sonobuoys.csv"})


@app.get("/api/reports/correlations")
def export_correlations_csv(db: Session = Depends(get_db)):
    from fastapi.responses import StreamingResponse
    corrs = db.query(Correlation).all()
    output = io.StringIO()
    w = csv.writer(output)
    w.writerow(["id", "sonobuoyA", "sonobuoyB", "correlationScore", "commonFrequencies", "timestamp"])
    for c in corrs:
        w.writerow([c.id, c.sonobuoy_id_a, c.sonobuoy_id_b, c.correlation_score,
                     json.dumps(c.common_frequencies),
                     c.timestamp.isoformat() if c.timestamp else ""])
    output.seek(0)
    return StreamingResponse(io.BytesIO(output.getvalue().encode()),
                             media_type="text/csv",
                             headers={"Content-Disposition": "attachment; filename=correlations.csv"})


@app.get("/api/reports/mission-summary")
def export_mission_summary(db: Session = Depends(get_db)):
    dashboard = get_dashboard(db)
    events = list_events(db=db)
    sonobuoys = [_sb_dict(s) for s in db.query(Sonobuoy).all()]
    return {
        "dashboard": dashboard,
        "sonobuoys": sonobuoys,
        "events": events,
    }


# ── Playback Snapshot ─────────────────────────────────────────────────────────

@app.get("/api/playback/info")
def playback_info(db: Session = Depends(get_db)):
    """Return time bounds and sonobuoy list for playback."""
    from datetime import timedelta as _td
    sbs = db.query(Sonobuoy).filter(Sonobuoy.wav_file.isnot(None)).all()
    if not sbs:
        return {"sonobuoys": [], "startTime": None, "endTime": None, "totalDuration": 0}

    entries = []
    for sb in sbs:
        dep = sb.deployment_time
        dur = sb.recording_duration or 30
        entries.append({
            **_sb_dict(sb),
            "startTime": dep.isoformat() + "Z" if dep else None,
            "endTime": (dep + _td(seconds=dur)).isoformat() + "Z" if dep else None,
        })

    all_starts = [sb.deployment_time for sb in sbs if sb.deployment_time]
    all_ends = [sb.deployment_time + _td(seconds=sb.recording_duration or 30) for sb in sbs if sb.deployment_time]

    global_start = min(all_starts) if all_starts else None
    global_end = max(all_ends) if all_ends else None
    total = (global_end - global_start).total_seconds() if global_start and global_end else 0

    return {
        "sonobuoys": entries,
        "startTime": global_start.isoformat() + "Z" if global_start else None,
        "endTime": global_end.isoformat() + "Z" if global_end else None,
        "totalDuration": round(total, 2),
    }


@app.get("/api/playback/snapshot")
def playback_snapshot(cursor: float = 0, window: float = 2.0,
                      max_points: int = 500,
                      db: Session = Depends(get_db)):
    """Return waveform + FFT data for ALL sonobuoys at a given cursor position.

    cursor: seconds offset from global start time
    window: seconds of audio to return around cursor
    """
    from datetime import timedelta as _td
    sbs = db.query(Sonobuoy).filter(Sonobuoy.wav_file.isnot(None)).all()
    if not sbs:
        return {"sonobuoys": []}

    all_starts = [sb.deployment_time for sb in sbs if sb.deployment_time]
    if not all_starts:
        return {"sonobuoys": []}

    global_start = min(all_starts)
    results = []

    for sb in sbs:
        dep = sb.deployment_time
        dur = sb.recording_duration or 30
        if not dep:
            continue

        sb_offset = cursor - (dep - global_start).total_seconds()
        sb_entry: dict = {
            "id": sb.id,
            "name": sb.name,
            "latitude": sb.latitude,
            "longitude": sb.longitude,
            "active": 0 <= sb_offset < dur,
            "waveform": None,
            "fft": None,
            "bearing": None,
            "detection": None,
        }

        if sb_entry["active"]:
            # WAV file may be shorter than recording_duration; wrap into file
            wav_info = sf.info(os.path.join(WAV_DIR, f"{sb.id}.wav"))
            file_dur = wav_info.duration
            wav_start = max(0, sb_offset - window / 2) % file_dur
            wav_end = wav_start + window
            if wav_end > file_dur:
                wav_end = file_dur
            try:
                data, sr = read_all_channels(sb.id, wav_start, wav_end)
                ch0 = data[:, 0] if data.shape[1] > 0 else data.flatten()
                step = max(1, len(ch0) // max_points)
                ds = ch0[::step]
                time_axis = np.linspace(wav_start, wav_end, len(ds))
                sb_entry["waveform"] = {
                    "time": time_axis.tolist(),
                    "amplitude": ds.tolist(),
                    "channels": data.shape[1],
                }
                sb_entry["fft"] = compute_fft(ch0, sr)
                br = db.query(BearingResult).filter(
                    BearingResult.sonobuoy_id == sb.id).first()
                if br:
                    sb_entry["bearing"] = {
                        "bearing": br.bearing,
                        "confidence": br.confidence,
                        "frequency": br.frequency,
                    }
                det = db.query(Detection).filter(
                    Detection.sonobuoy_id == sb.id).first()
                if det:
                    sb_entry["detection"] = {
                        "fundamentalFrequency": det.fundamental_frequency,
                        "harmonics": det.harmonics,
                        "confidence": det.confidence,
                    }
            except Exception:
                pass

        results.append(sb_entry)

    return {
        "cursor": cursor,
        "window": window,
        "sonobuoys": results,
    }
