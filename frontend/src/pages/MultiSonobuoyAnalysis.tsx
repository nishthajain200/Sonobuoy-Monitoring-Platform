import React, { useEffect, useState } from 'react';
import {
  Box, Typography, Button, CircularProgress, Checkbox, FormControlLabel,
  FormGroup, Table, TableBody, TableCell, TableContainer, TableHead,
  TableRow, Paper, Chip
} from '@mui/material';
import DateTimeRangePicker from '../components/DateTimeRangePicker';
import { getSonobuoys, runCorrelation, getCorrelations } from '../services/api';

const MultiSonobuoyAnalysis: React.FC = () => {
  const [sonobuoys, setSonobuoys] = useState<any[]>([]);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [correlations, setCorrelations] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [fromDt, setFromDt] = useState('');
  const [toDt, setToDt] = useState('');

  const toIso = (local: string) => local ? new Date(local).toISOString() : undefined;

  const loadData = (from?: string, to?: string) => {
    getSonobuoys().then(d => {
      const filtered = from && to
        ? d.filter((sb: any) => {
            const t = new Date(sb.deploymentTime).getTime();
            return t >= new Date(from).getTime() && t <= new Date(to).getTime();
          })
        : d;
      setSonobuoys(filtered);
    });
    getCorrelations(from ? new Date(from).toISOString() : undefined, to ? new Date(to).toISOString() : undefined)
      .then(setCorrelations).catch(() => {});
  };

  useEffect(() => { loadData(); }, []);

  const toggle = (id: string) => {
    const next = new Set(selected);
    if (next.has(id)) next.delete(id); else next.add(id);
    setSelected(next);
  };

  const handleCorrelate = async () => {
    const ids = Array.from(selected);
    if (ids.length < 2) return;
    setLoading(true);
    try {
      const result = await runCorrelation(ids);
      setCorrelations(result);
    } finally {
      setLoading(false);
    }
  };

  const getScoreColor = (score: number) => {
    if (score >= 80) return 'success';
    if (score >= 50) return 'warning';
    return 'default';
  };

  return (
    <Box p={3}>
      <Typography variant="h4" gutterBottom>Multi-Sonobuoy Analysis</Typography>

      <Box mb={2}>
        <DateTimeRangePicker
          fromDateTime={fromDt} toDateTime={toDt}
          onFromChange={setFromDt} onToChange={setToDt}
          onApply={() => loadData(fromDt, toDt)}
          onClear={() => { setFromDt(''); setToDt(''); loadData(); }}
          label="Filter by Date/Time:"
        />
      </Box>

      <Box mb={2}>
        <Typography variant="subtitle1" gutterBottom>Select sonobuoys to correlate:</Typography>
        <FormGroup row>
          {sonobuoys.map(sb => (
            <FormControlLabel key={sb.id}
              control={<Checkbox checked={selected.has(sb.id)} onChange={() => toggle(sb.id)} />}
              label={`${sb.id} (${sb.name})`} />
          ))}
        </FormGroup>
        <Button variant="contained" onClick={handleCorrelate} disabled={selected.size < 2 || loading} sx={{ mt: 1 }}>
          {loading ? <CircularProgress size={20} /> : 'Run Correlation'}
        </Button>
      </Box>

      {correlations.length > 0 && (
        <TableContainer component={Paper}>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Pair</TableCell>
                <TableCell>Correlation Score</TableCell>
                <TableCell>Common Frequencies</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {correlations.map((c: any, i: number) => (
                <TableRow key={i}>
                  <TableCell>{c.sonobuoyA} ↔ {c.sonobuoyB}</TableCell>
                  <TableCell>
                    <Chip label={`${c.correlationScore}%`}
                      color={getScoreColor(c.correlationScore) as any} size="small" />
                  </TableCell>
                  <TableCell>
                    {c.commonFrequencies?.map((f: number) => (
                      <Chip key={f} label={`${f} Hz`} size="small" sx={{ mr: 0.5 }} variant="outlined" />
                    ))}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}
    </Box>
  );
};

export default MultiSonobuoyAnalysis;
