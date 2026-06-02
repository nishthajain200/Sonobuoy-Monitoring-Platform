import React, { useEffect, useState } from 'react';
import { Box, Typography, FormControl, InputLabel, Select, MenuItem, CircularProgress, Card, CardContent, Chip } from '@mui/material';
import Plot from 'react-plotly.js';
import SonobuoySelector from '../components/SonobuoySelector';
import DateTimeRangePicker from '../components/DateTimeRangePicker';
import { getSonobuoys, getFFT, getHarmonics, getDetections } from '../services/api';

const FFTAnalysis: React.FC = () => {
  const [sonobuoys, setSonobuoys] = useState<any[]>([]);
  const [selectedSb, setSelectedSb] = useState('');
  const [channel, setChannel] = useState(0);
  const [fftData, setFftData] = useState<any>(null);
  const [harmonics, setHarmonics] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [fromDt, setFromDt] = useState('');
  const [toDt, setToDt] = useState('');

  const toIso = (local: string) => local ? new Date(local).toISOString() : undefined;

  const loadSonobuoys = () => {
    getSonobuoys().then(d => {
      const filtered = fromDt && toDt
        ? d.filter((sb: any) => {
            const t = new Date(sb.deploymentTime).getTime();
            return t >= new Date(fromDt).getTime() && t <= new Date(toDt).getTime();
          })
        : d;
      setSonobuoys(filtered);
      if (filtered.length && !filtered.find((s: any) => s.id === selectedSb)) {
        setSelectedSb(filtered[0].id);
      }
    });
  };

  useEffect(() => { loadSonobuoys(); }, []);

  useEffect(() => {
    if (!selectedSb) return;
    setLoading(true);
    Promise.all([
      getFFT(selectedSb, channel),
      getHarmonics(selectedSb, channel),
    ]).then(([fft, harm]) => {
      setFftData(fft);
      setHarmonics(harm);
    }).finally(() => setLoading(false));
  }, [selectedSb, channel]);

  const traces: any[] = [];
  if (fftData) {
    traces.push({
      x: fftData.frequencies,
      y: fftData.magnitudes,
      type: 'scatter',
      mode: 'lines',
      name: 'FFT',
      line: { color: '#1976d2' },
    });
    if (fftData.peaks?.length) {
      traces.push({
        x: fftData.peaks.map((p: any) => p.frequency),
        y: fftData.peaks.map((p: any) => p.amplitude),
        type: 'scatter',
        mode: 'markers',
        name: 'Peaks',
        marker: { color: '#d32f2f', size: 8 },
      });
    }
  }

  return (
    <Box p={3}>
      <Typography variant="h4" gutterBottom>FFT Analysis</Typography>
      <Box mb={2}>
        <DateTimeRangePicker
          fromDateTime={fromDt} toDateTime={toDt}
          onFromChange={setFromDt} onToChange={setToDt}
          onApply={loadSonobuoys}
          onClear={() => { setFromDt(''); setToDt(''); getSonobuoys().then(d => { setSonobuoys(d); if (d.length) setSelectedSb(d[0].id); }); }}
          label="Filter by Date/Time:"
        />
      </Box>
      <Box display="flex" gap={2} alignItems="center" mb={2}>
        <SonobuoySelector sonobuoys={sonobuoys} selected={selectedSb} onChange={setSelectedSb} />
        <FormControl size="small" sx={{ minWidth: 120 }}>
          <InputLabel>Channel</InputLabel>
          <Select value={channel} label="Channel" onChange={e => setChannel(e.target.value as number)}>
            {[0, 1, 2, 3].map(i => <MenuItem key={i} value={i}>Channel {i + 1}</MenuItem>)}
          </Select>
        </FormControl>
      </Box>

      {loading ? <CircularProgress /> : (
        <>
          <Plot
            data={traces}
            layout={{
              title: `FFT – ${selectedSb} Ch ${channel + 1}`,
              xaxis: { title: 'Frequency (Hz)', range: [0, 300] },
              yaxis: { title: 'Amplitude' },
              height: 450,
              margin: { t: 40 },
            }}
            config={{ responsive: true }}
            style={{ width: '100%' }}
            useResizeHandler
          />

          {harmonics && harmonics.fundamentalFrequency > 0 && (
            <Card sx={{ mt: 2, maxWidth: 500 }}>
              <CardContent>
                <Typography variant="h6">Harmonic Detection</Typography>
                <Typography>Fundamental: <strong>{harmonics.fundamentalFrequency} Hz</strong></Typography>
                <Box mt={1}>
                  Harmonics: {harmonics.harmonics?.map((h: number) => (
                    <Chip key={h} label={`${h} Hz`} size="small" sx={{ mr: 0.5 }} />
                  ))}
                </Box>
                <Typography mt={1}>Confidence: <strong>{(harmonics.confidence * 100).toFixed(0)}%</strong></Typography>
              </CardContent>
            </Card>
          )}
        </>
      )}
    </Box>
  );
};

export default FFTAnalysis;
