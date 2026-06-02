import React, { useEffect, useState } from 'react';
import { Box, Typography, Button, Select, MenuItem, FormControl, InputLabel, Alert, CircularProgress, Card, CardContent, TextField } from '@mui/material';
import { CloudUpload } from '@mui/icons-material';
import { getSonobuoys, ingestFile } from '../services/api';

const DataIngestion: React.FC = () => {
  const [sonobuoys, setSonobuoys] = useState<any[]>([]);
  const [selectedSb, setSelectedSb] = useState('');
  const [file, setFile] = useState<File | null>(null);
  const [timestamp, setTimestamp] = useState('');
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState('');

  useEffect(() => { getSonobuoys().then(setSonobuoys).catch(() => {}); }, []);

  const handleUpload = async () => {
    if (!selectedSb || !file) return;
    setUploading(true);
    setError('');
    setResult(null);
    try {
      const ts = timestamp ? new Date(timestamp).toISOString() : undefined;
      const res = await ingestFile(selectedSb, file, ts);
      setResult(res);
    } catch (e: any) {
      setError(e.response?.data?.detail || 'Upload failed');
    } finally {
      setUploading(false);
    }
  };

  return (
    <Box p={3}>
      <Typography variant="h4" gutterBottom>Data Ingestion</Typography>
      <Card sx={{ maxWidth: 600 }}>
        <CardContent>
          <Box display="flex" flexDirection="column" gap={2}>
            <FormControl size="small">
              <InputLabel>Sonobuoy</InputLabel>
              <Select value={selectedSb} label="Sonobuoy" onChange={e => setSelectedSb(e.target.value as string)}>
                {sonobuoys.map(sb => (
                  <MenuItem key={sb.id} value={sb.id}>{sb.id} – {sb.name}</MenuItem>
                ))}
              </Select>
            </FormControl>

            <TextField
              size="small"
              label="Recording Timestamp"
              type="datetime-local"
              value={timestamp}
              onChange={e => setTimestamp(e.target.value)}
              InputLabelProps={{ shrink: true }}
              helperText="When this recording was captured (used for time-based playback)"
            />

            <Button variant="outlined" component="label" startIcon={<CloudUpload />}>
              Select WAV File
              <input type="file" hidden accept=".wav" onChange={e => setFile(e.target.files?.[0] || null)} />
            </Button>
            {file && <Typography variant="body2">Selected: {file.name}</Typography>}

            <Button variant="contained" onClick={handleUpload} disabled={!selectedSb || !file || uploading}>
              {uploading ? <CircularProgress size={20} /> : 'Upload & Ingest'}
            </Button>

            {error && <Alert severity="error">{error}</Alert>}
            {result && (
              <Alert severity="success">
                Ingested: {result.channels} channels, {result.sampleRate} Hz, {result.duration}s
                {result.timestamp && <><br/>Timestamp: {result.timestamp}</>}
              </Alert>
            )}
          </Box>
        </CardContent>
      </Card>
    </Box>
  );
};

export default DataIngestion;
