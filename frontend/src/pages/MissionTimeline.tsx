import React, { useEffect, useState } from 'react';
import {
  Box, Typography, CircularProgress, Slider, FormControl, InputLabel,
  Select, MenuItem, Card, CardContent, Chip, TextField
} from '@mui/material';
import Plot from 'react-plotly.js';
import DateTimeRangePicker from '../components/DateTimeRangePicker';
import { getSonobuoys, getEvents } from '../services/api';

const MissionTimeline: React.FC = () => {
  const [sonobuoys, setSonobuoys] = useState<any[]>([]);
  const [events, setEvents] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [filterSb, setFilterSb] = useState('');
  const [filterFreq, setFilterFreq] = useState('');
  const [filterConf, setFilterConf] = useState(0);
  const [selectedEvent, setSelectedEvent] = useState<any>(null);
  const [fromDt, setFromDt] = useState('');
  const [toDt, setToDt] = useState('');

  const toIso = (local: string) => local ? new Date(local).toISOString() : undefined;

  const loadData = (from?: string, to?: string) => {
    setLoading(true);
    const evtParams: any = {};
    if (from) evtParams.from_datetime = new Date(from).toISOString();
    if (to) evtParams.to_datetime = new Date(to).toISOString();
    Promise.all([getSonobuoys(), getEvents(evtParams)]).then(([sbs, evts]) => {
      const filteredSbs = from && to
        ? sbs.filter((sb: any) => {
            const t = new Date(sb.deploymentTime).getTime();
            return t >= new Date(from).getTime() && t <= new Date(to).getTime();
          })
        : sbs;
      setSonobuoys(filteredSbs);
      setEvents(evts);
    }).finally(() => setLoading(false));
  };

  useEffect(() => { loadData(); }, []);

  const filteredEvents = events.filter(e => {
    if (filterSb && e.sonobuoyId !== filterSb) return false;
    if (filterFreq && e.fundamentalFrequency !== Number(filterFreq)) return false;
    if (filterConf && e.confidence < filterConf) return false;
    return true;
  });

  // Build timeline traces – one row per sonobuoy
  const sbIds = sonobuoys.map(s => s.id);
  const traces = sbIds.map((sbId, idx) => {
    const sbEvents = filteredEvents.filter(e => e.sonobuoyId === sbId);
    return {
      x: sbEvents.map(e => e.timestamp),
      y: sbEvents.map(() => sbId),
      text: sbEvents.map(e =>
        `${e.eventType}: ${e.fundamentalFrequency}Hz\nBearing: ${e.bearing}°\nConfidence: ${(e.confidence * 100).toFixed(0)}%\nMatch: ${e.lofarMatch || 'N/A'}`
      ),
      mode: 'markers' as const,
      type: 'scatter' as const,
      name: sbId,
      marker: {
        size: 14,
        symbol: 'diamond',
        color: sbEvents.map(e => e.confidence * 100),
        colorscale: 'RdYlGn',
        cmin: 0,
        cmax: 100,
        line: { width: 1, color: '#333' },
      },
      customdata: sbEvents,
    };
  });

  // Add recording duration bars
  const recordingTraces = sonobuoys.map(sb => ({
    x: [sb.deploymentTime, new Date(new Date(sb.deploymentTime).getTime() + (sb.recordingDuration || 30) * 1000).toISOString()],
    y: [sb.id, sb.id],
    mode: 'lines' as const,
    type: 'scatter' as const,
    name: `${sb.id} recording`,
    line: { color: '#e0e0e0', width: 8 },
    showlegend: false,
    hoverinfo: 'skip' as const,
  }));

  return (
    <Box p={3}>
      <Typography variant="h4" gutterBottom>Mission Timeline</Typography>

      <Box mb={2}>
        <DateTimeRangePicker
          fromDateTime={fromDt} toDateTime={toDt}
          onFromChange={setFromDt} onToChange={setToDt}
          onApply={() => loadData(fromDt, toDt)}
          onClear={() => { setFromDt(''); setToDt(''); loadData(); }}
          label="Filter by Date/Time:"
        />
      </Box>

      <Box display="flex" gap={2} mb={2} flexWrap="wrap" alignItems="center">
        <FormControl size="small" sx={{ minWidth: 150 }}>
          <InputLabel>Sonobuoy</InputLabel>
          <Select value={filterSb} label="Sonobuoy" onChange={e => setFilterSb(e.target.value)}>
            <MenuItem value="">All</MenuItem>
            {sonobuoys.map(s => <MenuItem key={s.id} value={s.id}>{s.id}</MenuItem>)}
          </Select>
        </FormControl>
        <TextField size="small" label="Frequency (Hz)" type="number" value={filterFreq}
          onChange={e => setFilterFreq(e.target.value)} sx={{ width: 130 }} />
        <Box sx={{ width: 200 }}>
          <Typography variant="caption">Min Confidence: {(filterConf * 100).toFixed(0)}%</Typography>
          <Slider size="small" min={0} max={1} step={0.05} value={filterConf}
            onChange={(_, v) => setFilterConf(v as number)} />
        </Box>
      </Box>

      {loading ? <CircularProgress /> : (
        <>
          <Plot
            data={[...recordingTraces, ...traces] as any}
            layout={{
              title: 'Mission Timeline',
              xaxis: { title: 'Time', type: 'date' },
              yaxis: { title: 'Sonobuoy', type: 'category', categoryorder: 'array', categoryarray: sbIds },
              height: 450,
              margin: { t: 40, l: 80 },
              hovermode: 'closest',
            }}
            config={{ responsive: true }}
            style={{ width: '100%' }}
            useResizeHandler
            onUpdate={(fig: any) => {
              // Handle click on event
            }}
          />

          {selectedEvent && (
            <Card sx={{ mt: 2, maxWidth: 500 }}>
              <CardContent>
                <Typography variant="h6">Event Details</Typography>
                <Typography>Event ID: {selectedEvent.eventId}</Typography>
                <Typography>Sonobuoy: {selectedEvent.sonobuoyId}</Typography>
                <Typography>Time: {selectedEvent.timestamp}</Typography>
                <Typography>Frequency: {selectedEvent.fundamentalFrequency} Hz</Typography>
                <Typography>Bearing: {selectedEvent.bearing}°</Typography>
                <Typography>Confidence: {(selectedEvent.confidence * 100).toFixed(0)}%</Typography>
                <Typography>LOFAR Match: {selectedEvent.lofarMatch}</Typography>
              </CardContent>
            </Card>
          )}

          <Box mt={2}>
            <Typography variant="h6" gutterBottom>Events List</Typography>
            {filteredEvents.map((e: any) => (
              <Card key={e.eventId} sx={{ mb: 1, cursor: 'pointer', '&:hover': { bgcolor: '#f5f5f5' } }}
                onClick={() => setSelectedEvent(e)}>
                <CardContent sx={{ py: 1, '&:last-child': { pb: 1 } }}>
                  <Box display="flex" gap={1} alignItems="center" flexWrap="wrap">
                    <Chip label={e.sonobuoyId} size="small" color="primary" />
                    <Chip label={`${e.fundamentalFrequency} Hz`} size="small" />
                    <Chip label={`${e.bearing}°`} size="small" variant="outlined" />
                    <Chip label={`${(e.confidence * 100).toFixed(0)}%`} size="small"
                      color={e.confidence > 0.85 ? 'success' : 'warning'} />
                    {e.lofarMatch && <Chip label={e.lofarMatch} size="small" variant="outlined" />}
                    <Typography variant="caption" color="textSecondary">{e.timestamp}</Typography>
                  </Box>
                </CardContent>
              </Card>
            ))}
          </Box>
        </>
      )}
    </Box>
  );
};

export default MissionTimeline;
