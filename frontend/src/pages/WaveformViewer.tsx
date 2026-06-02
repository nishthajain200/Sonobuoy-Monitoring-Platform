import React, { useEffect, useState } from 'react';
import { Box, Typography, FormGroup, FormControlLabel, Checkbox, CircularProgress } from '@mui/material';
import Plot from 'react-plotly.js';
import SonobuoySelector from '../components/SonobuoySelector';
import DateTimeRangePicker from '../components/DateTimeRangePicker';
import { getSonobuoys, getWaveform } from '../services/api';

const COLORS = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728'];

const WaveformViewer: React.FC = () => {
  const [sonobuoys, setSonobuoys] = useState<any[]>([]);
  const [selectedSb, setSelectedSb] = useState('');
  const [enabledChannels, setEnabledChannels] = useState([true, true, true, true]);
  const [waveData, setWaveData] = useState<any>(null);
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
    const chs = enabledChannels.map((e, i) => e ? i : -1).filter(i => i >= 0).join(',');
    getWaveform(selectedSb, chs).then(setWaveData).finally(() => setLoading(false));
  }, [selectedSb, enabledChannels]);

  const toggleChannel = (idx: number) => {
    const next = [...enabledChannels];
    next[idx] = !next[idx];
    setEnabledChannels(next);
  };

  // Convert relative seconds to absolute datetime strings
  const toAbsTime = (relSec: number) => {
    if (!waveData?.deploymentTime) return relSec;
    const base = new Date(waveData.deploymentTime).getTime();
    return new Date(base + relSec * 1000).toISOString();
  };

  const traces = waveData ? Object.entries(waveData.channels).map(([ch, d]: any) => ({
    x: d.time.map((t: number) => toAbsTime(t)),
    y: d.amplitude,
    type: 'scattergl' as const,
    mode: 'lines' as const,
    name: `Channel ${ch}`,
    line: { color: COLORS[parseInt(ch)] },
  })) : [];

  return (
    <Box p={3}>
      <Typography variant="h4" gutterBottom>Waveform Viewer</Typography>
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
        <FormGroup row>
          {[0, 1, 2, 3].map(i => (
            <FormControlLabel key={i} control={<Checkbox checked={enabledChannels[i]} onChange={() => toggleChannel(i)} />}
              label={`Ch ${i + 1}`} />
          ))}
        </FormGroup>
      </Box>
      {loading ? <CircularProgress /> : (
        <Plot
          data={traces}
          layout={{
            title: `Waveform – ${selectedSb}`,
            xaxis: { title: 'Time', type: waveData?.deploymentTime ? 'date' : undefined, rangeslider: {} },
            yaxis: { title: 'Amplitude' },
            height: 500,
            margin: { t: 40 },
          }}
          config={{ responsive: true }}
          style={{ width: '100%' }}
          useResizeHandler
        />
      )}
    </Box>
  );
};

export default WaveformViewer;
