import { useNavigate } from 'react-router-dom';
import {
  Alert, Box, Button, Card, Chip, Divider, Table, TableBody, TableCell, TableHead, TableRow, Typography,
} from '@mui/material';
import { Shield, ShieldCheck } from 'lucide-react';
import { useAsync } from '../hooks/useAsync';
import { useAuth } from '../hooks/useAuth';
import { api } from '../services/api';
import { rupees, timeOnly } from '../utils/format';
import { ErrorState, LoadingState } from '../components/StateViews';
import { RiskBadge, StatusChip } from '../components/RiskBadge';
import { SectionCard, StatCard } from '../components/SectionCard';

export function Dashboard() {
  const navigate = useNavigate();
  const { user, refresh } = useAuth();
  const { data, loading, error, reload } = useAsync(() => api.dashboard(), []);

  if (loading) return <LoadingState label="Loading your dashboard" />;
  if (error) return <ErrorState message={error} onRetry={reload} />;
  if (!data) return null;

  const toggleSafeMode = async () => {
    await api.setSafeMode(!data.safe_mode_enabled);
    await refresh();
    reload();
  };

  return (
    <Box sx={{ display: 'grid', gap: 3 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 2, flexWrap: 'wrap' }}>
        <Box>
          <Typography variant="h2">{data.greeting}, {user?.full_name.split(' ')[0]}</Typography>
          <Typography color="text.secondary">Your account protection is active.</Typography>
        </Box>
        <Chip icon={<ShieldCheck size={15} />} label="Protection active"
          sx={{ color: '#0f9d74', bgcolor: '#0f9d7414', border: '1px solid #0f9d7440' }} />
      </Box>

      <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr 1fr', md: 'repeat(4, 1fr)' }, gap: 2 }}>
        <StatCard label="Money received" value={rupees(data.total_transaction_value)} hint="Across all credits" />
        <StatCard label="Protected funds" value={rupees(data.protected_funds)} hint="Held back in this demo" tone="#0f9d74" />
        <StatCard label="Risk alerts" value={String(data.risk_alerts)} hint="High or critical" tone={data.risk_alerts ? '#c77700' : undefined} />
        <StatCard label="Open incidents" value={String(data.open_incidents)} hint="Cases in progress" tone={data.open_incidents ? '#c0342b' : undefined} />
      </Box>

      {data.pending_refund_requests.length ? (
        <Alert
          severity={data.pending_refund_requests[0].risk_level === 'CRITICAL' ? 'error' : 'warning'}
          action={<Button size="small" color="inherit" onClick={() => navigate('/app/refund-safety')}>Review</Button>}
        >
          {data.pending_refund_requests.length} refund request{data.pending_refund_requests.length === 1 ? '' : 's'} waiting on you.
          The highest scored {data.pending_refund_requests[0].risk_score}/100 for risk.
        </Alert>
      ) : null}

      <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', lg: '1.6fr 1fr' }, gap: 3 }}>
        <SectionCard
          title="Recent transactions"
          action={<Button size="small" onClick={() => navigate('/app/transactions')}>See all</Button>}
        >
          <Box sx={{ overflowX: 'auto' }}>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Transaction</TableCell>
                  <TableCell align="right">Amount</TableCell>
                  <TableCell>Status</TableCell>
                  <TableCell align="right">Risk</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {data.recent_transactions.map((tx) => (
                  <TableRow key={tx.id} hover sx={{ cursor: 'pointer' }}
                    onClick={() => navigate(`/app/transactions/${tx.reference}`)}>
                    <TableCell>
                      <Typography className="mono" variant="body2" sx={{ fontWeight: 600 }}>{tx.reference}</Typography>
                      <Typography variant="caption" color="text.secondary" className="mono">{tx.sender_handle}</Typography>
                    </TableCell>
                    <TableCell align="right" className="tabular">
                      <Typography variant="body2" sx={{ fontWeight: 600, color: tx.direction === 'credit' ? '#0f9d74' : 'text.primary' }}>
                        {tx.direction === 'credit' ? '+' : '−'}{rupees(tx.amount)}
                      </Typography>
                    </TableCell>
                    <TableCell><StatusChip status={tx.label} /></TableCell>
                    <TableCell align="right"><RiskBadge score={tx.risk_score} /></TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </Box>
        </SectionCard>

        <Box sx={{ display: 'grid', gap: 3, alignContent: 'start' }}>
          <Card sx={{ p: 2.5, bgcolor: data.safe_mode_enabled ? '#0f9d7409' : undefined }}>
            <Box sx={{ display: 'flex', gap: 1.25, alignItems: 'center', mb: 0.5 }}>
              <Shield size={18} color={data.safe_mode_enabled ? '#0f9d74' : '#5a6a7d'} />
              <Typography variant="h5">Account protection</Typography>
            </Box>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              Safe Mode is {data.safe_mode_enabled ? 'on' : 'off'}.{' '}
              {data.safe_mode_enabled
                ? 'New beneficiaries and high-risk transfers need an extra confirmation.'
                : 'Turn it on to add checks before money can leave in a hurry.'}
            </Typography>
            <Button fullWidth variant={data.safe_mode_enabled ? 'outlined' : 'contained'} onClick={toggleSafeMode}>
              {data.safe_mode_enabled ? 'Turn off Safe Mode' : 'Turn on Safe Mode'}
            </Button>
          </Card>

          <SectionCard title="Recent alerts" dense>
            {data.recent_alerts.length === 0 ? (
              <Typography variant="body2" color="text.secondary">Nothing to look at. Your account looks clear.</Typography>
            ) : (
              <Box sx={{ display: 'grid', gap: 1.5 }}>
                {data.recent_alerts.map((alert, index) => (
                  <Box key={alert.id}>
                    {index ? <Divider sx={{ mb: 1.5 }} /> : null}
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', gap: 1 }}>
                      <Typography variant="body2" sx={{ fontWeight: 600 }}>{alert.title}</Typography>
                      <Typography variant="caption" color="text.secondary" className="tabular">{timeOnly(alert.created_at)}</Typography>
                    </Box>
                    {alert.body ? <Typography variant="body2" color="text.secondary">{alert.body}</Typography> : null}
                  </Box>
                ))}
              </Box>
            )}
          </SectionCard>
        </Box>
      </Box>
    </Box>
  );
}
