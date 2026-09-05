import { useState } from 'react';
import {
  Alert, Box, Button, Dialog, DialogActions, DialogContent, DialogTitle, Divider,
  Paper, Typography,
} from '@mui/material';
import { ArrowRight, ShieldCheck, TriangleAlert } from 'lucide-react';
import { api, errorMessage } from '../services/api';
import { rupees } from '../utils/format';
import type { RefundAnalysis, RefundRequest } from '../types';
import { RiskGauge } from './RiskGauge';
import { RiskExplanation } from './RiskExplanation';

type Stage = 'check' | 'safe' | 'done';

/**
 * Opens instead of processing a refund. The whole point of the product lives
 * here: the user sees the score before the money can move.
 */
export function RefundSafetyDialog({
  open, onClose, refund, analysis, onChanged,
}: {
  open: boolean;
  onClose: () => void;
  refund: RefundRequest;
  analysis: RefundAnalysis | null;
  onChanged?: () => void;
}) {
  const [stage, setStage] = useState<Stage>('check');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<{ refund_id: string; status: string; mode: string; message: string } | null>(null);

  const level = analysis?.risk_level ?? refund.risk_level;
  const risk = analysis?.risk_score ?? refund.risk_score;
  const safety = analysis?.safety_score ?? refund.safety_score;
  const mismatch = !refund.destination_matches_sender;

  const close = () => { setStage('check'); setResult(null); setError(null); onClose(); };

  const runSafeRefund = async () => {
    setBusy(true); setError(null);
    try {
      setResult(await api.safeRefund(refund.id));
      setStage('done');
      onChanged?.();
    } catch (err) { setError(errorMessage(err)); } finally { setBusy(false); }
  };

  const recordManual = async () => {
    setBusy(true); setError(null);
    try {
      await api.manualRefund(refund.id);
      onChanged?.();
      close();
    } catch (err) { setError(errorMessage(err)); } finally { setBusy(false); }
  };

  return (
    <Dialog open={open} onClose={close} maxWidth="sm" fullWidth>
      <DialogTitle sx={{ pb: 0.5 }}>
        {stage === 'check' ? 'Refund safety check' : stage === 'safe' ? 'Safe refund' : 'Refund started'}
      </DialogTitle>

      <DialogContent>
        {error ? <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert> : null}

        {stage === 'check' ? (
          <>
            <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', sm: '1fr 1fr' }, gap: 1.5, mb: 2 }}>
              <Field label="Amount" value={rupees(refund.amount)} />
              <Field label="Requested" value={`${Math.max(1, Math.round(refund.seconds_since_payment / 60))} min after the credit`} />
              <Field label="Original sender" value={refund.original_sender} mono />
              <Field label="Refund destination" value={refund.refund_destination} mono tone={mismatch ? '#c0342b' : undefined} />
            </Box>

            {mismatch ? (
              <Alert severity="error" icon={<TriangleAlert size={18} />} sx={{ mb: 2.5 }}>
                The money is being asked for at a different account from the one that paid you.
                A real mistaken payment can always be returned to its source.
              </Alert>
            ) : null}

            <Box sx={{ py: 1.5 }}>
              <RiskGauge safetyScore={safety} riskScore={risk} level={level} recommendation={analysis?.recommendation ?? refund.recommendation} />
            </Box>

            <Divider sx={{ my: 2.5 }} />

            {analysis ? (
              <RiskExplanation signals={analysis.signals} components={analysis.components} mlDisclaimer={analysis.ml_disclaimer} limit={7} />
            ) : null}
          </>
        ) : null}

        {stage === 'safe' ? (
          <Box sx={{ display: 'grid', gap: 1.5 }}>
            <Typography variant="body2" color="text.secondary">
              The refund goes back along the original payment, so it can only reach the account the
              money came from. The handle you were sent is not used.
            </Typography>
            <Paper variant="outlined" sx={{ p: 2, display: 'grid', gap: 1.25 }}>
              <Field
                label="Original transaction"
                value={refund.transaction_reference ?? `Transaction #${refund.transaction_id}`}
              />
              <Field label="Amount" value={rupees(refund.amount)} />
              <Box sx={{ display: 'flex', gap: 1.5, alignItems: 'center' }}>
                <Field label="Requested destination" value={refund.refund_destination} mono tone="#c0342b" />
                <ArrowRight size={16} color="#5a6a7d" />
                <Field label="Actual destination" value={refund.original_sender} mono tone="#0f9d74" />
              </Box>
            </Paper>
            <Alert severity="info">This build uses a simulated refund. No funds move anywhere.</Alert>
          </Box>
        ) : null}

        {stage === 'done' && result ? (
          <Box sx={{ display: 'grid', gap: 1.5, py: 1 }}>
            <Box sx={{ display: 'flex', gap: 1.25, alignItems: 'center', color: '#0f9d74' }}>
              <ShieldCheck size={22} />
              <Typography variant="h5">Refund initiated</Typography>
            </Box>
            <Field label="Refund ID" value={result.refund_id} mono />
            <Field label="Status" value={result.status} />
            <Field label="Mode" value={result.mode.replace(/_/g, ' ').toLowerCase()} />
            <Alert severity="success">{result.message}</Alert>
          </Box>
        ) : null}
      </DialogContent>

      <DialogActions sx={{ px: 3, pb: 2.5, gap: 1, flexWrap: 'wrap' }}>
        {stage === 'check' ? (
          <>
            <Button onClick={close} color="inherit">Cancel</Button>
            <Box sx={{ flex: 1 }} />
            <Button onClick={recordManual} disabled={busy} color="error" variant="outlined">
              Transfer manually anyway
            </Button>
            <Button onClick={() => setStage('safe')} variant="contained" startIcon={<ShieldCheck size={16} />}>
              Use safe refund
            </Button>
          </>
        ) : null}
        {stage === 'safe' ? (
          <>
            <Button onClick={() => setStage('check')} color="inherit">Back</Button>
            <Box sx={{ flex: 1 }} />
            <Button onClick={runSafeRefund} variant="contained" disabled={busy}>
              {busy ? 'Starting…' : 'Start safe refund'}
            </Button>
          </>
        ) : null}
        {stage === 'done' ? <Button onClick={close} variant="contained">Done</Button> : null}
      </DialogActions>
    </Dialog>
  );
}

function Field({ label, value, mono, tone }: { label: string; value: string; mono?: boolean; tone?: string }) {
  return (
    <Box>
      <Typography variant="caption" color="text.secondary">{label}</Typography>
      <Typography className={mono ? 'mono' : undefined} sx={{ fontWeight: 600, fontSize: '0.9rem', color: tone, wordBreak: 'break-all' }}>
        {value}
      </Typography>
    </Box>
  );
}
