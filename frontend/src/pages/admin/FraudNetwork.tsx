import { useState } from 'react';
import { Box, Card, Chip, Typography } from '@mui/material';
import { Share2 } from 'lucide-react';
import { useAsync } from '../../hooks/useAsync';
import { api } from '../../services/api';
import { EmptyState, ErrorState, LoadingState } from '../../components/StateViews';
import { NetworkGraph } from '../../components/NetworkGraph';
import { SectionCard, StatCard } from '../../components/SectionCard';

export function FraudNetwork() {
  const { data, loading, error, reload } = useAsync(() => api.fraudNetwork(), []);
  const [index, setIndex] = useState(0);

  if (loading) return <LoadingState label="Computing the network" />;
  if (error) return <ErrorState message={error} onRetry={reload} />;
  if (!data) return null;

  const cluster = data.clusters[index];

  return (
    <Box sx={{ display: 'grid', gap: 2.5 }}>
      <Box>
        <Typography variant="h2">Fraud network</Typography>
        <Typography color="text.secondary">{data.note}</Typography>
      </Box>

      {data.clusters.length === 0 ? (
        <EmptyState icon={<Share2 size={30} />} title="No clusters found"
          body="A cluster appears once a sender is linked to more than one account, or has been flagged before." />
      ) : null}

      {cluster ? (
        <>
          <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
            {data.clusters.map((entry, position) => (
              <Chip
                key={entry.cluster_key}
                label={`${entry.suspect_handle} · ${entry.victim_count} accounts`}
                onClick={() => setIndex(position)}
                variant={position === index ? 'filled' : 'outlined'}
                color={position === index ? 'primary' : 'default'}
                className="mono"
              />
            ))}
          </Box>

          <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr 1fr', md: 'repeat(4, 1fr)' }, gap: 2 }}>
            <StatCard label="Paying account" value={cluster.suspect_handle} tone="#c0342b" />
            <StatCard label="Accounts paid" value={String(cluster.victim_count)} />
            <StatCard label="Refund destinations" value={String(cluster.destination_count)} tone="#c77700" />
            <StatCard label="Related payments" value={String(cluster.transaction_count)} />
          </Box>

          <SectionCard
            title="Coordinated activity"
            subtitle={`Cluster risk ${cluster.risk_score}/100. Dashed lines mark a refund destination that differs from the paying account.`}
          >
            <NetworkGraph cluster={cluster} />
          </SectionCard>

          <Card sx={{ p: 2.5 }}>
            <Typography variant="body2" color="text.secondary">
              A shared paying account across several unrelated people, each asked to refund to a
              different handle, is the shape this scam takes at scale. It is a lead worth reviewing,
              not proof that any account is fraudulent.
            </Typography>
          </Card>
        </>
      ) : null}
    </Box>
  );
}
