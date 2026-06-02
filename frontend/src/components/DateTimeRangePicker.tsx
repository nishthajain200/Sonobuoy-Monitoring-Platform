import React from 'react';
import { Box, TextField, Button, Typography } from '@mui/material';
import { FilterAlt, Clear } from '@mui/icons-material';

interface DateTimeRangePickerProps {
  fromDateTime: string;
  toDateTime: string;
  onFromChange: (value: string) => void;
  onToChange: (value: string) => void;
  onApply: () => void;
  onClear?: () => void;
  label?: string;
}

const DateTimeRangePicker: React.FC<DateTimeRangePickerProps> = ({
  fromDateTime,
  toDateTime,
  onFromChange,
  onToChange,
  onApply,
  onClear,
  label,
}) => {
  return (
    <Box
      sx={{
        display: 'flex',
        gap: 1.5,
        alignItems: 'center',
        flexWrap: 'wrap',
        p: 1.5,
        bgcolor: '#f8f9fa',
        borderRadius: 1,
        border: '1px solid #e0e0e0',
      }}
    >
      {label && (
        <Typography variant="subtitle2" sx={{ mr: 0.5, color: '#555' }}>
          {label}
        </Typography>
      )}
      <TextField
        size="small"
        label="From Date/Time"
        type="datetime-local"
        value={fromDateTime}
        onChange={(e) => onFromChange(e.target.value)}
        InputLabelProps={{ shrink: true }}
        sx={{ minWidth: 200 }}
      />
      <TextField
        size="small"
        label="To Date/Time"
        type="datetime-local"
        value={toDateTime}
        onChange={(e) => onToChange(e.target.value)}
        InputLabelProps={{ shrink: true }}
        sx={{ minWidth: 200 }}
      />
      <Button
        variant="contained"
        size="small"
        startIcon={<FilterAlt />}
        onClick={onApply}
        disabled={!fromDateTime || !toDateTime}
      >
        Apply
      </Button>
      {onClear && (
        <Button
          variant="outlined"
          size="small"
          startIcon={<Clear />}
          onClick={onClear}
        >
          Clear
        </Button>
      )}
    </Box>
  );
};

export default DateTimeRangePicker;
