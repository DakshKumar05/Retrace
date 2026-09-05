import { IconButton, Tooltip } from '@mui/material';
import { Moon, Sun } from 'lucide-react';
import { useThemeMode } from '../hooks/useThemeMode';

export function ThemeToggle({ dark = false }: { dark?: boolean }) {
  const { mode, toggleMode } = useThemeMode();
  const isDark = mode === 'dark';

  return (
    <Tooltip title={isDark ? 'Switch to light mode' : 'Switch to dark mode'}>
      <IconButton
        onClick={toggleMode}
        aria-label={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
        size="small"
        sx={{
          color: dark ? 'rgba(255,255,255,0.78)' : 'text.secondary',
          '&:hover': dark ? { bgcolor: 'rgba(255,255,255,0.08)', color: '#fff' } : undefined,
        }}
      >
        {isDark ? <Sun size={18} /> : <Moon size={18} />}
      </IconButton>
    </Tooltip>
  );
}
