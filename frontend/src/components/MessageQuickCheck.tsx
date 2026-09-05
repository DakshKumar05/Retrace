import { useState } from 'react';
import { Alert, Box, Button, Card, Chip, Collapse, Divider, TextField, Typography } from '@mui/material';
import { ChevronDown, ChevronUp, MessageSquare } from 'lucide-react';
import { api, errorMessage } from '../services/api';
import { riskColor } from '../theme';
import { ErrorState } from './StateViews';
import { RiskExplanation } from './RiskExplanation';
import { recommendationCopy } from './RiskGauge';
import type { MessageAnalysis } from '../types';

const SAMPLE = `Hi bro, I accidentally sent ₹8,000 to you.
Please send it to my wife's UPI urgently.
My account isn't working.`;

/**
 * A message doesn't always arrive with a refund request already attached to
 * it in the system — someone forwards a suspicious text before any payment
 * or refund exists yet. This runs the NLP layer alone (no transaction, no
 * rules, no ML) against just the words, so that check doesn't need one.
 * Collapsed by default: it's a secondary tool on a page whose main job is
 * the list of refund requests that already have a score.
 */
export function MessageQuickCheck() {
  const [open, setOpen] = useState(false);
  const [text, setText] = useState('');
  const [result, setResult] = useState<MessageAnalysis | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const analyze = async () => {
    setBusy(true); setError(null);
    try { setResult(await api.analyzeMessage(text)); }
    catch (err) { setError(errorMessage(err)); }
    finally { setBusy(false); }
  };

  const color = result ? riskColor(result.risk_level) : undefined;

  return (
    <Card sx={{ overflow: 'hidden' }}>
      <Box
        onClick={() => setOpen((v) => !v)}
        sx={{
          display: 'flex', alignItems: 'center', gap: 1.25, px: 2.5, py: 1.75, cursor: 'pointer',
          '&:hover': { bgcolor: 'action.hover' },
        }}
      >
        <MessageSquare size={18} color="#5a6a7d" />
        <Box sx={{ flex: 1, minWidth: 0 }}>
          <Typography sx={{ fontWeight: 650 }}>Check a message</Typography>
          <Typography variant="body2" color="text.secondary">
            Got a message before there's a refund request to review? Paste it here — no transaction needed.
          </Typography>
        </Box>
        {open ? <ChevronUp size={18} color="#5a6a7d" /> : <ChevronDown size={18} color="#5a6a7d" />}
      </Box>

      <Collapse in={open}>
        <Divider />
        <Box sx={{ p: 2.5, display: 'grid', gridTemplateColumns: { xs: '1fr', md: '1fr 1fr' }, gap: 3 }}>
          <Box>
            <TextField
              multiline minRows={6} fullWidth placeholder="Paste the WhatsApp or SMS message here"
              value={text} onChange={(event) => setText(event.target.value)}
              inputProps={{ maxLength: 5000 }}
            />
            <Box sx={{ display: 'flex', gap: 1.5, mt: 2, flexWrap: 'wrap' }}>
              <Button variant="contained" disabled={busy || !text.trim()} onClick={analyze}>
                {busy ? 'Analyzing…' : 'Analyze message'}
              </Button>
              <Button onClick={() => { setText(SAMPLE); setResult(null); }} color="inherit">Use an example</Button>
              {text ? <Button onClick={() => { setText(''); setResult(null); }} color="inherit">Clear</Button> : null}
            </Box>
            <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 1.5 }}>
              The text stays on your own server. Nothing is sent to a third party. This checks only the
              wording — it doesn't know the amount, timing or destination, so a full refund request still
              gets the complete score above.
            </Typography>
          </Box>

          <Box>
            {error ? <ErrorState message={error} /> : null}

            {result ? (
              <Box>
                <Box sx={{ display: 'flex', alignItems: 'baseline', gap: 1.5 }}>
                  <Typography className="tabular" sx={{ fontSize: '2.2rem', fontWeight: 800, letterSpacing: '-0.03em', color }}>
                    {result.message_risk_score}
                  </Typography>
                  <Typography color="text.secondary">/ 100 message risk</Typography>
                </Box>
                <Typography sx={{ fontWeight: 700, color, letterSpacing: '0.05em', mb: 1.5, fontSize: '0.85rem' }}>
                  {result.risk_level} RISK
                </Typography>
                <Alert
                  severity={result.message_risk_score >= 61 ? 'error' : result.message_risk_score >= 31 ? 'warning' : 'success'}
                  sx={{ mb: 2 }}
                >
                  {recommendationCopy(result.recommendation)}
                </Alert>

                {result.extracted_handles.length ? (
                  <Box sx={{ mb: 2 }}>
                    <Typography variant="body2" sx={{ fontWeight: 650, mb: 0.75 }}>Payment destinations in the message</Typography>
                    <Box sx={{ display: 'flex', gap: 0.75, flexWrap: 'wrap' }}>
                      {result.extracted_handles.map((handle) => (
                        <Chip key={handle} size="small" label={handle} className="mono"
                          sx={{ color: '#c0342b', bgcolor: '#c0342b14', border: '1px solid #c0342b33' }} />
                      ))}
                    </Box>
                  </Box>
                ) : null}

                {result.signals.length ? (
                  <RiskExplanation signals={result.signals} />
                ) : (
                  <Typography variant="body2" color="text.secondary">
                    No scam patterns matched. That is not a guarantee the message is genuine, only that
                    nothing in it looks like the usual refund-scam language.
                  </Typography>
                )}
              </Box>
            ) : (
              <Box sx={{
                height: '100%', display: 'grid', placeContent: 'center', textAlign: 'center',
                border: '1px dashed', borderColor: 'divider', borderRadius: 1.5, p: 3, color: 'text.secondary',
              }}>
                <Typography variant="body2">Paste a message and the result shows up here.</Typography>
              </Box>
            )}
          </Box>
        </Box>
      </Collapse>
    </Card>
  );
}
