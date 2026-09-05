import { createTheme } from '@mui/material/styles';
import type { PaletteMode } from '@mui/material';

export const RISK_COLORS: Record<string, string> = {
  LOW: '#0f9d74',
  MEDIUM: '#c77700',
  HIGH: '#d4552c',
  CRITICAL: '#c0342b',
};

// Risk colours stay identical in both modes — they're always drawn as a
// saturated foreground over a low-alpha tint of themselves, so the tint
// already adapts to whatever surface it lands on.
export const riskColor = (level?: string) => RISK_COLORS[level ?? 'LOW'] ?? '#5a6a7d';

export function createAppTheme(mode: PaletteMode) {
  const dark = mode === 'dark';

  return createTheme({
    palette: {
      mode,
      primary: { main: '#1e6fd9', dark: '#155aad', light: dark ? '#173357' : '#e8f0fb' },
      secondary: { main: '#0e1f33' },
      success: { main: '#0f9d74' },
      warning: { main: '#c77700' },
      error: { main: '#c0342b' },
      background: {
        default: dark ? '#0b141f' : '#f4f7fb',
        paper: dark ? '#111c29' : '#ffffff',
      },
      text: {
        primary: dark ? '#e7edf5' : '#16283c',
        secondary: dark ? '#8fa1b8' : '#5a6a7d',
      },
      divider: dark ? 'rgba(255,255,255,0.11)' : '#dde5ef',
    },
    shape: { borderRadius: 10 },
    typography: {
      fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
      h1: { fontSize: '2.9rem', fontWeight: 800, letterSpacing: '-0.03em', lineHeight: 1.08 },
      h2: { fontSize: '1.9rem', fontWeight: 700, letterSpacing: '-0.02em' },
      h3: { fontSize: '1.4rem', fontWeight: 700, letterSpacing: '-0.015em' },
      h4: { fontSize: '1.15rem', fontWeight: 650, letterSpacing: '-0.01em' },
      h5: { fontSize: '1rem', fontWeight: 650 },
      h6: { fontSize: '0.9rem', fontWeight: 650 },
      body2: { fontSize: '0.875rem', lineHeight: 1.55 },
      button: { textTransform: 'none', fontWeight: 600 },
    },
    components: {
      MuiPaper: {
        styleOverrides: {
          root: { backgroundImage: 'none' },
          outlined: ({ theme }) => ({ borderColor: theme.palette.divider }),
        },
      },
      MuiCard: {
        defaultProps: { variant: 'outlined' },
        styleOverrides: { root: ({ theme }) => ({ borderColor: theme.palette.divider }) },
      },
      MuiButton: {
        defaultProps: { disableElevation: true },
        styleOverrides: { root: { borderRadius: 8, paddingInline: 16 } },
      },
      MuiChip: { styleOverrides: { root: { fontWeight: 600 } } },
      MuiTableCell: {
        styleOverrides: {
          root: ({ theme }) => ({ borderColor: theme.palette.divider }),
          head: ({ theme }) => ({ fontWeight: 650, color: theme.palette.text.secondary, fontSize: '0.78rem' }),
        },
      },
      MuiTooltip: { defaultProps: { arrow: true } },
      MuiLinearProgress: { styleOverrides: { root: { borderRadius: 6, height: 8 } } },
    },
  });
}
