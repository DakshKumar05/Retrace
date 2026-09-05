import { useState } from 'react';
import {
  Alert, Box, Button, Card, Divider, FormControlLabel, Switch, TextField, Typography,
} from '@mui/material';
import { Check, Shield, ShieldCheck } from 'lucide-react';
import { useAsync } from '../hooks/useAsync';
import { useAuth } from '../hooks/useAuth';
import { api, errorMessage } from '../services/api';
import { rupees } from '../utils/format';
import { ErrorState, LoadingState } from '../components/StateViews';
import { SectionCard } from '../components/SectionCard';

const PROTECTIONS = [
  'New beneficiaries need an extra confirmation before money can go out',
  'High-risk transfers are held until you confirm them',
  'Suspicious refund requests are flagged instead of processed',
  'Evidence from a flagged sequence is preserved automatically',
];

export function SafeMode() {
  const { user, refresh } = useAuth();
  const { data, loading, error, reload } = useAsync(() => api.protection(), []);
  const [amount, setAmount] = useState('42000');
  const [busy, setBusy] = useState(false);
  const [failure, setFailure] = useState<string | null>(null);

  const act = async (action: () => Promise<unknown>) => {
    setBusy(true); setFailure(null);
    try { await action(); await refresh(); reload(); }
    catch (err) { setFailure(errorMessage(err)); }
    finally { setBusy(false); }
  };

  if (loading) return <LoadingState label="Loading protection settings" />;
  if (error) return <ErrorState message={error} onRetry={reload} />;

  const on = user?.safe_mode_enabled ?? false;

  return (
    <Box sx={{ display: 'grid', gap: 2.5 }}>
      <Box>
        <Typography variant="h2">Safe Mode</Typography>
        <Typography color="text.secondary">
          A protective state for your account after something risky happens.
        </Typography>
      </Box>

      <Alert severity="info">
        Safe Mode is a state inside Retrace. It does not reach into your bank and cannot block a
        real transaction.
      </Alert>

      {failure ? <ErrorState message={failure} /> : null}

      <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: '1fr 1fr' }, gap: 3 }}>
        <Card sx={{ p: 3, bgcolor: on ? '#0f9d7409' : undefined, borderColor: on ? '#0f9d7440' : undefined }}>
          <Box sx={{ display: 'flex', gap: 1.5, alignItems: 'center', mb: 1 }}>
            {on ? <ShieldCheck size={26} color="#0f9d74" /> : <Shield size={26} color="#5a6a7d" />}
            <Box>
              <Typography variant="h3">{on ? 'Safe Mode is on' : 'Safe Mode is off'}</Typography>
              {on && user?.safe_mode_activated_at ? (
                <Typography variant="caption" color="text.secondary">
                  Since {new Date(user.safe_mode_activated_at).toLocaleString('en-IN')}
                </Typography>
              ) : null}
            </Box>
          </Box>

          <Box sx={{ display: 'grid', gap: 0.9, my: 2.5 }}>
            {PROTECTIONS.map((line) => (
              <Box key={line} sx={{ display: 'flex', gap: 1, alignItems: 'flex-start' }}>
                <Box sx={{ pt: '2px' }}><Check size={15} color={on ? '#0f9d74' : '#9aa9ba'} /></Box>
                <Typography variant="body2" color={on ? 'text.primary' : 'text.secondary'}>{line}</Typography>
              </Box>
            ))}
          </Box>

          <Button fullWidth variant={on ? 'outlined' : 'contained'} disabled={busy}
            onClick={() => act(() => api.setSafeMode(!on))}>
            {on ? 'Turn off Safe Mode' : 'Turn on Safe Mode'}
          </Button>
        </Card>

        <SectionCard title="Emergency fund protection" subtitle="Opt in to hold a balance back from outgoing transfers.">
          <Box sx={{ display: 'grid', gap: 2 }}>
            <FormControlLabel
              control={<Switch checked={data?.enabled ?? false} disabled={busy}
                onChange={(event) => act(() => api.updateProtection({ enabled: event.target.checked }))} />}
              label={<Typography variant="body2">Emergency protection account •••• {data?.account_last4}</Typography>}
            />

            <Divider />

            {data?.protection_active ? (
              <Box>
                <Typography variant="caption" color="text.secondary">Protected balance</Typography>
                <Typography className="tabular" sx={{ fontSize: '2rem', fontWeight: 750, color: '#0f9d74', lineHeight: 1.1 }}>
                  {rupees(user?.protected_balance ?? 0)}
                </Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                  Held back from outgoing transfers in this demo. Nothing has moved in a real bank account.
                </Typography>
                <Button variant="outlined" disabled={busy} onClick={() => act(() => api.releaseProtection())}>
                  Release protected funds
                </Button>
              </Box>
            ) : (
              <Box>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                  Available to protect: <strong className="tabular">{rupees(user?.balance ?? 0)}</strong>
                </Typography>
                <TextField
                  size="small" label="Amount to isolate" fullWidth value={amount}
                  onChange={(event) => setAmount(event.target.value.replace(/[^0-9]/g, ''))}
                  sx={{ mb: 2 }}
                />
                <Button variant="contained" fullWidth disabled={busy || !data?.enabled || !amount}
                  onClick={() => act(() => api.activateProtection(Number(amount)))}>
                  Activate protection
                </Button>
                {!data?.enabled ? (
                  <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 1 }}>
                    Turn the setting on first.
                  </Typography>
                ) : null}
              </Box>
            )}
          </Box>
        </SectionCard>
      </Box>
    </Box>
  );
}
