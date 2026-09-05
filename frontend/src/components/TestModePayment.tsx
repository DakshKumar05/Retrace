import { useEffect, useState } from 'react';
import { Alert, Box, Button, Chip, TextField, Typography } from '@mui/material';
import { CreditCard } from 'lucide-react';
import { api, errorMessage } from '../services/api';
import { SectionCard } from './SectionCard';
import type { PaymentsConfig, Transaction } from '../types';

const CHECKOUT_SRC = 'https://checkout.razorpay.com/v1/checkout.js';

declare global {
  interface Window {
    Razorpay?: new (options: Record<string, unknown>) => { open: () => void };
  }
}

/** Load Checkout once, reusing the tag if it is already on the page. */
const loadCheckout = () =>
  new Promise<void>((resolve, reject) => {
    if (window.Razorpay) return resolve();
    const existing = document.querySelector<HTMLScriptElement>(`script[src="${CHECKOUT_SRC}"]`);
    if (existing) {
      existing.addEventListener('load', () => resolve());
      existing.addEventListener('error', () => reject(new Error('Could not load Razorpay Checkout.')));
      return;
    }
    const script = document.createElement('script');
    script.src = CHECKOUT_SRC;
    script.async = true;
    script.onload = () => resolve();
    script.onerror = () => reject(new Error('Could not load Razorpay Checkout.'));
    document.body.appendChild(script);
  });

export function TestModePayment({ onPaid }: { onPaid: (transaction: Transaction) => void }) {
  const [config, setConfig] = useState<PaymentsConfig | null>(null);
  const [amount, setAmount] = useState(8000);
  const [sender, setSender] = useState('unknown@upi');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [note, setNote] = useState<string | null>(null);

  useEffect(() => {
    api.paymentsConfig().then(setConfig).catch(() => setConfig(null));
  }, []);

  if (!config?.enabled) return null;

  const pay = async () => {
    setBusy(true); setError(null); setNote(null);
    try {
      await loadCheckout();
      const order = await api.createPaymentOrder(amount, sender);
      const checkout = new window.Razorpay!({
        key: order.key_id,
        order_id: order.order_id,
        amount: Math.round(order.amount * 100),
        currency: order.currency,
        name: 'Retrace',
        description: 'Test Mode credit for the refund-scam walkthrough',
        handler: async (response: Record<string, string>) => {
          try {
            const result = await api.verifyPayment({
              razorpay_order_id: response.razorpay_order_id,
              razorpay_payment_id: response.razorpay_payment_id,
              razorpay_signature: response.razorpay_signature,
              sender_handle: sender,
            });
            setNote(result.message);
            onPaid(result.transaction);
          } catch (err) {
            setError(errorMessage(err));
          } finally {
            setBusy(false);
          }
        },
        modal: { ondismiss: () => setBusy(false) },
        theme: { color: '#0b7285' },
      });
      checkout.open();
    } catch (err) {
      setError(errorMessage(err));
      setBusy(false);
    }
  };

  return (
    <SectionCard
      title="Receive a real Test Mode payment"
      action={<Chip size="small" color="success" variant="outlined" label={config.mode.replace(/_/g, ' ')} />}
    >
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2, maxWidth: '70ch' }}>
        This opens Razorpay Checkout in test mode and produces a genuine payment id. The refund that
        follows is a real Razorpay refund against that payment, which is why it can only reach the
        account that paid — never the handle a scammer supplies.
      </Typography>

      <Box sx={{ display: 'flex', gap: 1.5, flexWrap: 'wrap', alignItems: 'flex-start' }}>
        <TextField
          label="Amount" type="number" size="small" value={amount}
          onChange={(e) => setAmount(Number(e.target.value))}
          sx={{ width: 140 }} inputProps={{ min: 1, max: 100000 }}
        />
        <TextField
          label="Claimed sender handle" size="small" value={sender}
          onChange={(e) => setSender(e.target.value)} sx={{ width: 220 }}
        />
        <Button variant="contained" startIcon={<CreditCard size={16} />} disabled={busy} onClick={pay}>
          {busy ? 'Waiting for Checkout…' : 'Open Razorpay Checkout'}
        </Button>
      </Box>

      {note ? <Alert severity="success" sx={{ mt: 2 }}>{note}</Alert> : null}
      {error ? <Alert severity="error" sx={{ mt: 2 }}>{error}</Alert> : null}
      {!config.webhook_configured ? (
        <Alert severity="info" sx={{ mt: 2 }}>
          No webhook secret is set, so refund status updates arrive only when the API is polled.
          Set RAZORPAY_WEBHOOK_SECRET to receive them from Razorpay directly.
        </Alert>
      ) : null}
    </SectionCard>
  );
}
