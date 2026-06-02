import React, { useEffect, useState } from 'react';
import { Box, Typography, FormControl, InputLabel, Select, MenuItem, TextField, CircularProgress, Button } from '@mui/material';
import Plot from 'react-plotly.js';
import SonobuoySelector from '../components/SonobuoySelector';
import DateTimeRangePicker from '../components/DateTimeRangePicker';
import { getSonobuoys, getLofargram, runLofarMatch } from '../services/api';

const LofargramViewer: React.FC = () => {
  const [sonobuoys, setSonobuoys] = useState<any[]>([]);
  const [selectedSb, setSelectedSb] = useState('');
  const [channel, setChannel] = useState(0);
  const [freqMin, setFreqMin] = useState(0);
  const [freqMax, setFreqMax] = useState(250);
  const [specData, setSpecData] = useState<any>(null);
  const [matchResult, setMatchResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [fromDt, setFromDt] = useState('');
  const [toDt, setToDt] = useState('');

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
    getLofargram(selectedSb, channel, freqMin, freqMax).then(setSpecData).finally(() => setLoading(false));
  }, [selectedSb, channel, freqMin, freqMax]);

  const handleMatch = async () => {
    if (!selectedSb) return;
    const result = await runLofarMatch(selectedSb, channel);
    setMatchResult(result);
  };

  return (
    <Box p={3}>
      <Typography variant="h4" gutterBottom>LOFARgram / Spectrogram</Typography>
      <Box mb={2}>
        <DateTimeRangePicker
          fromDateTime={fromDt} toDateTime={toDt}
          onFromChange={setFromDt} onToChange={setToDt}
          onApply={loadSonobuoys}
          onClear={() => { setFromDt(''); setToDt(''); getSonobuoys().then(d => { setSonobuoys(d); if (d.length) setSelectedSb(d[0].id); }); }}
          label="Filter by Date/Time:"
        />
      </Box>
      <Box display="flex" gap={2} alignItems="center" mb={2} flexWrap="wrap">
        <SonobuoySelector sonobuoys={sonobuoys} selected={selectedSb} onChange={setSelectedSb} />
        <FormControl size="small" sx={{ minWidth: 120 }}>
          <InputLabel>Channel</InputLabel>
          <Select value={channel} label="Channel" onChange={e => setChannel(e.target.value as number)}>
            {[0, 1, 2, 3].map(i => <MenuItem key={i} value={i}>Channel {i + 1}</MenuItem>)}
          </Select>
        </FormControl>
        <TextField size="small" label="Min Freq" type="number" value={freqMin}
          onChange={e => setFreqMin(Number(e.target.value))} sx={{ width: 100 }} />
        <TextField size="small" label="Max Freq" type="number" value={freqMax}
          onChange={e => setFreqMax(Number(e.target.value))} sx={{ width: 100 }} />
        <Button variant="outlined" onClick={handleMatch}>Run LOFAR Match</Button>
      </Box>

      {loading ? <CircularProgress /> : specData && (
        <Plot
          data={[{
            z: specData.magnitudes,
            x: specData.deploymentTime
              ? specData.times.map((t: number) => new Date(new Date(specData.deploymentTime).getTime() + t * 1000).toISOString())
              : specData.times,
            y: specData.frequencies,
            type: 'heatmap',
            colorscale: 'Jet',
            colorbar: { title: 'dB' },
          }]}
          layout={{
            title: `LOFARgram – ${selectedSb} Ch ${channel + 1}`,
            xaxis: { title: 'Time', type: specData?.deploymentTime ? 'date' : undefined },
            yaxis: { title: 'Frequency (Hz)' },
            height: 500,
            margin: { t: 40 },
          }}
          config={{ responsive: true }}
          style={{ width: '100%' }}
          useResizeHandler
        />
      )}

      {matchResult && (
        <Box mt={2}>
          <Typography variant="h6">LOFAR Match Results</Typography>
          <Typography>Detected: {matchResult.detection?.fundamentalFrequency} Hz (confidence: {(matchResult.detection?.confidence * 100).toFixed(0)}%)</Typography>
          {matchResult.matches?.map((m: any, i: number) => (
            <Box key={i} mt={1} p={1} sx={{ bgcolor: '#f5f5f5', borderRadius: 1 }}>
              <Typography><strong>{m.platformType}</strong> ({m.signatureId}) – {(m.confidence * 100).toFixed(0)}% match</Typography>
              <Typography variant="body2">{m.description}</Typography>
            </Box>
          ))}
        </Box>
      )}
    </Box>
  );
};

export default LofargramViewer;
