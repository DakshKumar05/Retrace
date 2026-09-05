import { Box, Card, CardContent, Typography } from '@mui/material';
import type { ReactNode } from 'react';

export function SectionCard({
  title, subtitle, action, children, dense,
}: {
  title?: string;
  subtitle?: string;
  action?: ReactNode;
  children: ReactNode;
  dense?: boolean;
}) {
  return (
    <Card sx={{ height: '100%' }}>
      {title ? (
        <Box
          sx={{
            px: dense ? 2 : 2.5, pt: dense ? 1.75 : 2.25, pb: 1.25,
            display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 2,
          }}
        >
          <Box>
            <Typography variant="h5">{title}</Typography>
            {subtitle ? (
              <Typography variant="body2" color="text.secondary" sx={{ mt: 0.25 }}>{subtitle}</Typography>
            ) : null}
          </Box>
          {action}
        </Box>
      ) : null}
      <CardContent sx={{ px: dense ? 2 : 2.5, pt: title ? 0.5 : 2.5, '&:last-child': { pb: 2.5 } }}>
        {children}
      </CardContent>
    </Card>
  );
}

export function StatCard({
  label, value, hint, tone,
}: { label: string; value: string; hint?: string; tone?: string }) {
  return (
    <Card sx={{ p: 2.25, height: '100%' }}>
      <Typography variant="body2" color="text.secondary" sx={{ fontWeight: 550 }}>{label}</Typography>
      <Typography
        className="tabular"
        sx={{ fontSize: '1.75rem', fontWeight: 700, letterSpacing: '-0.02em', mt: 0.5, color: tone }}
      >
        {value}
      </Typography>
      {hint ? (
        <Typography variant="caption" color="text.secondary">{hint}</Typography>
      ) : null}
    </Card>
  );
}
