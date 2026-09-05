import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Alert, Box, Button, Card, Divider, Typography } from '@mui/material';
import { Play, RotateCcw, ShieldCheck, TriangleAlert } from 'lucide-react';
import { api, errorMessage } from '../services/api';
import { useAuth } from '../hooks/useAuth';
import { rupees } from '../utils/format';
import { ErrorState } from '../components/StateViews';
import { RiskGauge } from '../components/RiskGauge';
import { RiskExplanation } from '../components/RiskExplanation';
import { BehaviorTimeline } from '../components/BehaviorTimeline';
import { EvidenceMeter } from '../components/EvidenceMeter';
import { SectionCard } from '../components/SectionCard';
import { TestModePayment } from '../components/TestModePayment';
import type { SimulationResult, Transaction } from '../types';

export function Simulate() {
  const navigate = useNavigate();
  const { refresh } = useAuth();
  const [result, setResult] = useState<SimulationResult | null>(null);
  const [paid, setPaid] = useState<Transaction | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const run = async (unsafe: boolean) => {
    setBusy(true); setError(null);
    try { setResult(await api.simulate(unsafe)); await refresh(); }
    catch (err) { setError(errorMessage(err)); }
    finally { setBusy(false); }
  };

  const reset = async () => {
    setBusy(true); setError(null);
    try { await api.resetDemo(); setResult(null); setPaid(null); await refresh(); }
    catch (err) { setError(errorMessage(err)); }
    finally { setBusy(false); }
  };

  return (
    <Box sx={{ display: 'grid', gap: 2.5 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', gap: 2, flexWrap: 'wrap', alignItems: 'flex-start' }}>
        <Box>
          <Typography variant="h2">Simulate the scam</Typography>
          <Typography color="text.secondary" sx={{ maxWidth: '70ch' }}>
            Play out the whole attack against synthetic data: the payment arrives, the refund is
            demanded to a different handle, and you choose what happens next.
          </Typography>
        </Box>
        <Button startIcon={<RotateCcw size={15} />} onClick={reset} disabled={busy} color="inherit">
          Reset demo data
        </Button>
      </Box>

      <Alert severity="info">
        Nothing here touches a bank. Every amount, handle and balance is fabricated.
      </Alert>

      {error ? <ErrorState message={error} /> : null}

      <TestModePayment onPaid={setPaid} />

      {paid ? (
        <Alert
          severity="success"
          action={
            <Button size="small" onClick={() => navigate(`/app/transactions/${paid.reference}`)}>
              Open {paid.reference}
            </Button>
          }
        >
          {rupees(paid.amount)} received through Razorpay Test Mode from {paid.sender_handle}. A
          refund on this payment can only go back to the account that paid.
        </Alert>
      ) : null}

      {!result ? (
        <Card sx={{ p: { xs: 3, md: 5 }, textAlign: 'center' }}>
          <Box sx={{ display: 'grid', gap: 1.5, maxWidth: 520, mx: 'auto' }}>
            <Typography variant="h3">₹8,000 lands in your account from a stranger</Typography>
            <Typography color="text.secondary">
              Four minutes later they message: "Sorry, sent by mistake. Please send it back urgently
              to my wife's UPI." Choose how the story ends.
            </Typography>
            <Box sx={{ display: 'flex', gap: 1.5, justifyContent: 'center', flexWrap: 'wrap', mt: 2 }}>
              <Button variant="contained" size="large" startIcon={<ShieldCheck size={17} />}
                disabled={busy} onClick={() => run(false)}>
                Use safe refund
              </Button>
              <Button variant="outlined" color="error" size="large" startIcon={<TriangleAlert size={17} />}
                disabled={busy} onClick={() => run(true)}>
                Transfer manually
              </Button>
            </Box>
            {busy ? <Typography variant="caption" color="text.secondary">Running the sequence…</Typography> : null}
          </Box>
        </Card>
      ) : null}

      {result ? (
        <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', lg: '1fr 1fr' }, gap: 3, alignItems: 'start' }}>
          <Box sx={{ display: 'grid', gap: 3 }}>
            <SectionCard title="Refund safety score">
              <Box sx={{ py: 1 }}>
                <RiskGauge
                  safetyScore={result.analysis.safety_score}
                  riskScore={result.analysis.risk_score}
                  level={result.analysis.risk_level}
                  recommendation={result.analysis.recommendation}
                />
              </Box>
              <Divider sx={{ my: 3 }} />
              <RiskExplanation signals={result.analysis.signals} components={result.analysis.components}
                mlDisclaimer={result.analysis.ml_disclaimer} limit={8} />
            </SectionCard>
          </Box>

          <Box sx={{ display: 'grid', gap: 3 }}>
            <SectionCard title="What happened">
              <BehaviorTimeline items={result.steps.map((step) => ({
                id: step.step,
                occurred_at: step.at,
                title: step.title,
                detail: step.detail,
                severity: step.step >= 5 && result.incident ? 'critical' : step.step === 4 ? 'warning' : 'info',
              }))} />
            </SectionCard>

            {result.incident ? (
              <SectionCard title={`Case ${result.incident.case_id} opened`}>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                  {rupees(result.incident.potential_loss)} left the account. Safe Mode is now on, the
                  timeline is built and the evidence checklist has been started.
                </Typography>
                {result.completeness ? <EvidenceMeter data={result.completeness} compact /> : null}
                <Box sx={{ display: 'flex', gap: 1.5, mt: 2.5, flexWrap: 'wrap' }}>
                  <Button variant="contained" onClick={() => navigate(`/app/incidents/${result.incident!.id}`)}>
                    Open the case
                  </Button>
                  <Button variant="outlined" onClick={() => navigate('/app/evidence')}>Add evidence</Button>
                </Box>
              </SectionCard>
            ) : (
              <SectionCard title="Safe refund used">
                <Typography variant="body2" color="text.secondary">
                  The money went back along the original payment instead of to the handle you were sent.
                  No case was needed, because nothing was lost.
                </Typography>
                <Button variant="outlined" sx={{ mt: 2 }} startIcon={<Play size={15} />}
                  onClick={() => setResult(null)}>
                  Run it the other way
                </Button>
              </SectionCard>
            )}
          </Box>
        </Box>
      ) : null}
    </Box>
  );
}
