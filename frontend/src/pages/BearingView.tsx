import React, { useEffect, useState } from 'react';
import { Box, Typography, CircularProgress, Card, CardContent, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Paper } from '@mui/material';
import Plot from 'react-plotly.js';
import SonobuoySelector from '../components/SonobuoySelector';
import DateTimeRangePicker from '../components/DateTimeRangePicker';
import { getSonobuoys, getBearingAllChannels } from '../services/api';

const PAIR_COLORS = ['#d32f2f', '#1976d2', '#388e3c', '#f57c00', '#7b1fa2', '#00838f'];

const BearingView: React.FC = () => {
  const [sonobuoys, setSonobuoys] = useState<any[]>([]);
  const [selectedSb, setSelectedSb] = useState('');
  const [bearingData, setBearingData] = useState<any>(null);
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
    getBearingAllChannels(selectedSb).then(setBearingData).finally(() => setLoading(false));
  }, [selectedSb]);

  const pairs: any[] = bearingData?.channelPairs ?? [];
  const combined = bearingData?.combined;

  // Build one polar trace per channel pair + combined
  const traces: any[] = pairs.map((p: any, i: number) => ({
    type: 'scatterpolar' as const,
    mode: 'markers+lines+text' as const,
    r: [0, p.confidence * 100],
    theta: [0, p.bearing],
    text: ['', `${p.label}\n${p.bearing}°`],
    textposition: 'top center',
    textfont: { size: 11, color: PAIR_COLORS[i % PAIR_COLORS.length] },
    name: p.label,
    marker: { size: 10, color: PAIR_COLORS[i % PAIR_COLORS.length] },
    line: { color: PAIR_COLORS[i % PAIR_COLORS.length], width: 2 },
  }));

  if (combined) {
    traces.push({
      type: 'scatterpolar' as const,
      mode: 'markers+lines+text' as const,
      r: [0, combined.confidence * 100],
      theta: [0, combined.bearing],
      text: ['', `Combined\n${combined.bearing}°`],
      textposition: 'top center',
      textfont: { size: 13, color: '#000', weight: 700 },
      name: 'Combined',
      marker: { size: 14, color: '#000', symbol: 'diamond' },
      line: { color: '#000', width: 3, dash: 'dash' },
    });
  }

  return (
    <Box p={3}>
      <Typography variant="h4" gutterBottom>Bearing / Polar View – All Channels</Typography>
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
        {bearingData && (
          <Typography variant="body2" color="text.secondary">
            {bearingData.totalChannels} channels &middot; {pairs.length} channel pairs
          </Typography>
        )}
      </Box>

      {loading ? <CircularProgress /> : (
        <Box display="flex" gap={3} flexWrap="wrap">
          <Plot
            data={traces}
            layout={{
              title: `Bearing – ${selectedSb} (All Channel Pairs)`,
              polar: {
                radialaxis: { visible: true, range: [0, 100], title: 'Confidence %' },
                angularaxis: {
                  direction: 'clockwise',
                  rotation: 90,
                  dtick: 15,
                  tickfont: { size: 10 },
                  tickvals: [0, 15, 30, 45, 60, 75, 90, 105, 120, 135, 150, 165, 180, 195, 210, 225, 240, 255, 270, 285, 300, 315, 330, 345],
                  ticktext: ['0° (N)', '15°', '30°', '45° (NE)', '60°', '75°', '90° (E)', '105°', '120°', '135° (SE)', '150°', '165°', '180° (S)', '195°', '210°', '225° (SW)', '240°', '255°', '270° (W)', '285°', '300°', '315° (NW)', '330°', '345°'],
                },
              },
              height: 550,
              width: 600,
              margin: { t: 50 },
              legend: { x: 1.05, y: 1 },
            }}
            config={{ responsive: true }}
          />

          <Box display="flex" flexDirection="column" gap={2} sx={{ minWidth: 320 }}>
            {combined && (
              <Card>
                <CardContent>
                  <Typography variant="h6">Combined Bearing</Typography>
                  <Typography>Sonobuoy: <strong>{bearingData.sonobuoyId}</strong></Typography>
                  <Typography>Bearing: <strong>{combined.bearing}°</strong></Typography>
                  <Typography>Confidence: <strong>{(combined.confidence * 100).toFixed(0)}%</strong></Typography>
                  <Typography>Frequency: <strong>{combined.frequency} Hz</strong></Typography>
                </CardContent>
              </Card>
            )}

            {pairs.length > 0 && (
              <TableContainer component={Paper}>
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>Channel Pair</TableCell>
                      <TableCell align="right">Bearing (°)</TableCell>
                      <TableCell align="right">Confidence</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {pairs.map((p: any, i: number) => (
                      <TableRow key={i}>
                        <TableCell>
                          <Box display="flex" alignItems="center" gap={1}>
                            <Box sx={{ width: 12, height: 12, borderRadius: '50%', backgroundColor: PAIR_COLORS[i % PAIR_COLORS.length] }} />
                            {p.label}
                          </Box>
                        </TableCell>
                        <TableCell align="right">{p.bearing}°</TableCell>
                        <TableCell align="right">{(p.confidence * 100).toFixed(0)}%</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            )}
          </Box>
        </Box>
      )}
    </Box>
  );
};

export default BearingView;
