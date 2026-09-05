import { Box, Card, Chip, Divider, Typography, useTheme } from '@mui/material';
import {
  Area, AreaChart, Bar, BarChart, CartesianGrid, Cell, Legend, Line, LineChart,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts';
import { useAsync } from '../../hooks/useAsync';
import { api } from '../../services/api';
import { elapsed, rupees } from '../../utils/format';
import { riskColor } from '../../theme';
import { ErrorState, LoadingState } from '../../components/StateViews';
import { SectionCard, StatCard } from '../../components/SectionCard';

export function RiskIntelligence() {
  const theme = useTheme();
  const axis = { fontSize: 11, fill: theme.palette.text.secondary };
  const gridColor = theme.palette.divider;
  const stats = useAsync(() => api.adminStatistics(), []);
  const feed = useAsync(() => api.riskFeed(), []);

  if (stats.loading) return <LoadingState label="Loading fraud intelligence" />;
  if (stats.error) return <ErrorState message={stats.error} onRetry={stats.reload} />;
  if (!stats.data) return null;

  const data = stats.data;
  const shortDate = (value: string) => value.slice(5).replace('-', '/');

  return (
    <Box sx={{ display: 'grid', gap: 2.5 }}>
      <Box>
        <Typography variant="h2">Fraud intelligence</Typography>
        <Typography color="text.secondary">
          Platform view across all accounts. Figures combine seeded demo activity with a demonstration baseline.
        </Typography>
      </Box>

      <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr 1fr', md: 'repeat(5, 1fr)' }, gap: 2 }}>
        <StatCard label="Transactions" value={data.total_transactions.toLocaleString('en-IN')} />
        <StatCard label="Suspicious" value={data.suspicious.toLocaleString('en-IN')} tone="#c77700" />
        <StatCard label="High risk" value={data.high_risk.toLocaleString('en-IN')} tone="#c0342b" />
        <StatCard label="Open incidents" value={data.open_incidents.toLocaleString('en-IN')} />
        <StatCard label="Protected users" value={data.protected_users.toLocaleString('en-IN')} tone="#0f9d74" />
      </Box>

      <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', lg: '1.4fr 1fr' }, gap: 3 }}>
        <SectionCard title="Transactions over time" subtitle="Last 14 days">
          <ResponsiveContainer width="100%" height={240}>
            <AreaChart data={data.transactions_over_time}>
              <CartesianGrid strokeDasharray="3 3" stroke={gridColor} />
              <XAxis dataKey="date" tickFormatter={shortDate} tick={axis} />
              <YAxis tick={axis} />
              <Tooltip />
              <Area type="monotone" dataKey="transactions" stroke="#1e6fd9" fill="#1e6fd918" strokeWidth={2} />
            </AreaChart>
          </ResponsiveContainer>
        </SectionCard>

        <SectionCard title="Risk distribution">
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={data.risk_distribution}>
              <CartesianGrid strokeDasharray="3 3" stroke={gridColor} />
              <XAxis dataKey="level" tick={axis} />
              <YAxis tick={axis} />
              <Tooltip />
              <Bar dataKey="count" radius={[6, 6, 0, 0]}>
                {data.risk_distribution.map((entry) => (
                  <Cell key={entry.level} fill={riskColor(entry.level)} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </SectionCard>
      </Box>

      <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', lg: '1fr 1fr' }, gap: 3 }}>
        <SectionCard title="Refund scams flagged per day">
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={data.refund_scam_frequency}>
              <CartesianGrid strokeDasharray="3 3" stroke={gridColor} />
              <XAxis dataKey="date" tickFormatter={shortDate} tick={axis} />
              <YAxis tick={axis} />
              <Tooltip />
              <Line type="monotone" dataKey="refund_scams" stroke="#c0342b" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </SectionCard>

        <SectionCard title="Signals firing most often"
          subtitle={`Average gap from payment to refund request: ${elapsed(data.average_payment_to_refund_seconds)}`}>
          {data.top_signals.length === 0 ? (
            <Typography variant="body2" color="text.secondary">No signals recorded yet.</Typography>
          ) : (
            <Box sx={{ display: 'grid', gap: 1.25 }}>
              {data.top_signals.map((signal) => (
                <Box key={signal.label} sx={{ display: 'flex', gap: 1.5, alignItems: 'center' }}>
                  <Typography className="tabular" sx={{ minWidth: 28, fontWeight: 700 }}>{signal.count}</Typography>
                  <Typography variant="body2" sx={{ flex: 1 }}>{signal.label}</Typography>
                  <Chip size="small" label={signal.category} sx={{ height: 19, fontSize: '0.66rem' }} />
                </Box>
              ))}
            </Box>
          )}
        </SectionCard>
      </Box>

      <SectionCard title="Live risk feed" subtitle="Most recent scored transactions across the platform">
        {feed.loading ? <LoadingState label="Loading feed" /> : null}
        {feed.data?.length ? (
          <Box sx={{ display: 'grid', gap: 0 }}>
            {feed.data.slice(0, 12).map((item, index) => (
              <Box key={`${item.reference}-${index}`}>
                {index ? <Divider /> : null}
                <Box sx={{ display: 'flex', gap: 2, alignItems: 'center', py: 1 }}>
                  <Typography className="mono tabular" variant="caption" color="text.secondary" sx={{ minWidth: 62 }}>
                    {new Date(item.timestamp).toLocaleTimeString('en-IN', { hour12: false })}
                  </Typography>
                  <Typography className="mono" variant="body2" sx={{ minWidth: 78, fontWeight: 600 }}>{item.reference}</Typography>
                  <Typography className="tabular" variant="body2" sx={{ minWidth: 82 }}>{rupees(item.amount)}</Typography>
                  <Typography className="mono" variant="caption" color="text.secondary" sx={{ flex: 1, minWidth: 0 }}>
                    {item.sender_handle}
                  </Typography>
                  <Typography variant="caption" sx={{ fontWeight: 700, color: riskColor(item.risk_level) }}>
                    {item.risk_level}
                  </Typography>
                </Box>
              </Box>
            ))}
          </Box>
        ) : null}
      </SectionCard>
    </Box>
  );
}
