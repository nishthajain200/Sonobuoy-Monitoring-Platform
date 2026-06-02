import axios from 'axios';

const API_BASE = process.env.REACT_APP_API_URL || '/api';

const api = axios.create({ baseURL: API_BASE });

// ── Sonobuoys ───────────────────────────────────────────────────────────────
export const getSonobuoys = () => api.get('/sonobuoys').then(r => r.data);
export const getSonobuoy = (id: string) => api.get(`/sonobuoys/${id}`).then(r => r.data);
export const createSonobuoy = (data: any) => api.post('/sonobuoys', data).then(r => r.data);
export const updateSonobuoy = (id: string, data: any) => api.put(`/sonobuoys/${id}`, data).then(r => r.data);
export const deleteSonobuoy = (id: string) => api.delete(`/sonobuoys/${id}`).then(r => r.data);

// ── Sample Data ─────────────────────────────────────────────────────────────
export const generateSampleData = (fromDatetime?: string, toDatetime?: string) =>
  api.post('/generate-sample-data', { fromDatetime, toDatetime }).then(r => r.data);

// ── Ingestion ───────────────────────────────────────────────────────────────
export const ingestFile = (sbId: string, file: File, timestamp?: string) => {
  const form = new FormData();
  form.append('file', file);
  const params: any = {};
  if (timestamp) params.timestamp = timestamp;
  return api.post(`/ingest/${sbId}`, form, { params }).then(r => r.data);
};

// ── Waveform ────────────────────────────────────────────────────────────────
export const getWaveform = (sbId: string, channels = '0,1,2,3', start = 0, end?: number) =>
  api.get(`/waveform/${sbId}`, { params: { channels, start, end } }).then(r => r.data);

// ── FFT ─────────────────────────────────────────────────────────────────────
export const getFFT = (sbId: string, channel = 0, start = 0, end?: number) =>
  api.get(`/fft/${sbId}`, { params: { channel, start, end } }).then(r => r.data);

// ── LOFARgram ───────────────────────────────────────────────────────────────
export const getLofargram = (sbId: string, channel = 0, freqMin = 0, freqMax = 250) =>
  api.get(`/lofargram/${sbId}`, { params: { channel, freq_min: freqMin, freq_max: freqMax } }).then(r => r.data);

// ── Harmonics ───────────────────────────────────────────────────────────────
export const getHarmonics = (sbId: string, channel = 0) =>
  api.get(`/harmonics/${sbId}`, { params: { channel } }).then(r => r.data);

export const getDetections = (sonobuoyId?: string, fromDatetime?: string, toDatetime?: string) =>
  api.get('/detections', { params: { sonobuoy_id: sonobuoyId, from_datetime: fromDatetime, to_datetime: toDatetime } }).then(r => r.data);

// ── LOFAR Matching ──────────────────────────────────────────────────────────
export const getLofarSignatures = () => api.get('/lofar-signatures').then(r => r.data);
export const runLofarMatch = (sbId: string, channel = 0) =>
  api.post(`/lofar-match/${sbId}`, null, { params: { channel } }).then(r => r.data);
export const getLofarMatches = (sonobuoyId?: string, fromDatetime?: string, toDatetime?: string) =>
  api.get('/lofar-matches', { params: { sonobuoy_id: sonobuoyId, from_datetime: fromDatetime, to_datetime: toDatetime } }).then(r => r.data);

// ── Bearing ─────────────────────────────────────────────────────────────────
export const getBearing = (sbId: string) => api.get(`/bearing/${sbId}`).then(r => r.data);

// ── Correlation ─────────────────────────────────────────────────────────────
export const runCorrelation = (sonobuoyIds: string[]) =>
  api.post('/correlate', sonobuoyIds).then(r => r.data);
export const getCorrelations = (fromDatetime?: string, toDatetime?: string) =>
  api.get('/correlations', { params: { from_datetime: fromDatetime, to_datetime: toDatetime } }).then(r => r.data);

// ── Events / Timeline ───────────────────────────────────────────────────────
export const getEvents = (params?: { sonobuoy_id?: string; min_confidence?: number; frequency?: number; from_datetime?: string; to_datetime?: string }) =>
  api.get('/events', { params }).then(r => r.data);

// ── Dashboard ───────────────────────────────────────────────────────────────
export const getDashboard = (fromDatetime?: string, toDatetime?: string) =>
  api.get('/dashboard', { params: { from_datetime: fromDatetime, to_datetime: toDatetime } }).then(r => r.data);

// ── Reports ─────────────────────────────────────────────────────────────────
export const downloadDetectionsCSV = () => api.get('/reports/detections', { responseType: 'blob' }).then(r => r.data);
export const downloadSonobuoysCSV = () => api.get('/reports/sonobuoys', { responseType: 'blob' }).then(r => r.data);
export const downloadCorrelationsCSV = () => api.get('/reports/correlations', { responseType: 'blob' }).then(r => r.data);
export const getMissionSummary = () => api.get('/reports/mission-summary').then(r => r.data);

// ── Playback ────────────────────────────────────────────────────────────────
export const getPlaybackInfo = () => api.get('/playback/info').then(r => r.data);
export const getPlaybackSnapshot = (cursor: number, window = 2.0, maxPoints = 500) =>
  api.get('/playback/snapshot', { params: { cursor, window, max_points: maxPoints } }).then(r => r.data);
