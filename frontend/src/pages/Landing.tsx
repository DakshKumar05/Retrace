import { useState } from 'react';
import { Link as RouterLink, useNavigate } from 'react-router-dom';
import { Box, Button, Card, CircularProgress, Container, Typography } from '@mui/material';
import { Archive, ChevronDown, FileText, MessageSquare, Search, ShieldCheck } from 'lucide-react';
import { RiskGauge } from '../components/RiskGauge';
import { useAuth } from '../hooks/useAuth';
import { errorMessage } from '../services/api';
import { DEMO_CREDENTIALS } from '../utils/demo';

const PILLARS = [
  { icon: Search, title: 'Detect', body: 'Spot the refund patterns that give this scam away: the speed, the mismatch, the pressure.' },
  { icon: ShieldCheck, title: 'Protect', body: 'Turn on Safe Mode when risk goes critical, so nothing else leaves in a hurry.' },
  { icon: MessageSquare, title: 'Analyze', body: 'Read the message the way a fraud analyst would, and show which phrases matter.' },
  { icon: Archive, title: 'Document', body: 'Keep statements, screenshots and call logs together with a fingerprint for each file.' },
  { icon: FileText, title: 'Report', body: 'Produce one structured Incident & Evidence Report you can hand to your bank.' },
];

const REASONS = [
  'Refund asked for 4 minutes after the credit',
  'Destination differs from the paying account',
  'Sender account is 6 days old',
  'Message uses urgency to rush the transfer',
];

/** The four-point sparkle that sits inline with the headline.
 *  Sized in em so it tracks the headline through every breakpoint. */
function Sparkle() {
  return (
    <Box
      component="svg"
      viewBox="0 0 100 100"
      aria-hidden
      sx={{
        width: '0.72em', height: '0.72em',
        verticalAlign: 'baseline', position: 'relative', top: '0.03em',
        mr: '0.16em',
        filter: 'drop-shadow(0 0 0.35em rgba(90, 160, 255, 0.7))',
      }}
    >
      <defs>
        <linearGradient id="rs-sparkle" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="#8fc2ff" />
          <stop offset="55%" stopColor="#3d8bf7" />
          <stop offset="100%" stopColor="#6a7dff" />
        </linearGradient>
      </defs>
      <path
        d="M50 2 C53.5 30 70 46.5 98 50 C70 53.5 53.5 70 50 98 C46.5 70 30 53.5 2 50 C30 46.5 46.5 30 50 2 Z"
        fill="url(#rs-sparkle)"
      />
    </Box>
  );
}

export function Landing() {
  const navigate = useNavigate();
  const { signIn } = useAuth();
  const [simulating, setSimulating] = useState(false);
  const [simulateError, setSimulateError] = useState<string | null>(null);

  const runSimulation = async () => {
    setSimulating(true); setSimulateError(null);
    try {
      // Skips the login screen entirely: signs straight into the seeded demo
      // account and drops the visitor into the guided scam, which is the
      // whole point of this button. Falls back to a normal login only if the
      // demo account itself is unreachable.
      await signIn(DEMO_CREDENTIALS.email, DEMO_CREDENTIALS.password);
      navigate('/app/simulate');
    } catch (err) {
      setSimulateError(errorMessage(err));
      setSimulating(false);
    }
  };

  return (
    <Box sx={{ bgcolor: '#fff' }}>
      {/* ---------------------------------------------------------------- hero */}
      <Box
        sx={{
          position: 'relative',
          minHeight: '100vh',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
          bgcolor: '#050d1a',
        }}
      >
        {/* Atmosphere. Two drifting blooms over a fixed gradient field, so the
            background moves like light rather than like a loop. */}
        <Box
          aria-hidden
          sx={{
            position: 'absolute', inset: 0,
            background:
              'radial-gradient(75% 55% at 50% 100%, rgba(4,10,20,0.92) 0%, rgba(4,10,20,0) 62%),'
              + 'linear-gradient(180deg, #08182e 0%, #050f1e 52%, #040913 100%)',
          }}
        />
        <Box
          aria-hidden
          className="rs-drift-a"
          sx={{
            position: 'absolute', inset: '-18%',
            background:
              'radial-gradient(42% 34% at 50% 14%, rgba(51,128,246,0.60) 0%, rgba(51,128,246,0) 70%),'
              + 'radial-gradient(34% 30% at 16% 74%, rgba(38,190,222,0.30) 0%, rgba(38,190,222,0) 72%)',
          }}
        />
        <Box
          aria-hidden
          className="rs-drift-b"
          sx={{
            position: 'absolute', inset: '-18%',
            background:
              'radial-gradient(38% 32% at 84% 68%, rgba(104,116,255,0.38) 0%, rgba(104,116,255,0) 72%),'
              + 'radial-gradient(30% 26% at 68% 10%, rgba(140,190,255,0.26) 0%, rgba(140,190,255,0) 74%)',
          }}
        />

        {/* nav */}
        <Container
          maxWidth="lg"
          sx={{ position: 'relative', py: 2.5, display: 'flex', alignItems: 'center', gap: 1.25 }}
        >
          <ShieldCheck size={21} color="#6aa9ff" />
          <Typography sx={{ fontWeight: 750, letterSpacing: '-0.02em', flex: 1, color: '#fff' }}>
            Retrace
          </Typography>
          <Button
            component={RouterLink}
            to="/login"
            size="small"
            sx={{ color: 'rgba(255,255,255,0.78)', '&:hover': { color: '#fff', bgcolor: 'rgba(255,255,255,0.06)' } }}
          >
            Sign in
          </Button>
        </Container>

        {/* centred statement */}
        <Container
          maxWidth="md"
          sx={{
            position: 'relative', flex: 1,
            display: 'flex', flexDirection: 'column',
            alignItems: 'center', justifyContent: 'center',
            textAlign: 'center', py: { xs: 8, md: 4 },
          }}
        >
          <Box
            sx={{
              display: 'inline-flex', alignItems: 'center', gap: 1,
              px: 1.75, py: 0.5, mb: { xs: 3, md: 4 },
              borderRadius: 999,
              border: '1px solid rgba(255,255,255,0.16)',
              bgcolor: 'rgba(255,255,255,0.04)',
              backdropFilter: 'blur(6px)',
            }}
          >
            <Box sx={{ width: 6, height: 6, borderRadius: '50%', bgcolor: '#4ea3ff' }} />
            <Typography sx={{ fontSize: '0.76rem', fontWeight: 600, color: 'rgba(255,255,255,0.72)', letterSpacing: '0.01em' }}>
              Prototype · synthetic data
            </Typography>
          </Box>

          <Typography
            variant="h1"
            sx={{
              color: '#fff',
              fontSize: 'clamp(2.5rem, 7.2vw, 5rem)',
              fontWeight: 900,
              letterSpacing: '-0.045em',
              lineHeight: 0.98,
              maxWidth: '16ch',
              mb: { xs: 2.5, md: 3 },
            }}
          >
            <Sparkle />
            Don’t let a “wrong payment” become your loss.
          </Typography>

          <Typography
            sx={{
              fontSize: { xs: '1rem', md: '1.12rem' },
              color: 'rgba(255,255,255,0.60)',
              lineHeight: 1.6,
              maxWidth: '52ch',
              mb: { xs: 4, md: 5 },
            }}
          >
            A stranger pays you by “mistake”, then asks you to send it back somewhere new.
            Retrace scores how safe that refund really is — before the money moves.
          </Typography>

          <Box sx={{ display: 'flex', gap: 1.5, flexWrap: 'wrap', justifyContent: 'center' }}>
            <Button
              size="large"
              onClick={() => navigate('/login')}
              sx={{
                px: 4, py: 1.35, borderRadius: 999,
                fontSize: '0.98rem', fontWeight: 650, color: '#fff',
                background: 'linear-gradient(135deg, #4a8ffb 0%, #2f6fe4 52%, #5b6dff 100%)',
                boxShadow: '0 12px 34px rgba(58,124,235,0.42)',
                transition: 'transform 160ms ease, box-shadow 160ms ease',
                '&:hover': {
                  background: 'linear-gradient(135deg, #5b9cff 0%, #3a7bef 52%, #6c7dff 100%)',
                  boxShadow: '0 16px 40px rgba(58,124,235,0.55)',
                  transform: 'translateY(-1px)',
                },
              }}
            >
              Explore the demo
            </Button>
            <Button
              size="large"
              disabled={simulating}
              onClick={() => void runSimulation()}
              startIcon={simulating ? <CircularProgress size={15} sx={{ color: 'inherit' }} /> : undefined}
              sx={{
                px: 3.5, py: 1.35, borderRadius: 999,
                fontSize: '0.98rem', fontWeight: 600,
                color: 'rgba(255,255,255,0.82)',
                border: '1px solid rgba(255,255,255,0.20)',
                '&:hover': { bgcolor: 'rgba(255,255,255,0.07)', borderColor: 'rgba(255,255,255,0.34)', color: '#fff' },
                '&.Mui-disabled': { color: 'rgba(255,255,255,0.5)', borderColor: 'rgba(255,255,255,0.14)' },
              }}
            >
              {simulating ? 'Loading the scam…' : 'Simulate the scam'}
            </Button>
          </Box>

          {simulateError ? (
            <Typography sx={{ mt: 2, fontSize: '0.85rem', color: '#ff8a8a' }}>
              {simulateError} —{' '}
              <Box
                component="span"
                onClick={() => navigate('/login?next=simulate')}
                sx={{ textDecoration: 'underline', cursor: 'pointer' }}
              >
                sign in manually instead
              </Box>
            </Typography>
          ) : null}
        </Container>

        <Box
          sx={{
            position: 'relative', pb: 3.5,
            display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 0.5,
            color: 'rgba(255,255,255,0.34)',
          }}
        >
          <Typography sx={{ fontSize: '0.72rem', letterSpacing: '0.08em', fontWeight: 600 }}>
            SEE IT SCORED
          </Typography>
          <ChevronDown size={16} />
        </Box>
      </Box>

      {/* ------------------------------------------------------- scored example */}
      <Container maxWidth="lg" sx={{ py: { xs: 7, md: 11 } }}>
        <Box
          sx={{
            display: 'grid',
            gridTemplateColumns: { xs: '1fr', md: '0.95fr 1.05fr' },
            gap: { xs: 5, md: 8 },
            alignItems: 'center',
          }}
        >
          <Box>
            <Typography variant="h2" sx={{ mb: 2 }}>
              Every refund gets a number, and the reasons behind it.
            </Typography>
            <Typography sx={{ fontSize: '1.05rem', color: 'text.secondary', lineHeight: 1.65, maxWidth: '54ch' }}>
              No screen shows a bare score. Each contributing signal is listed with its weight, the
              layer that produced it, and the specific detail behind it — so a warning can be checked
              rather than just believed.
            </Typography>
          </Box>

          <Card sx={{ p: { xs: 3, md: 4 }, bgcolor: '#fbfcfe' }}>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
              A real request scored by the engine
            </Typography>
            <RiskGauge safetyScore={6} riskScore={94} level="CRITICAL" recommendation="DO_NOT_REFUND" size={210} />
            <Box sx={{ mt: 4, display: 'grid', gap: 0.75 }}>
              {REASONS.map((reason) => (
                <Typography key={reason} variant="body2" color="text.secondary">— {reason}</Typography>
              ))}
            </Box>
          </Card>
        </Box>
      </Container>

      {/* -------------------------------------------------------------- pillars */}
      <Box sx={{ bgcolor: '#0e1f33', py: { xs: 6, md: 9 } }}>
        <Container maxWidth="lg">
          <Typography variant="h2" sx={{ color: '#fff', mb: 1 }}>The whole lifecycle, not just a score</Typography>
          <Typography sx={{ color: 'rgba(255,255,255,0.6)', mb: 5, maxWidth: '58ch' }}>
            Most tools stop at "this looks fraudulent". The hard part starts after that.
          </Typography>
          <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', sm: '1fr 1fr', lg: 'repeat(5, 1fr)' }, gap: 2 }}>
            {PILLARS.map((pillar) => (
              <Box key={pillar.title} sx={{ p: 2.5, borderRadius: 2, border: '1px solid rgba(255,255,255,0.1)' }}>
                <pillar.icon size={20} color="#5fa8ff" />
                <Typography sx={{ color: '#fff', fontWeight: 700, mt: 1.5, mb: 0.75 }}>{pillar.title}</Typography>
                <Typography variant="body2" sx={{ color: 'rgba(255,255,255,0.62)' }}>{pillar.body}</Typography>
              </Box>
            ))}
          </Box>
        </Container>
      </Box>

      <Container maxWidth="lg" sx={{ py: 5 }}>
        <Typography variant="caption" color="text.secondary">
          Retrace is a prototype built on synthetic data. It never moves real money and never asks
          for a UPI PIN, OTP, bank password or card CVV. The report it generates is a structured evidence
          summary, not an official police report.
        </Typography>
      </Container>
    </Box>
  );
}
