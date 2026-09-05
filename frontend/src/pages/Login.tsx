import { useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import {
  Alert, Box, Button, Card, Container, Divider, Link, Paper, TextField, Typography,
} from '@mui/material';
import { ShieldCheck } from 'lucide-react';
import { useAuth } from '../hooks/useAuth';
import { errorMessage } from '../services/api';
import { DEMO_CREDENTIALS } from '../utils/demo';
import { ThemeToggle } from '../components/ThemeToggle';

const DEMO = DEMO_CREDENTIALS;

export function Login() {
  const { signIn, signUp } = useAuth();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const [mode, setMode] = useState<'login' | 'register'>('login');
  const [form, setForm] = useState({ email: '', fullName: '', password: '' });
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const destination = params.get('next') === 'simulate' ? '/app/simulate' : '/app/dashboard';

  const submit = async (email: string, password: string, fullName?: string) => {
    setBusy(true); setError(null);
    try {
      if (mode === 'register' && fullName) await signUp(email, fullName, password);
      else await signIn(email, password);
      navigate(destination);
    } catch (err) { setError(errorMessage(err)); } finally { setBusy(false); }
  };

  return (
    <Box sx={{ minHeight: '100vh', display: 'grid', placeItems: 'center', p: 2, position: 'relative' }}>
      <Box sx={{ position: 'absolute', top: 12, right: 12 }}>
        <ThemeToggle />
      </Box>
      <Container maxWidth="xs" disableGutters>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.25, justifyContent: 'center', mb: 3 }}>
          <ShieldCheck size={24} color="#1e6fd9" />
          <Typography sx={{ fontWeight: 750, fontSize: '1.2rem', letterSpacing: '-0.02em' }}>Retrace</Typography>
        </Box>

        <Card sx={{ p: 3.5 }}>
          <Typography variant="h3" sx={{ mb: 0.5 }}>
            {mode === 'login' ? 'Sign in' : 'Create an account'}
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
            {mode === 'login' ? 'Use the demo account below to see populated data.' : 'A new account starts empty, so you can see the first-run state.'}
          </Typography>

          {error ? <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert> : null}

          <Box
            component="form"
            onSubmit={(event) => { event.preventDefault(); void submit(form.email, form.password, form.fullName); }}
            sx={{ display: 'grid', gap: 2 }}
          >
            {mode === 'register' ? (
              <TextField label="Full name" size="small" required value={form.fullName}
                onChange={(e) => setForm({ ...form, fullName: e.target.value })} />
            ) : null}
            <TextField label="Email" type="email" size="small" required autoComplete="email"
              value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
            <TextField label="Password" type="password" size="small" required
              autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
              helperText={mode === 'register' ? 'At least 8 characters, with letters and numbers.' : undefined}
              value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} />
            <Button type="submit" variant="contained" disabled={busy}>
              {busy ? 'Working…' : mode === 'login' ? 'Sign in' : 'Create account'}
            </Button>
          </Box>

          <Divider sx={{ my: 2.5 }} />

          <Link component="button" variant="body2" onClick={() => { setMode(mode === 'login' ? 'register' : 'login'); setError(null); }}>
            {mode === 'login' ? 'Create an account instead' : 'I already have an account'}
          </Link>
        </Card>

        <Paper variant="outlined" sx={{ mt: 2, p: 2.25, bgcolor: 'action.hover' }}>
          <Typography variant="body2" sx={{ fontWeight: 650, mb: 1 }}>Demo account</Typography>
          <Typography variant="body2" className="mono" color="text.secondary">{DEMO.email}</Typography>
          <Typography variant="body2" className="mono" color="text.secondary" sx={{ mb: 1.5 }}>{DEMO.password}</Typography>
          <Button size="small" variant="outlined" fullWidth disabled={busy}
            onClick={() => { setForm({ ...form, ...DEMO }); void submit(DEMO.email, DEMO.password); }}>
            Sign in with the demo account
          </Button>
        </Paper>

        <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 2, textAlign: 'center' }}>
          Retrace never asks for a UPI PIN, OTP, bank password or card CVV.
        </Typography>
      </Container>
    </Box>
  );
}
