import { useState } from 'react';
import {
  Alert, Box, Button, Card, Chip, Divider, Table, TableBody, TableCell, TableHead,
  TableRow, Typography,
} from '@mui/material';
import { ShieldCheck } from 'lucide-react';
import { useAsync } from '../hooks/useAsync';
import { api, errorMessage } from '../services/api';
import { dateTime, elapsed, rupees } from '../utils/format';
import { EmptyState, ErrorState, LoadingState } from '../components/StateViews';
import { RiskBadge, StatusChip } from '../components/RiskBadge';
import { RefundSafetyDialog } from '../components/RefundSafetyDialog';
import { MessageQuickCheck } from '../components/MessageQuickCheck';
import type { RefundAnalysis, RefundRequest } from '../types';

export function RefundSafety() {
  const { data, loading, error, reload } = useAsync(() => api.refunds(), []);
  const [active, setActive] = useState<RefundRequest | null>(null);
  const [analysis, setAnalysis] = useState<RefundAnalysis | null>(null);
  const [busy, setBusy] = useState(false);
  const [failure, setFailure] = useState<string | null>(null);

  const review = async (refund: RefundRequest) => {
    setBusy(true); setFailure(null); setAnalysis(null);
    try {
      // The reference has to be the real one. The engine looks the transaction
      // up by it, and without a match it scores against defaults instead of the
      // sender's actual history — a different number from the one on the card.
      const result = await api.analyzeRefund({
        transaction_id: refund.transaction_reference ?? refund.reference,
        refund_amount: refund.amount,
        original_sender: refund.original_sender,
        refund_destination: refund.refund_destination,
        time_since_payment: refund.seconds_since_payment,
        message: refund.message,
        persist: false,
      });
      setAnalysis(result);
      setActive(refund);
    } catch (err) { setFailure(errorMessage(err)); } finally { setBusy(false); }
  };

  const pending = data?.filter((r) => ['PENDING', 'BLOCKED'].includes(r.status)) ?? [];
  const settled = data?.filter((r) => !['PENDING', 'BLOCKED'].includes(r.status)) ?? [];

  return (
    <Box sx={{ display: 'grid', gap: 2.5 }}>
      <Box>
        <Typography variant="h2">Refund safety</Typography>
        <Typography color="text.secondary">
          Before a refund goes out, Retrace answers one question: is it safe for you to send this back?
        </Typography>
      </Box>

      <MessageQuickCheck />

      {failure ? <ErrorState message={failure} /> : null}
      {loading ? <LoadingState label="Loading refund requests" /> : null}
      {error ? <ErrorState message={error} onRetry={reload} /> : null}

      {data && pending.length === 0 && settled.length === 0 ? (
        <EmptyState
          icon={<ShieldCheck size={30} />}
          title="No refund requests"
          body="Nothing is waiting on you. If someone asks you to return a payment, it will show up here first."
        />
      ) : null}

      {pending.length ? (
        <Box sx={{ display: 'grid', gap: 2 }}>
          {pending.map((refund) => (
            <Card key={refund.id} sx={{ p: 2.5, borderColor: refund.risk_level === 'CRITICAL' ? '#c0342b40' : undefined }}>
              <Box sx={{ display: 'flex', gap: 2, justifyContent: 'space-between', flexWrap: 'wrap', alignItems: 'flex-start' }}>
                <Box sx={{ minWidth: 0 }}>
                  <Box sx={{ display: 'flex', gap: 1, alignItems: 'center', mb: 0.75, flexWrap: 'wrap' }}>
                    <Typography variant="h4" className="tabular">{rupees(refund.amount)}</Typography>
                    <RiskBadge level={refund.risk_level} score={refund.risk_score} />
                    <StatusChip status={refund.status} />
                  </Box>
                  <Typography variant="body2" color="text.secondary">
                    Asked for {elapsed(refund.seconds_since_payment)} after the money arrived, over {refund.channel.toLowerCase()}.
                  </Typography>
                  <Box sx={{ display: 'flex', gap: 2.5, mt: 1.25, flexWrap: 'wrap' }}>
                    <Box>
                      <Typography variant="caption" color="text.secondary">Paid in from</Typography>
                      <Typography className="mono" variant="body2">{refund.original_sender}</Typography>
                    </Box>
                    <Box>
                      <Typography variant="caption" color="text.secondary">Refund asked to</Typography>
                      <Typography className="mono" variant="body2"
                        sx={{ color: refund.destination_matches_sender ? 'text.primary' : '#c0342b', fontWeight: 600 }}>
                        {refund.refund_destination}
                      </Typography>
                    </Box>
                  </Box>
                </Box>
                <Button variant="contained" disabled={busy} onClick={() => review(refund)}>
                  {busy ? 'Scoring…' : 'Run safety check'}
                </Button>
              </Box>

              {!refund.destination_matches_sender ? (
                <Alert severity="error" sx={{ mt: 2 }}>
                  The destination does not match the account that paid you. A genuine mistaken payment
                  can always be returned to its source.
                </Alert>
              ) : null}

              {refund.message ? (
                <Box sx={{ mt: 2, p: 1.75, bgcolor: 'action.hover', borderRadius: 1.5, borderLeft: '3px solid', borderColor: 'divider' }}>
                  <Typography variant="body2" sx={{ fontStyle: 'italic', color: 'text.secondary' }}>"{refund.message}"</Typography>
                </Box>
              ) : null}
            </Card>
          ))}
        </Box>
      ) : null}

      {settled.length ? (
        <Card>
          <Box sx={{ px: 2.5, pt: 2.25, pb: 1 }}><Typography variant="h5">Settled requests</Typography></Box>
          <Box sx={{ overflowX: 'auto' }}>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Reference</TableCell>
                  <TableCell>Date</TableCell>
                  <TableCell align="right">Amount</TableCell>
                  <TableCell>Destination</TableCell>
                  <TableCell>Outcome</TableCell>
                  <TableCell align="right">Risk</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {settled.map((refund) => (
                  <TableRow key={refund.id}>
                    <TableCell className="mono">{refund.reference}</TableCell>
                    <TableCell><Typography variant="body2" color="text.secondary">{dateTime(refund.created_at)}</Typography></TableCell>
                    <TableCell align="right" className="tabular">{rupees(refund.amount)}</TableCell>
                    <TableCell className="mono"><Typography variant="body2">{refund.refund_destination}</Typography></TableCell>
                    <TableCell><StatusChip status={refund.status} /></TableCell>
                    <TableCell align="right"><RiskBadge score={refund.risk_score} /></TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </Box>
        </Card>
      ) : null}

      {active ? (
        <RefundSafetyDialog open onClose={() => setActive(null)} refund={active} analysis={analysis}
          onChanged={() => { reload(); setActive(null); }} />
      ) : null}
    </Box>
  );
}
