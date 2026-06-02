import React, { useEffect, useState } from 'react';
import { Box, Card, CardContent, Typography, Grid, Chip, Button, CircularProgress } from '@mui/material';
import { getDashboard, generateSampleData } from '../services/api';
import DateTimeRangePicker from '../components/DateTimeRangePicker';

const Dashboard: React.FC = () => {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [fromDt, setFromDt] = useState('');
  const [toDt, setToDt] = useState('');
  const [filterFrom, setFilterFrom] = useState('');
  const [filterTo, setFilterTo] = useState('');

  const toIso = (local: string) => local ? new Date(local).toISOString() : undefined;

  const load = (from?: string, to?: string) => {
    setLoading(true);
    getDashboard(toIso(from), toIso(to)).then(setData).catch(() => setData(null)).finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  const handleGenerate = async () => {
    setGenerating(true);
    try {
      await generateSampleData(toIso(fromDt), toIso(toDt));
      load(filterFrom, filterTo);
    } finally {
      setGenerating(false);
    }
  };

  const handleFilterApply = () => {
    setFilterFrom(fromDt);
    setFilterTo(toDt);
    load(fromDt, toDt);
  };

  const handleFilterClear = () => {
    setFromDt('');
    setToDt('');
    setFilterFrom('');
    setFilterTo('');
    load();
  };

  if (loading) return <Box p={4}><CircularProgress /></Box>;

  const stats = [
    { label: 'Total Sonobuoys', value: data?.totalSonobuoys ?? 0, color: '#1976d2' },
    { label: 'Total Channels', value: data?.totalChannels ?? 0, color: '#388e3c' },
    { label: 'Active Recordings', value: data?.activeRecordings ?? 0, color: '#f57c00' },
    { label: 'Detected Contacts', value: data?.detectedContacts ?? 0, color: '#d32f2f' },
    { label: 'Total Detections', value: data?.totalDetections ?? 0, color: '#7b1fa2' },
    { label: 'LOFAR Matches', value: data?.totalLofarMatches ?? 0, color: '#00796b' },
    { label: 'Avg Correlation', value: `${data?.averageCorrelationScore ?? 0}%`, color: '#5d4037' },
  ];

  return (
    <Box p={3}>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
        <Typography variant="h4">Dashboard</Typography>
        <Button variant="contained" onClick={handleGenerate} disabled={generating}>
          {generating ? 'Generating...' : 'Generate Sample Data'}
        </Button>
      </Box>

      <Box mb={3}>
        <DateTimeRangePicker
          fromDateTime={fromDt}
          toDateTime={toDt}
          onFromChange={setFromDt}
          onToChange={setToDt}
          onApply={handleFilterApply}
          onClear={handleFilterClear}
          label="Date/Time Range:"
        />
        <Typography variant="caption" color="textSecondary" sx={{ mt: 0.5, display: 'block' }}>
          Set date range before generating sample data, or use it to filter the dashboard view.
        </Typography>
      </Box>

      <Grid container spacing={2}>
        {stats.map(s => (
          <Grid item xs={12} sm={6} md={3} key={s.label}>
            <Card sx={{ borderLeft: `4px solid ${s.color}` }}>
              <CardContent>
                <Typography color="textSecondary" gutterBottom>{s.label}</Typography>
                <Typography variant="h4">{s.value}</Typography>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>

      {data?.highestConfidenceMatch && (
        <Card sx={{ mt: 3 }}>
          <CardContent>
            <Typography variant="h6" gutterBottom>Highest Confidence LOFAR Match</Typography>
            <Typography>Sonobuoy: <Chip label={data.highestConfidenceMatch.sonobuoyId} size="small" /></Typography>
            <Typography>Platform: {data.highestConfidenceMatch.platformType}</Typography>
            <Typography>Confidence: {(data.highestConfidenceMatch.confidence * 100).toFixed(0)}%</Typography>
          </CardContent>
        </Card>
      )}
    </Box>
  );
};

export default Dashboard;
