import { Alert, Box, Button, CircularProgress, Paper, Typography } from '@mui/material';
import type { ReactNode } from 'react';

export function LoadingState({ label = 'Loading' }: { label?: string }) {
  return (
    <Box sx={{ display: 'grid', placeItems: 'center', py: 8, gap: 2 }}>
      <CircularProgress size={26} thickness={5} />
      <Typography variant="body2" color="text.secondary">{label}…</Typography>
    </Box>
  );
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <Alert
      severity="error"
      variant="outlined"
      sx={{ my: 2 }}
      action={onRetry ? <Button color="inherit" size="small" onClick={onRetry}>Try again</Button> : undefined}
    >
      {message}
    </Alert>
  );
}

export function EmptyState({
  title, body, action, icon,
}: { title: string; body?: string; action?: ReactNode; icon?: ReactNode }) {
  return (
    <Paper variant="outlined" sx={{ p: 5, textAlign: 'center', borderStyle: 'dashed' }}>
      {icon ? <Box sx={{ color: 'text.secondary', mb: 1.5 }}>{icon}</Box> : null}
      <Typography variant="h5" sx={{ mb: 0.5 }}>{title}</Typography>
      {body ? (
        <Typography variant="body2" color="text.secondary" sx={{ maxWidth: 460, mx: 'auto' }}>
          {body}
        </Typography>
      ) : null}
      {action ? <Box sx={{ mt: 2.5 }}>{action}</Box> : null}
    </Paper>
  );
}
