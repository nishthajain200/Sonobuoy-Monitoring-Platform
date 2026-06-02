import React, { useEffect, useState, useRef, useCallback } from 'react';
import {
  Box, Typography, Slider, IconButton, Chip, Card, CardContent,
  CircularProgress, Grid, FormControl, InputLabel, Select, MenuItem,
  Tooltip,
} from '@mui/material';
import {
  PlayArrow, Pause, SkipPrevious, SkipNext, Speed, FiberManualRecord,
} from '@mui/icons-material';
import Plot from 'react-plotly.js';
import { MapContainer, TileLayer, CircleMarker, Popup, Polyline } from 'react-leaflet';
import { getPlaybackInfo, getPlaybackSnapshot } from '../services/api';

const SPEEDS = [0.25, 0.5, 1, 2, 4];

const LivePlayback: React.FC = () => {
  const [info, setInfo] = useState<any>(null);
  const [snapshot, setSnapshot] = useState<any>(null);
  const [cursor, setCursor] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [speedIdx, setSpeedIdx] = useState(2); // 1x
  const [window, setWindow] = useState(2);
  const [loading, setLoading] = useState(true);
  const timerRef = useRef<number | null>(null);
  const cursorRef = useRef(0);

  // Load playback info on mount
  useEffect(() => {
    getPlaybackInfo().then(d => {
      setInfo(d);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, []);

  // Fetch snapshot when cursor changes
  const fetchSnapshot = useCallback((c: number) => {
    getPlaybackSnapshot(c, window).then(setSnapshot).catch(() => {});
  }, [window]);

  useEffect(() => {
    if (info?.totalDuration > 0) fetchSnapshot(cursor);
  }, [cursor, info, fetchSnapshot]);

  // Autoplay loop
  useEffect(() => {
    if (playing && info?.totalDuration > 0) {
      const speed = SPEEDS[speedIdx];
      const interval = 500; // ms between updates
      const step = (interval / 1000) * speed;

      timerRef.current = globalThis.setInterval(() => {
        cursorRef.current += step;
        if (cursorRef.current >= info.totalDuration) {
          cursorRef.current = 0;
          setPlaying(false);
        }
        setCursor(parseFloat(cursorRef.current.toFixed(2)));
      }, interval) as unknown as number;

      return () => {
        if (timerRef.current) clearInterval(timerRef.current);
      };
    }
  }, [playing, speedIdx, info]);

  // Sync ref with state
  useEffect(() => { cursorRef.current = cursor; }, [cursor]);

  const handleSliderChange = (_: any, v: number | number[]) => {
    const val = v as number;
    setCursor(val);
    cursorRef.current = val;
  };

  const togglePlay = () => setPlaying(p => !p);

  const cycleSpeed = () => setSpeedIdx(i => (i + 1) % SPEEDS.length);

  const formatTime = (s: number) => {
    const m = Math.floor(s / 60);
    const sec = Math.floor(s % 60);
    return `${m}:${sec.toString().padStart(2, '0')}`;
  };

  const cursorAbsTime = info?.startTime
    ? new Date(new Date(info.startTime).getTime() + cursor * 1000).toISOString().replace('T', ' ').slice(0, 19)
    : '';

  if (loading) return <Box p={4}><CircularProgress /></Box>;

  if (!info || info.totalDuration === 0) {
    return (
      <Box p={3}>
        <Typography variant="h4" gutterBottom>Live Playback</Typography>
        <Typography color="textSecondary">
          No sonobuoy recordings found. Generate sample data or ingest WAV files first.
        </Typography>
      </Box>
    );
  }

  const activeSbs = snapshot?.sonobuoys?.filter((s: any) => s.active) || [];
  const inactiveSbs = snapshot?.sonobuoys?.filter((s: any) => !s.active) || [];

  // Map center from all sonobuoys in info
  const allSbs = info?.sonobuoys || [];
  const mapCenter: [number, number] = allSbs.length
    ? [allSbs.reduce((s: number, b: any) => s + b.latitude, 0) / allSbs.length,
       allSbs.reduce((s: number, b: any) => s + b.longitude, 0) / allSbs.length]
    : [12.85, 72.97];

  // Convert relative waveform seconds to absolute datetime
  const toAbsoluteTime = (sb: any, relSec: number) => {
    if (!info?.startTime) return relSec;
    // sb deploys at some offset from global start
    const sbEntry = allSbs.find((s: any) => s.id === sb.id);
    const deployMs = sbEntry ? new Date(sbEntry.deploymentTime).getTime() : new Date(info.startTime).getTime();
    return new Date(deployMs + relSec * 1000).toISOString();
  };

  // Bearing lines for active sonobuoys
  const bearingLines: { positions: [number, number][]; id: string }[] = [];
  (snapshot?.sonobuoys || []).forEach((sb: any) => {
    if (!sb.active || !sb.bearing || !sb.latitude) return;
    const rad = (sb.bearing.bearing * Math.PI) / 180;
    const len = 0.03;
    bearingLines.push({
      positions: [[sb.latitude, sb.longitude], [sb.latitude + len * Math.cos(rad), sb.longitude + len * Math.sin(rad)]],
      id: sb.id,
    });
  });

  return (
    <Box p={2}>
      <Typography variant="h5" gutterBottom>
        Live Playback – All Sonobuoys
      </Typography>

      {/* ── Transport Controls ── */}
      <Card sx={{ mb: 2 }}>
        <CardContent sx={{ py: 1, '&:last-child': { pb: 1 } }}>
          <Box display="flex" alignItems="center" gap={1}>
            <IconButton size="small" onClick={() => { setCursor(0); cursorRef.current = 0; }}>
              <SkipPrevious />
            </IconButton>
            <IconButton color="primary" onClick={togglePlay}>
              {playing ? <Pause /> : <PlayArrow />}
            </IconButton>
            <IconButton size="small" onClick={() => {
              const end = info.totalDuration;
              setCursor(end);
              cursorRef.current = end;
              setPlaying(false);
            }}>
              <SkipNext />
            </IconButton>

            <Tooltip title={`Speed: ${SPEEDS[speedIdx]}x`}>
              <IconButton size="small" onClick={cycleSpeed}>
                <Speed />
              </IconButton>
            </Tooltip>
            <Chip label={`${SPEEDS[speedIdx]}x`} size="small" variant="outlined" />

            <Box sx={{ flexGrow: 1, mx: 2 }}>
              <Slider
                value={cursor}
                min={0}
                max={info.totalDuration}
                step={0.1}
                onChange={handleSliderChange}
                valueLabelDisplay="auto"
                valueLabelFormat={formatTime}
                size="small"
              />
            </Box>

            <Typography variant="body2" sx={{ minWidth: 80, textAlign: 'right' }}>
              {formatTime(cursor)} / {formatTime(info.totalDuration)}
            </Typography>

            <FormControl size="small" sx={{ minWidth: 80, ml: 1 }}>
              <InputLabel>Window</InputLabel>
              <Select value={window} label="Window" onChange={e => setWindow(e.target.value as number)}>
                {[0.5, 1, 2, 5, 10].map(w => (
                  <MenuItem key={w} value={w}>{w}s</MenuItem>
                ))}
              </Select>
            </FormControl>
          </Box>

          <Typography variant="caption" color="textSecondary">
            {cursorAbsTime} | Active: {activeSbs.length}/{snapshot?.sonobuoys?.length || 0} sonobuoys
          </Typography>
        </CardContent>
      </Card>

      {/* ── Map + Grid Layout ── */}
      <Grid container spacing={2}>
        {/* Map panel */}
        <Grid item xs={12} md={5} lg={4}>
          <Card sx={{ height: 420 }}>
            <CardContent sx={{ p: 1, '&:last-child': { pb: 1 }, height: '100%' }}>
              <Typography variant="subtitle2" gutterBottom>Sonobuoy Positions</Typography>
              <Box sx={{ height: 'calc(100% - 28px)', borderRadius: 1, overflow: 'hidden' }}>
                <MapContainer center={mapCenter} zoom={12} style={{ height: '100%', width: '100%' }}>
                  <TileLayer
                    attribution='&copy; OpenStreetMap'
                    url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                  />
                  {(snapshot?.sonobuoys || allSbs).map((sb: any) => (
                    <CircleMarker
                      key={sb.id}
                      center={[sb.latitude, sb.longitude]}
                      radius={sb.active ? 10 : 6}
                      fillColor={sb.active ? '#4caf50' : '#9e9e9e'}
                      color={sb.active ? '#1b5e20' : '#616161'}
                      weight={2}
                      fillOpacity={0.8}
                    >
                      <Popup>
                        <strong>{sb.id}</strong> – {sb.name}<br />
                        Status: {sb.active ? 'Active' : 'Inactive'}<br />
                        {sb.detection && <>Freq: {sb.detection.fundamentalFrequency} Hz<br /></>}
                        {sb.bearing && <>Bearing: {sb.bearing.bearing}°<br /></>}
                      </Popup>
                    </CircleMarker>
                  ))}
                  {bearingLines.map((line, i) => (
                    <Polyline key={`b-${i}`} positions={line.positions} color="#d32f2f" weight={2} />
                  ))}
                </MapContainer>
              </Box>
            </CardContent>
          </Card>
        </Grid>

        {/* Sonobuoy cards */}
        <Grid item xs={12} md={7} lg={8}>
          <Grid container spacing={1}>

      {/* ── Sonobuoy Grid ── */}
      {snapshot?.sonobuoys?.map((sb: any) => (
        <Grid item xs={12} sm={6} lg={4} key={sb.id}>
            <Card sx={{
              border: sb.active ? '2px solid #1976d2' : '1px solid #e0e0e0',
              opacity: sb.active ? 1 : 0.5,
              height: '100%',
            }}>
              <CardContent sx={{ p: 1, '&:last-child': { pb: 1 } }}>
                {/* Header */}
                <Box display="flex" alignItems="center" justifyContent="space-between" mb={0.5}>
                  <Box display="flex" alignItems="center" gap={0.5}>
                    <FiberManualRecord
                      sx={{ fontSize: 10, color: sb.active ? '#4caf50' : '#bdbdbd' }}
                    />
                    <Typography variant="subtitle2">{sb.id}</Typography>
                  </Box>
                  <Typography variant="caption" color="textSecondary">{sb.name}</Typography>
                </Box>

                {sb.active && sb.waveform ? (
                  <>
                    {/* Waveform mini-plot */}
                    <Plot
                      data={[{
                        x: sb.waveform.time.map((t: number) => toAbsoluteTime(sb, t)),
                        y: sb.waveform.amplitude,
                        type: 'scattergl',
                        mode: 'lines',
                        line: { color: '#1976d2', width: 1 },
                      }]}
                      layout={{
                        height: 100,
                        margin: { t: 5, b: 25, l: 30, r: 5 },
                        xaxis: { title: '', type: 'date', tickfont: { size: 7 }, tickformat: '%H:%M:%S' },
                        yaxis: { title: '', tickfont: { size: 8 } },
                        showlegend: false,
                      }}
                      config={{ staticPlot: true, responsive: true }}
                      style={{ width: '100%' }}
                      useResizeHandler
                    />

                    {/* FFT mini-plot */}
                    {sb.fft && (
                      <Plot
                        data={[{
                          x: sb.fft.frequencies,
                          y: sb.fft.magnitudes,
                          type: 'scatter',
                          mode: 'lines',
                          line: { color: '#ff6f00', width: 1 },
                        }]}
                        layout={{
                          height: 80,
                          margin: { t: 5, b: 20, l: 30, r: 5 },
                          xaxis: { title: '', range: [0, 300], tickfont: { size: 8 } },
                          yaxis: { title: '', tickfont: { size: 8 } },
                          showlegend: false,
                        }}
                        config={{ staticPlot: true, responsive: true }}
                        style={{ width: '100%' }}
                        useResizeHandler
                      />
                    )}

                    {/* Info chips */}
                    <Box display="flex" gap={0.5} flexWrap="wrap" mt={0.5}>
                      {sb.detection && (
                        <Chip label={`${sb.detection.fundamentalFrequency} Hz`}
                          size="small" color="primary" variant="outlined" />
                      )}
                      {sb.bearing && (
                        <Chip label={`${sb.bearing.bearing}°`}
                          size="small" variant="outlined" />
                      )}
                      {sb.detection && (
                        <Chip label={`${(sb.detection.confidence * 100).toFixed(0)}%`}
                          size="small"
                          color={sb.detection.confidence > 0.85 ? 'success' : 'warning'}
                        />
                      )}
                      <Chip label={`${sb.waveform.channels}ch`} size="small" variant="outlined" />
                    </Box>
                  </>
                ) : (
                  <Box sx={{ height: 180, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                    <Typography variant="caption" color="textSecondary">
                      {sb.active ? 'Loading...' : 'Inactive at this time'}
                    </Typography>
                  </Box>
                )}
              </CardContent>
            </Card>
          </Grid>
        ))}
          </Grid>
        </Grid>
      </Grid>
    </Box>
  );
};

export default LivePlayback;
