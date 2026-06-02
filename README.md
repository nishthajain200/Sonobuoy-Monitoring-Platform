# Sonobuoy Acoustic Analysis System

A local web-based POC for managing and analyzing recorded acoustic data from 8 sonobuoys. Each sonobuoy has 4 hydrophone channels stored as multi-channel WAV (PCM) files.

## Features

- **Dashboard** – overview of sonobuoys, detections, LOFAR matches, and correlation scores
- **Sonobuoy Management** – CRUD for 8 sonobuoys with deployment metadata
- **Data Ingestion** – upload multi-channel WAV files, auto-detect channels/sample rate/duration
- **Waveform Viewer** – multi-channel waveform with zoom/pan and channel toggle
- **FFT Analysis** – frequency vs amplitude with peak detection and harmonic identification
- **LOFARgram Viewer** – STFT-based spectrogram with frequency filtering and LOFAR signature matching
- **Bearing / Polar View** – polar plot with bearing angle, confidence, and frequency label
- **Multi-Sonobuoy Analysis** – correlation across 2/4/8 sonobuoys by frequency and harmonic pattern
- **Tactical Map** – Leaflet map showing sonobuoy locations, bearing lines, correlation links, target zone
- **Mission Timeline** – time-axis view of all events with filters and event detail panel
- **Reports** – export detection CSV, sonobuoy CSV, correlation CSV, mission summary JSON

## Technology Stack

| Layer    | Technology |
|----------|-----------|
| Frontend | React.js + TypeScript, Material UI, Plotly.js, Leaflet.js |
| Backend  | Python FastAPI, NumPy, SciPy, Librosa, SoundFile, Pandas |
| Database | SQLite |
| Deploy   | Docker Compose |

## Quick Start

### 1. Build and run with Docker Compose

```bash
docker compose up --build
```

This starts:
- **Backend** at `http://localhost:8000` (FastAPI)
- **Frontend** at `http://localhost:3000` (React/Nginx)

### 2. Generate sample data

Open the Dashboard at `http://localhost:3000` and click **"Generate Sample Data"**.

Or call the API directly:

```bash
curl -X POST http://localhost:8000/api/generate-sample-data
```

This creates:
- 8 multi-channel WAV files (SB001–SB008)
- Sonobuoy records in SQLite
- Detection, bearing, LOFAR match, and mission event records
- `mission_metadata.json`, `sonobuoy_manifest.csv`, `bearing_metadata.csv`, `lofar_signature_database.csv`

### 3. Explore the application

1. **Dashboard** – view summary statistics
2. **Sonobuoy Management** – view/edit all 8 sonobuoys
3. **Waveform Viewer** – select a sonobuoy to see 4-channel waveforms
4. **FFT Analysis** – view frequency spectrum and detected harmonics
5. **LOFARgram** – view spectrogram and run LOFAR signature matching
6. **Bearing View** – view polar bearing plot
7. **Multi-Sonobuoy** – select sonobuoys and run correlation analysis
8. **Tactical Map** – see all sonobuoys on map with bearing lines
9. **Mission Timeline** – view all events across time with filters
10. **Reports** – download CSV and JSON exports

### 4. Local development (without Docker)

**Backend:**
```bash
cd backend
pip install -r requirements.txt
python -m app.sample_data_generator   # generate sample data
uvicorn app.main:app --reload --port 8000
```

**Frontend:**
```bash
cd frontend
npm install --legacy-peer-deps
set REACT_APP_API_URL=http://localhost:8000/api
npm start
```

## Project Structure

```
backend/
  app/
    main.py                  # FastAPI application with all endpoints
    models.py                # SQLAlchemy ORM models
    database.py              # SQLite setup and session management
    ingestion.py             # WAV file ingestion and channel extraction
    dsp.py                   # FFT and STFT/LOFARgram computation
    harmonic_detection.py    # Harmonic detection engine
    lofar_matching.py        # LOFAR signature matching
    bearing.py               # Bearing estimation
    correlation.py           # Multi-sonobuoy correlation
    sample_data_generator.py # Synthetic data generator
  requirements.txt
  Dockerfile

frontend/
  src/
    pages/
      Dashboard.tsx
      SonobuoyManagement.tsx
      DataIngestion.tsx
      WaveformViewer.tsx
      FFTAnalysis.tsx
      LofargramViewer.tsx
      BearingView.tsx
      MultiSonobuoyAnalysis.tsx
      TacticalMap.tsx
      MissionTimeline.tsx
      Reports.tsx
    components/
      SonobuoySelector.tsx
    services/
      api.ts
    App.tsx
  package.json
  Dockerfile

docker-compose.yml
README.md
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/generate-sample-data` | Generate all synthetic data |
| GET | `/api/sonobuoys` | List all sonobuoys |
| POST | `/api/sonobuoys` | Create sonobuoy |
| PUT | `/api/sonobuoys/{id}` | Update sonobuoy |
| DELETE | `/api/sonobuoys/{id}` | Delete sonobuoy |
| POST | `/api/ingest/{id}` | Upload WAV file |
| GET | `/api/waveform/{id}` | Get waveform data |
| GET | `/api/fft/{id}` | Get FFT data |
| GET | `/api/lofargram/{id}` | Get spectrogram data |
| GET | `/api/harmonics/{id}` | Detect harmonics |
| GET | `/api/lofar-signatures` | List LOFAR signatures |
| POST | `/api/lofar-match/{id}` | Run LOFAR matching |
| GET | `/api/bearing/{id}` | Get bearing data |
| POST | `/api/correlate` | Run multi-sonobuoy correlation |
| GET | `/api/events` | List mission events |
| GET | `/api/dashboard` | Get dashboard summary |
| GET | `/api/reports/*` | Export reports |

## Notes

- This is a **POC** using synthetic data only
- No real sonar hardware or RF input required
- WAV files are generated with fundamental frequencies (48, 60, 72 Hz) and their harmonics
- Duration is 30s per sonobuoy for fast generation
