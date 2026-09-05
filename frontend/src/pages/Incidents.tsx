import { useNavigate } from 'react-router-dom';
import { Box, Card, Typography } from '@mui/material';
import { ShieldCheck } from 'lucide-react';
import { useAsync } from '../hooks/useAsync';
import { api } from '../services/api';
import { dateTime, rupees } from '../utils/format';
import { EmptyState, ErrorState, LoadingState } from '../components/StateViews';
import { RiskBadge, StatusChip } from '../components/RiskBadge';

export function Incidents() {
  const navigate = useNavigate();
  const { data, loading, error, reload } = useAsync(() => api.incidents(), []);

  return (
    <Box sx={{ display: 'grid', gap: 2.5 }}>
      <Box>
        <Typography variant="h2">Incidents</Typography>
        <Typography color="text.secondary">Cases opened when a refund sequence looked like a scam.</Typography>
      </Box>

      {loading ? <LoadingState label="Loading cases" /> : null}
      {error ? <ErrorState message={error} onRetry={reload} /> : null}

      {data && data.length === 0 ? (
        <EmptyState icon={<ShieldCheck size={30} />} title="No incidents on this account"
          body="Nothing has gone wrong here. If a refund pattern is flagged, a case opens automatically." />
      ) : null}

      <Box sx={{ display: 'grid', gap: 2 }}>
        {data?.map((incident) => (
          <Card key={incident.id} sx={{ p: 2.5, cursor: 'pointer' }} onClick={() => navigate(`/app/incidents/${incident.id}`)}>
            <Box sx={{ display: 'flex', gap: 2, justifyContent: 'space-between', flexWrap: 'wrap', alignItems: 'flex-start' }}>
              <Box sx={{ minWidth: 0, flex: 1 }}>
                <Box sx={{ display: 'flex', gap: 1, alignItems: 'center', mb: 0.5, flexWrap: 'wrap' }}>
                  <Typography variant="h4" className="mono">{incident.case_id}</Typography>
                  <StatusChip status={incident.status} />
                  <RiskBadge level={incident.risk_level} score={incident.risk_score} />
                </Box>
                <Typography variant="body2" color="text.secondary" sx={{ maxWidth: '80ch' }}>{incident.summary}</Typography>
              </Box>
              <Box sx={{ textAlign: 'right' }}>
                <Typography variant="caption" color="text.secondary">Potential loss</Typography>
                <Typography className="tabular" sx={{ fontWeight: 750, fontSize: '1.25rem', color: '#c0342b' }}>
                  {rupees(incident.potential_loss)}
                </Typography>
                <Typography variant="caption" color="text.secondary">{dateTime(incident.created_at)}</Typography>
              </Box>
            </Box>
          </Card>
        ))}
      </Box>
    </Box>
  );
}
