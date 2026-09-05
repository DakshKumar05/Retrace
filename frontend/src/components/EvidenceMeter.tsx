import { Box, LinearProgress, Typography } from '@mui/material';
import { Check, X } from 'lucide-react';
import type { Completeness } from '../types';

export function EvidenceMeter({ data, compact }: { data: Completeness; compact?: boolean }) {
  const tone = data.percent >= 85 ? '#0f9d74' : data.percent >= 50 ? '#c77700' : '#c0342b';

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', mb: 0.75 }}>
        <Typography variant="body2" sx={{ fontWeight: 600 }}>Evidence completeness</Typography>
        <Typography className="tabular" sx={{ fontWeight: 750, color: tone }}>{data.percent}%</Typography>
      </Box>
      <LinearProgress
        variant="determinate"
        value={data.percent}
        sx={{ height: 9, bgcolor: 'divider', '& .MuiLinearProgress-bar': { bgcolor: tone } }}
      />
      <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 0.75 }}>
        {data.total_files} file{data.total_files === 1 ? '' : 's'} preserved
      </Typography>

      {compact ? null : (
        <Box sx={{ mt: 1.75, display: 'grid', gap: 0.6 }}>
          {data.present.map((label) => (
            <Box key={label} sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
              <Check size={14} color="#0f9d74" />
              <Typography variant="body2">{label}</Typography>
            </Box>
          ))}
          {data.missing.map((label) => (
            <Box key={label} sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
              <X size={14} color="#c0342b" />
              <Typography variant="body2" color="text.secondary">{label} — still missing</Typography>
            </Box>
          ))}
        </Box>
      )}
    </Box>
  );
}
