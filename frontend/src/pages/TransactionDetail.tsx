import { useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { Box, Button, Divider, Typography } from '@mui/material';
import { ArrowLeft } from 'lucide-react';
import { useAsync } from '../hooks/useAsync';
import { api } from '../services/api';
import { dateTime, elapsed, rupees } from '../utils/format';
import { ErrorState, LoadingState } from '../components/StateViews';
import { RiskBadge, StatusChip } from '../components/RiskBadge';
import { SectionCard } from '../components/SectionCard';
import { BehaviorTimeline } from '../components/BehaviorTimeline';
import { RiskExplanation } from '../components/RiskExplanation';
import { RiskGauge } from '../components/RiskGauge';
import { RefundSafetyDialog } from '../components/RefundSafetyDialog';

function Field({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <Box>
      <Typography variant="caption" color="text.secondary">{label}</Typography>
      <Typography className={mono ? 'mono' : 'tabular'} sx={{ fontWeight: 600, wordBreak: 'break-all' }}>{value}</Typography>
    </Box>
  );
}

export function TransactionDetail() {
  const { reference } = useParams();
  const navigate = useNavigate();
  const [dialogOpen, setDialogOpen] = useState(false);
  const { data, loading, error, reload } = useAsync(() => api.transaction(reference!), [reference]);

  if (loading) return <LoadingState label="Loading transaction" />;
  if (error) return <ErrorState message={error} onRetry={reload} />;
  if (!data) return null;

  const refund = data.refund_requests[0];
  const assessment = data.latest_assessment;

  return (
    <Box sx={{ display: 'grid', gap: 2.5 }}>
      <Button startIcon={<ArrowLeft size={16} />} onClick={() => navigate('/app/transactions')} sx={{ justifySelf: 'start', px: 0 }}>
        All transactions
      </Button>

      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 2, flexWrap: 'wrap' }}>
        <Box>
          <Typography variant="h2" className="mono">{data.reference}</Typography>
          <Typography color="text.secondary">{dateTime(data.created_at)}</Typography>
        </Box>
        <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
          <StatusChip status={data.label} />
          <RiskBadge score={data.risk_score} size="medium" />
        </Box>
      </Box>

      <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', lg: '1.4fr 1fr' }, gap: 3 }}>
        <Box sx={{ display: 'grid', gap: 3, alignContent: 'start' }}>
          <SectionCard title="Transaction details">
            <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr 1fr', sm: 'repeat(3, 1fr)' }, gap: 2.25 }}>
              <Field label="Amount" value={rupees(data.amount)} />
              <Field label="Direction" value={data.direction === 'credit' ? 'Received' : 'Sent'} />
              <Field label="Method" value={data.payment_method} />
              <Field label="Sender" value={data.sender_handle} mono />
              <Field label="Receiver" value={data.receiver_handle} mono />
              <Field label="Status" value={data.status} />
              <Field label="Known sender" value={data.sender_known ? 'Yes' : 'No prior history'} />
              <Field label="Sender account age" value={`about ${data.sender_account_age_days} days`} />
              <Field label="Refund requested" value={data.refund_requested ? 'Yes' : 'No'} />
            </Box>
            {data.note ? (
              <>
                <Divider sx={{ my: 2 }} />
                <Typography variant="body2" color="text.secondary">{data.note}</Typography>
              </>
            ) : null}
          </SectionCard>

          {data.events.length ? (
            <SectionCard title="Transaction behaviour" subtitle="What happened, in the order it happened.">
              <BehaviorTimeline items={data.events} />
            </SectionCard>
          ) : null}
        </Box>

        <Box sx={{ display: 'grid', gap: 3, alignContent: 'start' }}>
          {refund ? (
            <SectionCard title="Refund request">
              <Box sx={{ display: 'grid', gap: 2 }}>
                <RiskGauge safetyScore={refund.safety_score} riskScore={refund.risk_score}
                  level={refund.risk_level} recommendation={refund.recommendation} size={200} />
                <Box sx={{ mt: 3, display: 'grid', gap: 1.75 }}>
                  <Field label="Asked for" value={rupees(refund.amount)} />
                  <Field label="Requested" value={`${elapsed(refund.seconds_since_payment)} after the credit`} />
                  <Field label="Destination" value={refund.refund_destination} mono />
                  <Field label="Outcome" value={refund.status.replace(/_/g, ' ').toLowerCase()} />
                </Box>
                {['PENDING', 'BLOCKED'].includes(refund.status) ? (
                  <Button variant="contained" onClick={() => setDialogOpen(true)}>Review this refund</Button>
                ) : null}
              </Box>
            </SectionCard>
          ) : null}

          {assessment ? (
            <SectionCard title="Risk breakdown">
              <RiskExplanation signals={assessment.signals} limit={8} />
            </SectionCard>
          ) : null}
        </Box>
      </Box>

      {refund ? (
        <RefundSafetyDialog open={dialogOpen} onClose={() => setDialogOpen(false)} refund={refund}
          analysis={null} onChanged={reload} />
      ) : null}
    </Box>
  );
}
