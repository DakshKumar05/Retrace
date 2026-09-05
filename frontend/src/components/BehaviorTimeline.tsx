import { Box, Typography } from '@mui/material';
import { dateTime, timeOnly } from '../utils/format';

const TONE: Record<string, string> = { info: '#1e6fd9', warning: '#c77700', critical: '#c0342b' };

export interface TimelineItem {
  id: number | string;
  occurred_at: string;
  title: string;
  detail?: string | null;
  severity?: string;
  source?: string;
}

/** A single vertical spine. The dot colour is the only thing carrying severity,
 *  so the sequence stays readable at a glance. */
export function BehaviorTimeline({ items, showDate }: { items: TimelineItem[]; showDate?: boolean }) {
  return (
    <Box sx={{ position: 'relative', pl: 3.5 }}>
      <Box sx={{ position: 'absolute', left: 7, top: 8, bottom: 8, width: '2px', bgcolor: 'divider' }} />
      {items.map((item) => {
        const color = TONE[item.severity ?? 'info'] ?? '#1e6fd9';
        return (
          <Box key={item.id} sx={{ position: 'relative', pb: 2.75, '&:last-of-type': { pb: 0 } }}>
            <Box
              sx={{
                position: 'absolute', left: -24, top: 4, width: 16, height: 16, borderRadius: '50%',
                bgcolor: 'background.paper', border: `3px solid ${color}`,
              }}
            />
            <Typography variant="caption" className="tabular" sx={{ color: 'text.secondary', fontWeight: 600 }}>
              {showDate ? dateTime(item.occurred_at) : timeOnly(item.occurred_at)}
            </Typography>
            <Typography variant="body2" sx={{ fontWeight: 600, color: item.severity === 'critical' ? color : 'text.primary' }}>
              {item.title}
            </Typography>
            {item.detail ? (
              <Typography variant="body2" color="text.secondary" sx={{ mt: 0.15 }}>{item.detail}</Typography>
            ) : null}
          </Box>
        );
      })}
    </Box>
  );
}
