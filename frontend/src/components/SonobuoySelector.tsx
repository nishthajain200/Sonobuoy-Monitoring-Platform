import React from 'react';
import { FormControl, InputLabel, Select, MenuItem } from '@mui/material';

interface Props {
  sonobuoys: any[];
  selected: string;
  onChange: (id: string) => void;
  label?: string;
}

const SonobuoySelector: React.FC<Props> = ({ sonobuoys, selected, onChange, label }) => (
  <FormControl size="small" sx={{ minWidth: 200 }}>
    <InputLabel>{label || 'Sonobuoy'}</InputLabel>
    <Select value={selected} label={label || 'Sonobuoy'}
            onChange={e => onChange(e.target.value as string)}>
      {sonobuoys.map(sb => (
        <MenuItem key={sb.id} value={sb.id}>{sb.id} – {sb.name}</MenuItem>
      ))}
    </Select>
  </FormControl>
);

export default SonobuoySelector;
