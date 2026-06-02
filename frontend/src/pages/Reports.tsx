import React, { useState } from 'react';
import { Box, Typography, Button, Card, CardContent, Grid, CircularProgress } from '@mui/material';
import { Download } from '@mui/icons-material';
import { downloadDetectionsCSV, downloadSonobuoysCSV, downloadCorrelationsCSV, getMissionSummary } from '../services/api';

const downloadBlob = (blob: Blob, filename: string) => {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
};

const Reports: React.FC = () => {
  const [summary, setSummary] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  const handleDownload = async (type: string) => {
    try {
      let blob: Blob;
      let filename: string;
      switch (type) {
        case 'detections':
          blob = await downloadDetectionsCSV();
          filename = 'detections.csv';
          break;
        case 'sonobuoys':
          blob = await downloadSonobuoysCSV();
          filename = 'sonobuoys.csv';
          break;
        case 'correlations':
          blob = await downloadCorrelationsCSV();
          filename = 'correlations.csv';
          break;
        default:
          return;
      }
      downloadBlob(blob, filename);
    } catch (e) {
      console.error('Download failed', e);
    }
  };

  const handleMissionSummary = async () => {
    setLoading(true);
    try {
      const data = await getMissionSummary();
      setSummary(data);
      // Also download as JSON
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
      downloadBlob(blob, 'mission_summary.json');
    } finally {
      setLoading(false);
    }
  };

  const exports = [
    { label: 'Detection Summary CSV', key: 'detections', desc: 'All detected acoustic contacts with frequencies and confidence' },
    { label: 'Sonobuoy Metadata CSV', key: 'sonobuoys', desc: 'All sonobuoy configuration and deployment data' },
    { label: 'Correlation Results CSV', key: 'correlations', desc: 'Multi-sonobuoy correlation scores' },
  ];

  return (
    <Box p={3}>
      <Typography variant="h4" gutterBottom>Reports</Typography>

      <Grid container spacing={2}>
        {exports.map(exp => (
          <Grid item xs={12} sm={6} md={4} key={exp.key}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>{exp.label}</Typography>
                <Typography variant="body2" color="textSecondary" gutterBottom>{exp.desc}</Typography>
                <Button variant="outlined" startIcon={<Download />} onClick={() => handleDownload(exp.key)}>
                  Download
                </Button>
              </CardContent>
            </Card>
          </Grid>
        ))}

        <Grid item xs={12} sm={6} md={4}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>Mission Summary JSON</Typography>
              <Typography variant="body2" color="textSecondary" gutterBottom>Complete mission summary with dashboard, events and sonobuoy data</Typography>
              <Button variant="outlined" startIcon={loading ? <CircularProgress size={16} /> : <Download />}
                onClick={handleMissionSummary} disabled={loading}>
                Download
              </Button>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {summary && (
        <Card sx={{ mt: 3 }}>
          <CardContent>
            <Typography variant="h6" gutterBottom>Mission Summary Preview</Typography>
            <Typography>Total Sonobuoys: {summary.dashboard?.totalSonobuoys}</Typography>
            <Typography>Total Detections: {summary.dashboard?.totalDetections}</Typography>
            <Typography>Active Recordings: {summary.dashboard?.activeRecordings}</Typography>
            <Typography>LOFAR Matches: {summary.dashboard?.totalLofarMatches}</Typography>
            <Typography>Events: {summary.events?.length}</Typography>
          </CardContent>
        </Card>
      )}
    </Box>
  );
};

export default Reports;
