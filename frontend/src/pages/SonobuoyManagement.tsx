import React, { useEffect, useState } from 'react';
import {
  Box, Typography, Table, TableBody, TableCell, TableContainer, TableHead,
  TableRow, Paper, Button, Dialog, DialogTitle, DialogContent, DialogActions,
  TextField, IconButton, Chip
} from '@mui/material';
import { Delete, Edit } from '@mui/icons-material';
import { getSonobuoys, createSonobuoy, updateSonobuoy, deleteSonobuoy } from '../services/api';

const emptyForm = {
  id: '', name: '', latitude: '', longitude: '',
  deploymentTime: '2026-05-01T08:35:12Z', numberOfChannels: 4,
  sampleRate: 48000, recordingDuration: 600, status: 'Active',
};

const SonobuoyManagement: React.FC = () => {
  const [sonobuoys, setSonobuoys] = useState<any[]>([]);
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState<any>({ ...emptyForm });
  const [editing, setEditing] = useState(false);

  const load = () => getSonobuoys().then(setSonobuoys).catch(() => {});
  useEffect(() => { load(); }, []);

  const handleSave = async () => {
    const payload = {
      ...form,
      latitude: parseFloat(form.latitude),
      longitude: parseFloat(form.longitude),
      numberOfChannels: parseInt(form.numberOfChannels),
      sampleRate: parseInt(form.sampleRate),
      recordingDuration: parseFloat(form.recordingDuration),
    };
    if (editing) {
      await updateSonobuoy(form.id, { name: payload.name, latitude: payload.latitude, longitude: payload.longitude, status: payload.status });
    } else {
      await createSonobuoy(payload);
    }
    setOpen(false);
    load();
  };

  const handleEdit = (sb: any) => {
    setForm({ ...sb, latitude: sb.latitude.toString(), longitude: sb.longitude.toString() });
    setEditing(true);
    setOpen(true);
  };

  const handleDelete = async (id: string) => {
    if (window.confirm(`Delete sonobuoy ${id}?`)) {
      await deleteSonobuoy(id);
      load();
    }
  };

  const handleNew = () => {
    setForm({ ...emptyForm });
    setEditing(false);
    setOpen(true);
  };

  return (
    <Box p={3}>
      <Box display="flex" justifyContent="space-between" mb={2}>
        <Typography variant="h4">Sonobuoy Management</Typography>
        <Button variant="contained" onClick={handleNew}>Add Sonobuoy</Button>
      </Box>

      <TableContainer component={Paper}>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>ID</TableCell><TableCell>Name</TableCell>
              <TableCell>Lat</TableCell><TableCell>Lon</TableCell>
              <TableCell>Channels</TableCell><TableCell>Sample Rate</TableCell>
              <TableCell>Duration (s)</TableCell><TableCell>Status</TableCell>
              <TableCell>Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {sonobuoys.map(sb => (
              <TableRow key={sb.id}>
                <TableCell>{sb.id}</TableCell>
                <TableCell>{sb.name}</TableCell>
                <TableCell>{sb.latitude}</TableCell>
                <TableCell>{sb.longitude}</TableCell>
                <TableCell>{sb.numberOfChannels}</TableCell>
                <TableCell>{sb.sampleRate}</TableCell>
                <TableCell>{sb.recordingDuration}</TableCell>
                <TableCell><Chip label={sb.status} color={sb.status === 'Active' ? 'success' : 'default'} size="small" /></TableCell>
                <TableCell>
                  <IconButton size="small" onClick={() => handleEdit(sb)}><Edit fontSize="small" /></IconButton>
                  <IconButton size="small" onClick={() => handleDelete(sb.id)}><Delete fontSize="small" /></IconButton>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>

      <Dialog open={open} onClose={() => setOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>{editing ? 'Edit Sonobuoy' : 'New Sonobuoy'}</DialogTitle>
        <DialogContent>
          <Box display="flex" flexDirection="column" gap={2} mt={1}>
            <TextField label="ID" value={form.id} onChange={e => setForm({ ...form, id: e.target.value })} disabled={editing} size="small" />
            <TextField label="Name" value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} size="small" />
            <TextField label="Latitude" value={form.latitude} onChange={e => setForm({ ...form, latitude: e.target.value })} size="small" type="number" />
            <TextField label="Longitude" value={form.longitude} onChange={e => setForm({ ...form, longitude: e.target.value })} size="small" type="number" />
            <TextField label="Deployment Time" value={form.deploymentTime} onChange={e => setForm({ ...form, deploymentTime: e.target.value })} size="small" />
            <TextField label="Channels" value={form.numberOfChannels} onChange={e => setForm({ ...form, numberOfChannels: e.target.value })} size="small" type="number" />
            <TextField label="Sample Rate" value={form.sampleRate} onChange={e => setForm({ ...form, sampleRate: e.target.value })} size="small" type="number" />
            <TextField label="Duration (s)" value={form.recordingDuration} onChange={e => setForm({ ...form, recordingDuration: e.target.value })} size="small" type="number" />
            <TextField label="Status" value={form.status} onChange={e => setForm({ ...form, status: e.target.value })} size="small" />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpen(false)}>Cancel</Button>
          <Button variant="contained" onClick={handleSave}>Save</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default SonobuoyManagement;
