import { useState } from 'react';
import { Link, NavLink, Outlet, useNavigate } from 'react-router-dom';
import {
  AppBar, Box, Button, Chip, Divider, Drawer, IconButton, List, ListItemButton,
  ListItemIcon, ListItemText, Toolbar, Tooltip, Typography, useMediaQuery, useTheme,
} from '@mui/material';
import {
  Activity, AlertTriangle, Archive, ArrowLeftRight, BarChart3, FlaskConical, LayoutDashboard,
  LogOut, Menu as MenuIcon, Play, Shield, ShieldCheck, Share2, FileText,
} from 'lucide-react';
import { useAuth } from '../hooks/useAuth';
import { ThemeToggle } from '../components/ThemeToggle';

const WIDTH = 244;

const MAIN = [
  { to: '/app/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/app/lab', label: 'Scam Lab', icon: FlaskConical },
  { to: '/app/transactions', label: 'Transactions', icon: ArrowLeftRight },
  { to: '/app/refund-safety', label: 'Refund safety', icon: ShieldCheck },
  { to: '/app/safe-mode', label: 'Safe Mode', icon: Shield },
  { to: '/app/evidence', label: 'Evidence vault', icon: Archive },
  { to: '/app/incidents', label: 'Incidents', icon: AlertTriangle },
  { to: '/app/reports', label: 'Reports', icon: FileText },
];

const ADMIN = [
  { to: '/app/admin/risk', label: 'Risk intelligence', icon: BarChart3 },
  { to: '/app/admin/network', label: 'Fraud network', icon: Share2 },
];

function NavList({ onNavigate }: { onNavigate?: () => void }) {
  const { user, signOut } = useAuth();
  const navigate = useNavigate();

  const item = (entry: { to: string; label: string; icon: typeof Shield }) => (
    <ListItemButton
      key={entry.to}
      component={NavLink}
      to={entry.to}
      onClick={onNavigate}
      sx={{
        borderRadius: 1.5, mx: 1, mb: 0.25, py: 0.9, color: 'rgba(255,255,255,0.72)',
        '&:hover': { bgcolor: 'rgba(255,255,255,0.07)', color: '#fff' },
        '&.active': { bgcolor: 'rgba(255,255,255,0.11)', color: '#fff' },
      }}
    >
      <ListItemIcon sx={{ minWidth: 32, color: 'inherit' }}><entry.icon size={17} /></ListItemIcon>
      <ListItemText primaryTypographyProps={{ fontSize: '0.86rem', fontWeight: 550 }} primary={entry.label} />
    </ListItemButton>
  );

  return (
    <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column', bgcolor: '#0e1f33' }}>
      <Box component={Link} to="/" sx={{ px: 2.5, py: 2.5, display: 'flex', gap: 1.25, alignItems: 'center', textDecoration: 'none' }}>
        <ShieldCheck size={22} color="#5fa8ff" />
        <Typography sx={{ color: '#fff', fontWeight: 750, letterSpacing: '-0.02em', fontSize: '1.05rem' }}>
          Retrace
        </Typography>
      </Box>

      <Box sx={{ px: 2, pb: 1.5 }}>
        <Button
          fullWidth
          variant="contained"
          startIcon={<Play size={15} />}
          onClick={() => { onNavigate?.(); navigate('/app/simulate'); }}
          sx={{ bgcolor: '#1e6fd9', '&:hover': { bgcolor: '#2a7ce8' } }}
        >
          Simulate scam
        </Button>
      </Box>

      <List sx={{ py: 0, flex: 1, overflowY: 'auto' }}>
        {MAIN.map(item)}
        {user?.role === 'admin' ? (
          <>
            <Divider sx={{ my: 1.25, mx: 2, borderColor: 'rgba(255,255,255,0.1)' }} />
            <Typography sx={{ px: 3, pb: 0.75, fontSize: '0.68rem', fontWeight: 700, letterSpacing: '0.1em', color: 'rgba(255,255,255,0.38)' }}>
              ADMIN
            </Typography>
            {ADMIN.map(item)}
          </>
        ) : null}
      </List>

      <Box sx={{ p: 2, borderTop: '1px solid rgba(255,255,255,0.08)' }}>
        <Typography sx={{ color: '#fff', fontSize: '0.85rem', fontWeight: 600 }}>{user?.full_name}</Typography>
        <Typography sx={{ color: 'rgba(255,255,255,0.5)', fontSize: '0.75rem' }} className="mono">{user?.upi_id}</Typography>
        <Button
          size="small"
          startIcon={<LogOut size={14} />}
          onClick={() => { signOut(); navigate('/login'); }}
          sx={{ mt: 1, color: 'rgba(255,255,255,0.66)', px: 0 }}
        >
          Sign out
        </Button>
      </Box>
    </Box>
  );
}

export function AppLayout() {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('lg'));
  const [open, setOpen] = useState(false);
  const { user } = useAuth();

  return (
    <Box sx={{ display: 'flex', minHeight: '100vh' }}>
      {isMobile ? (
        <Drawer open={open} onClose={() => setOpen(false)} PaperProps={{ sx: { width: WIDTH, border: 0 } }}>
          <NavList onNavigate={() => setOpen(false)} />
        </Drawer>
      ) : (
        <Box component="nav" sx={{ width: WIDTH, flexShrink: 0 }}>
          <Box sx={{ position: 'fixed', width: WIDTH, height: '100vh' }}><NavList /></Box>
        </Box>
      )}

      <Box sx={{ flex: 1, minWidth: 0 }}>
        <AppBar
          position="sticky" elevation={0} color="inherit"
          sx={{
            borderBottom: '1px solid', borderColor: 'divider',
            bgcolor: (t) => (t.palette.mode === 'dark' ? 'rgba(17,28,41,0.86)' : 'rgba(255,255,255,0.86)'),
            backdropFilter: 'blur(8px)',
          }}
        >
          <Toolbar sx={{ gap: 1.5, minHeight: { xs: 56, md: 62 } }}>
            {isMobile ? (
              <IconButton edge="start" onClick={() => setOpen(true)} aria-label="Open navigation">
                <MenuIcon size={20} />
              </IconButton>
            ) : null}
            <Box sx={{ flex: 1 }} />
            {user?.safe_mode_enabled ? (
              <Chip size="small" icon={<Shield size={14} />} label="Safe Mode on"
                sx={{ color: '#0f9d74', bgcolor: '#0f9d7414', border: '1px solid #0f9d7440' }} />
            ) : null}
            <Tooltip title="Every figure in this build is synthetic. No real money moves.">
              <Chip size="small" icon={<Activity size={13} />} label="Demo data" variant="outlined" />
            </Tooltip>
            <ThemeToggle />
          </Toolbar>
        </AppBar>
        <Box component="main" sx={{ p: { xs: 2, md: 3.5 }, maxWidth: 1360, mx: 'auto' }}>
          <Outlet />
        </Box>
      </Box>
    </Box>
  );
}
