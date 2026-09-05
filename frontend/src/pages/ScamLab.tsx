import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Alert, Box, Button, Card, Checkbox, Chip, Divider, FormControlLabel, MenuItem,
  Step, StepContent, StepLabel, Stepper, TextField, Typography,
} from '@mui/material';
import { BadgeIndianRupee, RotateCcw, ShieldCheck, TriangleAlert, UserPlus, Wallet, Zap } from 'lucide-react';
import { api, errorMessage } from '../services/api';
import { useAuth } from '../hooks/useAuth';
import { rupees } from '../utils/format';
import { riskColor } from '../theme';
import { ErrorState } from '../components/StateViews';
import { RiskGauge, recommendationCopy } from '../components/RiskGauge';
import { RiskExplanation } from '../components/RiskExplanation';
import { SectionCard } from '../components/SectionCard';
import type { LabBatchRow, LabResolveResult, LabScamResult, ScamPreset, Transaction } from '../types';

export function ScamLab() {
  const navigate = useNavigate();
  const { user, openLabAccount, refresh } = useAuth();

  const [step, setStep] = useState(0);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [account, setAccount] = useState({ full_name: '', upi_handle: '', opening_balance: 50000, as_admin: false });
  const [credentials, setCredentials] = useState<{ email: string; password: string } | null>(null);

  const [funds, setFunds] = useState({ amount: 25000, from_handle: 'salary@hdfcbank' });
  const [added, setAdded] = useState<Transaction[]>([]);

  const [presets, setPresets] = useState<ScamPreset[]>([]);
  const [presetId, setPresetId] = useState('classic');
  const [scam, setScam] = useState({
    amount: 8000,
    sender_handle: 'abc123@upi',
    refund_destination: 'xyz987@upi',
    message: '',
    minutes_since_payment: 4,
  });
  const [result, setResult] = useState<LabScamResult | null>(null);
  const [outcome, setOutcome] = useState<LabResolveResult | null>(null);

  const [batchCount, setBatchCount] = useState(10);
  const [batch, setBatch] = useState<LabBatchRow[] | null>(null);

  useEffect(() => {
    api.scamPresets().then((rows) => {
      setPresets(rows);
      const first = rows.find((p) => p.id === 'classic') ?? rows[0];
      if (first) {
        setPresetId(first.id);
        setScam((s) => ({
          ...s,
          sender_handle: first.sender_handle,
          refund_destination: first.refund_destination,
          message: first.message,
        }));
      }
    }).catch(() => undefined);
  }, []);

  const applyPreset = (id: string) => {
    setPresetId(id);
    const preset = presets.find((p) => p.id === id);
    if (preset) {
      setScam((s) => ({
        ...s,
        sender_handle: preset.sender_handle,
        refund_destination: preset.refund_destination,
        message: preset.message,
      }));
    }
  };

  const guard = async (fn: () => Promise<void>) => {
    setBusy(true); setError(null);
    try { await fn(); } catch (err) { setError(errorMessage(err)); } finally { setBusy(false); }
  };

  const createAccount = () => guard(async () => {
    if (!account.full_name.trim()) {
      setError('Fill in the account holder name before creating the account.');
      return;
    }
    setCredentials(await openLabAccount({
      full_name: account.full_name.trim(),
      upi_handle: account.upi_handle.trim() || undefined,
      opening_balance: account.opening_balance,
      as_admin: account.as_admin,
    }));
    setAdded([]); setResult(null); setOutcome(null);
    setStep(1);
  });

  const addFunds = () => guard(async () => {
    if (!(funds.amount > 0)) {
      setError('Enter an amount greater than zero before adding funds.');
      return;
    }
    const res = await api.labFunds({ amount: funds.amount, from_handle: funds.from_handle });
    setAdded((rows) => [...rows, res.transaction]);
    await refresh();
  });

  const sendScam = () => guard(async () => {
    if (!(scam.amount > 0) || !scam.message.trim() || !scam.sender_handle.trim() || !scam.refund_destination.trim()) {
      setError('Fill in the amount, both handles and the message before sending.');
      return;
    }
    setResult(await api.labScam(scam));
    await refresh();
    setStep(3);
  });

  const resolve = (action: 'safe' | 'manual') => guard(async () => {
    if (!result) return;
    setOutcome(await api.labResolve(result.refund_request.id, action));
    await refresh();
  });

  const runBatch = () => guard(async () => {
    const res = await api.labBatch(batchCount);
    setBatch(res.rows);
    await refresh();
  });

  const restart = () => {
    setStep(0); setCredentials(null); setAdded([]); setResult(null); setOutcome(null); setError(null);
    setBatch(null);
    setAccount({ full_name: '', upi_handle: '', opening_balance: 50000, as_admin: false });
  };

  return (
    <Box sx={{ display: 'grid', gap: 2.5 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', gap: 2, flexWrap: 'wrap', alignItems: 'flex-start' }}>
        <Box>
          <Typography variant="h2">Scam Lab</Typography>
          <Typography color="text.secondary" sx={{ maxWidth: '72ch' }}>
            Build the situation yourself: open an account, put money in it, choose who pays you and
            what they say, then decide what to do. Or let a stream of randomised requests come at you
            and watch the engine sort them. Nothing here is scripted.
          </Typography>
        </Box>
        <Button startIcon={<RotateCcw size={15} />} onClick={restart} disabled={busy} color="inherit">
          Start over
        </Button>
      </Box>

      <Alert severity="info">
        Every account, rupee and handle here is synthetic. No real money moves and no real bank is contacted.
      </Alert>

      {error ? <ErrorState message={error} /> : null}

      <Card sx={{ p: { xs: 2, md: 3 } }}>
        <Stepper activeStep={step} orientation="vertical" nonLinear>
          {/* ------------------------------------------------ 1. account */}
          <Step completed={step > 0} expanded={step === 0}>
            <StepLabel
              onClick={() => setStep(0)}
              sx={{ cursor: 'pointer' }}
              optional={credentials ? (
                <Typography variant="caption" color="text.secondary" className="mono">{credentials.email}</Typography>
              ) : undefined}
            >
              Open an account
            </StepLabel>
            <StepContent>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2, maxWidth: '62ch' }}>
                This creates a brand new, completely empty account and signs you in as it — so every
                transaction that follows is one you made.
              </Typography>
              <Box sx={{ display: 'flex', gap: 1.5, flexWrap: 'wrap', mb: 2 }}>
                <TextField
                  label="Account holder name" size="small" required sx={{ width: 220 }}
                  value={account.full_name}
                  onChange={(e) => setAccount({ ...account, full_name: e.target.value })}
                  error={!!account.full_name && account.full_name.trim().length < 2}
                  helperText={
                    account.full_name.trim().length < 2 && account.full_name
                      ? 'At least two characters.'
                      : 'Required'
                  }
                />
                <TextField
                  label="UPI handle" size="small" sx={{ width: 220 }} placeholder="auto from the name"
                  value={account.upi_handle}
                  onChange={(e) => setAccount({ ...account, upi_handle: e.target.value })}
                />
                <TextField
                  label="Opening balance" type="number" size="small" sx={{ width: 160 }}
                  value={account.opening_balance}
                  onChange={(e) => setAccount({ ...account, opening_balance: Number(e.target.value) })}
                />
              </Box>
              <FormControlLabel
                sx={{ display: 'block', mb: 1.5, ml: 0 }}
                control={(
                  <Checkbox
                    size="small" checked={account.as_admin}
                    onChange={(e) => setAccount({ ...account, as_admin: e.target.checked })}
                  />
                )}
                label={<Typography variant="body2" color="text.secondary">Also grant analyst access</Typography>}
              />
              <Button
                variant="contained" startIcon={<UserPlus size={16} />}
                disabled={busy || account.full_name.trim().length < 2}
                onClick={createAccount}
              >
                {busy ? 'Creating…' : 'Create the account'}
              </Button>

              {credentials ? (
                <Alert severity="success" sx={{ mt: 2 }}>
                  <Typography variant="body2" sx={{ fontWeight: 650, mb: 0.5 }}>
                    Signed in as this account. Save the password — it isn't shown again.
                  </Typography>
                  <Typography variant="body2" className="mono">{credentials.email}</Typography>
                  <Typography variant="body2" className="mono">{credentials.password}</Typography>
                </Alert>
              ) : null}
            </StepContent>
          </Step>

          {/* -------------------------------------------------- 2. funds */}
          <Step completed={added.length > 0} expanded={step === 1}>
            <StepLabel
              onClick={() => setStep(1)}
              sx={{ cursor: 'pointer' }}
              optional={(
                <Typography variant="caption" color="text.secondary">
                  Balance {rupees(user?.balance ?? 0)}
                </Typography>
              )}
            >
              Add funds
            </StepLabel>
            <StepContent>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2, maxWidth: '62ch' }}>
                Ordinary money in. This matters: the scam only costs you something if there is real
                balance behind the payment you send back.
              </Typography>
              <Box sx={{ display: 'flex', gap: 1.5, flexWrap: 'wrap', alignItems: 'center', mb: 2 }}>
                <TextField
                  label="Amount" type="number" size="small" required sx={{ width: 150 }}
                  value={funds.amount}
                  onChange={(e) => setFunds({ ...funds, amount: Number(e.target.value) })}
                  error={!(funds.amount > 0)}
                  helperText={funds.amount > 0 ? 'Required' : 'Must be more than zero'}
                />
                <TextField
                  label="From" size="small" sx={{ width: 220 }}
                  value={funds.from_handle}
                  onChange={(e) => setFunds({ ...funds, from_handle: e.target.value })}
                />
                <Button
                  variant="outlined" startIcon={<Wallet size={16} />}
                  disabled={busy || funds.amount <= 0} onClick={addFunds}
                >
                  Add funds
                </Button>
              </Box>

              {added.length ? (
                <Box sx={{ display: 'grid', gap: 0.5, mb: 2 }}>
                  {added.map((tx) => (
                    <Typography key={tx.id} variant="body2" color="text.secondary">
                      + {rupees(tx.amount)} from <span className="mono">{tx.sender_handle}</span>
                    </Typography>
                  ))}
                </Box>
              ) : null}

              <Button variant="contained" onClick={() => setStep(2)} disabled={busy}>
                Next: bring in the scam
              </Button>
            </StepContent>
          </Step>

          {/* --------------------------------------------------- 3. scam */}
          <Step completed={!!result} expanded={step === 2}>
            <StepLabel onClick={() => setStep(2)} sx={{ cursor: 'pointer' }}>
              Bring in the scam
            </StepLabel>
            <StepContent>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2, maxWidth: '62ch' }}>
                A payment arrives from a stranger, then the message asking for it back. Change any of
                it — the refund destination is the field that matters most.
              </Typography>

              <TextField
                select label="Scenario" size="small" sx={{ width: 280, mb: 2 }}
                value={presetId} onChange={(e) => applyPreset(e.target.value)}
              >
                {presets.map((preset) => (
                  <MenuItem key={preset.id} value={preset.id}>{preset.label}</MenuItem>
                ))}
              </TextField>

              <Box sx={{ display: 'flex', gap: 1.5, flexWrap: 'wrap', mb: 2 }}>
                <TextField
                  label="Amount" type="number" size="small" required sx={{ width: 130 }}
                  value={scam.amount}
                  onChange={(e) => setScam({ ...scam, amount: Number(e.target.value) })}
                  error={!(scam.amount > 0)}
                  helperText={scam.amount > 0 ? 'Required' : 'Must be more than zero'}
                />
                <TextField
                  label="Paid in from" size="small" sx={{ width: 210 }}
                  value={scam.sender_handle}
                  onChange={(e) => setScam({ ...scam, sender_handle: e.target.value })}
                />
                <TextField
                  label="Refund wanted to" size="small" sx={{ width: 210 }}
                  value={scam.refund_destination}
                  onChange={(e) => setScam({ ...scam, refund_destination: e.target.value })}
                  helperText={
                    scam.refund_destination.trim().toLowerCase() === scam.sender_handle.trim().toLowerCase()
                      ? 'Same account — this is what a real mistake looks like'
                      : 'Different account — the tell'
                  }
                />
                <TextField
                  label="Minutes later" type="number" size="small" sx={{ width: 130 }}
                  value={scam.minutes_since_payment}
                  onChange={(e) => setScam({ ...scam, minutes_since_payment: Number(e.target.value) })}
                />
              </Box>

              <TextField
                label="The message they send" multiline minRows={3} fullWidth size="small" sx={{ mb: 2 }}
                value={scam.message}
                onChange={(e) => setScam({ ...scam, message: e.target.value })}
              />

              <Button
                variant="contained" startIcon={<BadgeIndianRupee size={16} />}
                disabled={busy || !scam.message.trim() || !(scam.amount > 0)} onClick={sendScam}
              >
                {busy ? 'Sending…' : 'Send the payment and the message'}
              </Button>
            </StepContent>
          </Step>

          {/* ------------------------------------------------ 4. decide */}
          <Step completed={!!outcome} expanded={step === 3}>
            <StepLabel onClick={() => result && setStep(3)} sx={{ cursor: result ? 'pointer' : 'default' }}>
              See it scored, then decide
            </StepLabel>
            <StepContent>
              {result ? (
                <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', lg: '0.9fr 1.1fr' }, gap: 3, alignItems: 'start' }}>
                  <SectionCard title="Refund safety score">
                    <Box sx={{ py: 1 }}>
                      <RiskGauge
                        safetyScore={result.analysis.safety_score}
                        riskScore={result.analysis.risk_score}
                        level={result.analysis.risk_level}
                        recommendation={result.analysis.recommendation}
                      />
                    </Box>
                    <Divider sx={{ my: 2.5 }} />
                    <RiskExplanation
                      signals={result.analysis.signals}
                      components={result.analysis.components}
                      mlDisclaimer={result.analysis.ml_disclaimer}
                      limit={8}
                    />
                  </SectionCard>

                  <Box sx={{ display: 'grid', gap: 3 }}>
                    <SectionCard
                      title="What will you do?"
                      action={<Chip size="small" label={`Balance ${rupees(user?.balance ?? 0)}`} variant="outlined" />}
                    >
                      {!outcome ? (
                        <>
                          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                            {rupees(result.transaction.amount)} is sitting in the account. A safe refund
                            returns it along the original payment. A manual transfer sends it to the
                            handle they gave you.
                          </Typography>
                          <Box sx={{ display: 'flex', gap: 1.5, flexWrap: 'wrap' }}>
                            <Button
                              variant="contained" startIcon={<ShieldCheck size={17} />}
                              disabled={busy} onClick={() => resolve('safe')}
                            >
                              Use safe refund
                            </Button>
                            <Button
                              variant="outlined" color="error" startIcon={<TriangleAlert size={17} />}
                              disabled={busy} onClick={() => resolve('manual')}
                            >
                              Transfer manually
                            </Button>
                          </Box>
                        </>
                      ) : (
                        <>
                          <Box sx={{ display: 'grid', gap: 1, mb: 2 }}>
                            {outcome.events.map((event) => (
                              <Typography key={event} variant="body2" color="text.secondary">— {event}</Typography>
                            ))}
                          </Box>
                          <Alert severity={outcome.loss > 0 ? 'error' : 'success'} sx={{ mb: 2 }}>
                            {outcome.loss > 0
                              ? `Net loss: ${rupees(outcome.loss)} of your own money.`
                              : 'Nothing was lost. The money went back where it came from.'}
                          </Alert>
                          <Box sx={{ display: 'flex', gap: 1.5, flexWrap: 'wrap' }}>
                            {outcome.incident ? (
                              <Button variant="contained" onClick={() => navigate(`/app/incidents/${outcome.incident!.id}`)}>
                                Open case {outcome.incident.case_id}
                              </Button>
                            ) : null}
                            <Button variant="outlined" onClick={() => navigate('/app/transactions')}>
                              See the transactions
                            </Button>
                            <Button color="inherit" onClick={restart}>Run it again</Button>
                          </Box>
                        </>
                      )}
                    </SectionCard>
                  </Box>
                </Box>
              ) : (
                <Typography variant="body2" color="text.secondary">
                  Send a payment and message in the previous step first.
                </Typography>
              )}
            </StepContent>
          </Step>
        </Stepper>
      </Card>

      {/* -------------------------------------------- automated request stream */}
      <SectionCard
        title="Or let them come at you"
        subtitle="Randomised refund requests, scored as they arrive. Roughly 60% scams, 20% borderline and 20% genuine mistakes — the mix is what makes the spread meaningful."
      >
        <Box sx={{ display: 'flex', gap: 1.5, flexWrap: 'wrap', alignItems: 'center', mb: batch ? 2.5 : 0 }}>
          <TextField
            label="How many" type="number" size="small" sx={{ width: 130 }}
            value={batchCount}
            onChange={(e) => setBatchCount(Math.max(1, Math.min(25, Number(e.target.value))))}
            inputProps={{ min: 1, max: 25 }}
          />
          <Button
            variant="contained" startIcon={<Zap size={16} />}
            disabled={busy || !user} onClick={runBatch}
          >
            {busy ? 'Generating…' : 'Generate requests'}
          </Button>
          {batch ? (
            <Typography variant="body2" color="text.secondary">
              {batch.filter((r) => r.risk_level === 'CRITICAL' || r.risk_level === 'HIGH').length} of {batch.length} flagged
            </Typography>
          ) : null}
        </Box>

        {batch ? (
          <Box sx={{ overflowX: 'auto' }}>
            <Box component="table" sx={{ width: '100%', minWidth: 720, borderCollapse: 'collapse' }}>
              <Box component="thead">
                <Box component="tr" sx={{ '& th': { textAlign: 'left', py: 1, px: 1, fontSize: '0.74rem', fontWeight: 700, color: 'text.secondary', borderBottom: '1px solid', borderColor: 'divider', letterSpacing: '0.04em' } }}>
                  <th>ACTUALLY</th>
                  <th>AMOUNT</th>
                  <th>PAID IN FROM</th>
                  <th>REFUND TO</th>
                  <th>AFTER</th>
                  <th>RISK</th>
                  <th>VERDICT</th>
                </Box>
              </Box>
              <Box component="tbody">
                {batch.map((row) => (
                  <Box
                    key={row.refund_request_id}
                    component="tr"
                    sx={{ '& td': { py: 1, px: 1, borderBottom: '1px solid', borderColor: 'divider', fontSize: '0.84rem', verticalAlign: 'middle' } }}
                  >
                    <td>
                      <Chip
                        size="small"
                        label={row.kind}
                        variant="outlined"
                        color={row.kind === 'scam' ? 'error' : row.kind === 'genuine' ? 'success' : 'warning'}
                      />
                    </td>
                    <td className="tabular">{rupees(row.amount)}</td>
                    <td className="mono" style={{ fontSize: '0.78rem' }}>{row.sender_handle}</td>
                    <td className="mono" style={{ fontSize: '0.78rem' }}>
                      {row.refund_destination}
                      {row.refund_destination === row.sender_handle ? null : (
                        <Typography component="span" variant="caption" color="error" sx={{ ml: 0.75 }}>
                          ≠ payer
                        </Typography>
                      )}
                    </td>
                    <td className="tabular">{row.minutes_since_payment} min</td>
                    <td className="tabular" style={{ fontWeight: 700, color: riskColor(row.risk_level) }}>
                      {row.risk_score}
                    </td>
                    <td>
                      <Typography variant="caption" sx={{ fontWeight: 700, color: riskColor(row.risk_level) }}>
                        {row.risk_level}
                      </Typography>
                      <Typography variant="caption" color="text.secondary" sx={{ display: 'block' }}>
                        {recommendationCopy(row.recommendation)}
                      </Typography>
                    </td>
                  </Box>
                ))}
              </Box>
            </Box>
            <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 1.5 }}>
              The "actually" column is ground truth from the generator, shown so you can check the
              engine against it. The engine never sees it.
            </Typography>
          </Box>
        ) : null}
      </SectionCard>
    </Box>
  );
}
