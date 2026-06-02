import React, { useEffect, useState } from 'react';
import { Box, Typography, CircularProgress, Card, CardContent } from '@mui/material';
import Plot from 'react-plotly.js';
import SonobuoySelector from '../components/SonobuoySelector';
import DateTimeRangePicker from '../components/DateTimeRangePicker';
import { getSonobuoys, getBearing } from '../services/api';

const BearingView: React.FC = () => {
  const [sonobuoys, setSonobuoys] = useState<any[]>([]);
  const [selectedSb, setSelectedSb] = useState('');
  const [bearingData, setBearingData] = useState<any[]>([]);
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
    getBearing(selectedSb).then(setBearingData).finally(() => setLoading(false));
  }, [selectedSb]);

  const primary = bearingData?.[0];

  return (
    <Box p={3}>
      <Typography variant="h4" gutterBottom>Bearing / Polar View</Typography>
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
      </Box>

      {loading ? <CircularProgress /> : (
        <Box display="flex" gap={3} flexWrap="wrap">
          <Plot
            data={[{
              type: 'scatterpolar',
              mode: 'lines+markers',
              r: bearingData.map(b => b.confidence * 100),
              theta: bearingData.map(b => b.bearing),
              text: bearingData.map(b => `${b.frequency} Hz`),
              marker: { size: 12, color: '#d32f2f' },
              line: { color: '#1976d2' },
            }]}
            layout={{
              title: `Bearing – ${selectedSb}`,
              polar: {
                radialaxis: { visible: true, range: [0, 100], title: 'Confidence %' },
                angularaxis: { direction: 'clockwise', rotation: 90 },
              },
              height: 500,
              width: 500,
              margin: { t: 50 },
              showlegend: false,
            }}
            config={{ responsive: true }}
          />

          {primary && (
            <Card sx={{ minWidth: 250, alignSelf: 'flex-start' }}>
              <CardContent>
                <Typography variant="h6">Bearing Details</Typography>
                <Typography>Sonobuoy: <strong>{primary.sonobuoyId}</strong></Typography>
                <Typography>Bearing: <strong>{primary.bearing}°</strong></Typography>
                <Typography>Confidence: <strong>{(primary.confidence * 100).toFixed(0)}%</strong></Typography>
                <Typography>Frequency: <strong>{primary.frequency} Hz</strong></Typography>
              </CardContent>
            </Card>
          )}
        </Box>
      )}
    </Box>
  );
};

export default BearingView;
