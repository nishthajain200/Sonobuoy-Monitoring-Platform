import React, { useEffect, useState } from 'react';
import { Box, Typography, CircularProgress, Card, CardContent, Grid, Chip } from '@mui/material';
import { MapContainer, TileLayer, CircleMarker, Popup, Polyline, Circle, Tooltip as LTooltip } from 'react-leaflet';
import DateTimeRangePicker from '../components/DateTimeRangePicker';
import { getSonobuoys, getBearing, getCorrelations, getDetections, getLofarMatches } from '../services/api';

const TacticalMap: React.FC = () => {
  const [sonobuoys, setSonobuoys] = useState<any[]>([]);
  const [bearings, setBearings] = useState<Record<string, any>>({});
  const [correlations, setCorrelations] = useState<any[]>([]);
  const [detections, setDetections] = useState<Record<string, any>>({});
  const [lofarMatches, setLofarMatches] = useState<Record<string, any>>({});
  const [loading, setLoading] = useState(true);
  const [fromDt, setFromDt] = useState('');
  const [toDt, setToDt] = useState('');

  const loadData = (from?: string, to?: string) => {
    setLoading(true);
    const corrFrom = from ? new Date(from).toISOString() : undefined;
    const corrTo = to ? new Date(to).toISOString() : undefined;
    Promise.all([
      getSonobuoys(),
      getCorrelations(corrFrom, corrTo),
      getDetections(undefined, corrFrom, corrTo),
      getLofarMatches(undefined, corrFrom, corrTo),
    ]).then(async ([sbs, corrs, dets, matches]) => {
      const filteredSbs = from && to
        ? sbs.filter((sb: any) => {
            const t = new Date(sb.deploymentTime).getTime();
            return t >= new Date(from).getTime() && t <= new Date(to).getTime();
          })
        : sbs;
      setSonobuoys(filteredSbs);
      setCorrelations(corrs);

      // Group detections by sonobuoy
      const detMap: Record<string, any> = {};
      dets.forEach((d: any) => { if (!detMap[d.sonobuoyId]) detMap[d.sonobuoyId] = d; });
      setDetections(detMap);

      // Group LOFAR matches by sonobuoy
      const matchMap: Record<string, any> = {};
      matches.forEach((m: any) => { if (!matchMap[m.sonobuoyId]) matchMap[m.sonobuoyId] = m; });
      setLofarMatches(matchMap);

      const bMap: Record<string, any> = {};
      for (const sb of filteredSbs) {
        try {
          const b = await getBearing(sb.id);
          if (b?.length) bMap[sb.id] = b[0];
        } catch {}
      }
      setBearings(bMap);
    }).finally(() => setLoading(false));
  };

  useEffect(() => { loadData(); }, []);

  if (loading) return <Box p={4}><CircularProgress /></Box>;

  const center: [number, number] = sonobuoys.length
    ? [sonobuoys.reduce((s, b) => s + b.latitude, 0) / sonobuoys.length,
       sonobuoys.reduce((s, b) => s + b.longitude, 0) / sonobuoys.length]
    : [12.85, 72.97];

  // Compute bearing lines (extend 0.02 degrees in bearing direction)
  const bearingLines: { positions: [number, number][]; color: string }[] = [];
  sonobuoys.forEach(sb => {
    const b = bearings[sb.id];
    if (!b) return;
    const rad = (b.bearing * Math.PI) / 180;
    const len = 0.03;
    const endLat = sb.latitude + len * Math.cos(rad);
    const endLon = sb.longitude + len * Math.sin(rad);
    bearingLines.push({
      positions: [[sb.latitude, sb.longitude], [endLat, endLon]],
      color: '#d32f2f',
    });
  });

  // Correlated sonobuoy pairs
  const corrLines: { positions: [number, number][]; score: number }[] = [];
  correlations.filter(c => c.correlationScore > 50).forEach(c => {
    const a = sonobuoys.find(s => s.id === c.sonobuoyA);
    const b = sonobuoys.find(s => s.id === c.sonobuoyB);
    if (a && b) {
      corrLines.push({
        positions: [[a.latitude, a.longitude], [b.latitude, b.longitude]],
        score: c.correlationScore,
      });
    }
  });

  // Probable target zone: average of bearing line endpoints
  let targetCenter: [number, number] | null = null;
  if (bearingLines.length >= 2) {
    const ends = bearingLines.map(l => l.positions[1]);
    targetCenter = [
      ends.reduce((s, e) => s + e[0], 0) / ends.length,
      ends.reduce((s, e) => s + e[1], 0) / ends.length,
    ];
  }

  return (
    <Box p={3}>
      <Typography variant="h4" gutterBottom>Tactical Map</Typography>
      <Box mb={2}>
        <DateTimeRangePicker
          fromDateTime={fromDt} toDateTime={toDt}
          onFromChange={setFromDt} onToChange={setToDt}
          onApply={() => loadData(fromDt, toDt)}
          onClear={() => { setFromDt(''); setToDt(''); loadData(); }}
          label="Filter by Date/Time:"
        />
      </Box>

      <Grid container spacing={2}>
        {/* Map */}
        <Grid item xs={12} md={8}>
          <Box sx={{ height: 600, border: '1px solid #ccc', borderRadius: 1 }}>
            <MapContainer center={center} zoom={13} style={{ height: '100%', width: '100%' }}>
              <TileLayer
                attribution='&copy; OpenStreetMap'
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
              />
              {sonobuoys.map(sb => (
                <CircleMarker
                  key={sb.id}
                  center={[sb.latitude, sb.longitude]}
                  radius={12}
                  fillColor={sb.status === 'Active' ? '#1976d2' : '#9e9e9e'}
                  color="#0d47a1"
                  weight={2}
                  fillOpacity={0.85}
                >
                  <LTooltip permanent direction="top" offset={[0, -10]}>
                    <strong>{sb.id}</strong>
                  </LTooltip>
                  <Popup>
                    <strong>{sb.id}</strong> – {sb.name}<br />
                    Status: {sb.status}<br />
                    Deployed: {sb.deploymentTime ? new Date(sb.deploymentTime).toLocaleString() : 'N/A'}<br />
                    {bearings[sb.id] && <>Bearing: {bearings[sb.id].bearing}°<br /></>}
                    {detections[sb.id] && <>Frequency: {detections[sb.id].fundamentalFrequency} Hz<br />
                    Confidence: {(detections[sb.id].confidence * 100).toFixed(0)}%<br /></>}
                  </Popup>
                </CircleMarker>
              ))}
              {bearingLines.map((line, i) => (
                <Polyline key={`b-${i}`} positions={line.positions} color="#d32f2f" weight={2} />
              ))}
              {corrLines.map((line, i) => (
                <Polyline key={`c-${i}`} positions={line.positions} color="#1976d2"
                  weight={1} dashArray="5 5" />
              ))}
              {targetCenter && (
                <Circle center={targetCenter} radius={500} color="#ff9800"
                  fillColor="#ff9800" fillOpacity={0.2} />
              )}
            </MapContainer>
          </Box>
        </Grid>

        {/* Sonobuoy Info Panel */}
        <Grid item xs={12} md={4}>
          <Typography variant="h6" gutterBottom>Sonobuoy Details</Typography>
          <Box sx={{ maxHeight: 570, overflow: 'auto' }}>
            {sonobuoys.map(sb => (
              <Card key={sb.id} sx={{ mb: 1, borderLeft: `4px solid ${sb.status === 'Active' ? '#1976d2' : '#9e9e9e'}` }}>
                <CardContent sx={{ py: 1, '&:last-child': { pb: 1 } }}>
                  <Typography variant="subtitle2">{sb.id} – {sb.name}</Typography>
                  <Typography variant="caption" display="block">
                    {sb.latitude.toFixed(4)}°N, {sb.longitude.toFixed(4)}°E
                  </Typography>
                  <Typography variant="caption" display="block">
                    Deployed: {sb.deploymentTime ? new Date(sb.deploymentTime).toLocaleString() : '—'}
                  </Typography>
                  <Box display="flex" gap={0.5} flexWrap="wrap" mt={0.5}>
                    <Chip label={sb.status} size="small"
                      color={sb.status === 'Active' ? 'success' : 'default'} variant="outlined" />
                    {bearings[sb.id] && (
                      <Chip label={`${bearings[sb.id].bearing}°`} size="small" variant="outlined" />
                    )}
                    {detections[sb.id] && (
                      <Chip label={`${detections[sb.id].fundamentalFrequency} Hz`} size="small" color="primary" variant="outlined" />
                    )}
                    {detections[sb.id] && (
                      <Chip label={`${(detections[sb.id].confidence * 100).toFixed(0)}%`} size="small"
                        color={detections[sb.id].confidence > 0.85 ? 'success' : 'warning'} />
                    )}
                  </Box>
                </CardContent>
              </Card>
            ))}
          </Box>

          {/* Legend */}
          <Card sx={{ mt: 2 }}>
            <CardContent sx={{ py: 1, '&:last-child': { pb: 1 } }}>
              <Typography variant="subtitle2" gutterBottom>Legend</Typography>
              <Box display="flex" gap={1} flexWrap="wrap">
                <Chip size="small" sx={{ bgcolor: '#1976d2', color: '#fff' }} label="Active Sonobuoy" />
                <Chip size="small" sx={{ bgcolor: '#d32f2f', color: '#fff' }} label="Bearing Line" />
                <Chip size="small" sx={{ bgcolor: '#1976d2', color: '#fff' }} label="Correlation Link" variant="outlined" />
                <Chip size="small" sx={{ bgcolor: '#ff9800', color: '#fff' }} label="Target Zone" />
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
};

export default TacticalMap;
