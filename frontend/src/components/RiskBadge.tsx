import { Chip } from '@mui/material';
import { riskColor } from '../theme';
import type { RiskLevel } from '../types';

export const levelFor = (score: number): RiskLevel =>
  score <= 30 ? 'LOW' : score <= 60 ? 'MEDIUM' : score <= 80 ? 'HIGH' : 'CRITICAL';

export function RiskBadge({
  level, score, size = 'small',
}: { level?: RiskLevel; score?: number; size?: 'small' | 'medium' }) {
  const resolved = level ?? levelFor(score ?? 0);
  const color = riskColor(resolved);
  return (
    <Chip
      size={size}
      label={score === undefined ? resolved : `${resolved} · ${score}`}
      sx={{
        color,
        bgcolor: `${color}14`,
        border: `1px solid ${color}40`,
        letterSpacing: '0.02em',
        fontSize: size === 'small' ? '0.72rem' : '0.8rem',
      }}
    />
  );
}

const STATUS_TONE: Record<string, string> = {
  SAFE: '#0f9d74', SUSPICIOUS: '#c77700', HIGH_RISK: '#c0342b',
  PENDING: '#5a6a7d', BLOCKED: '#c0342b', SAFE_REFUND_INITIATED: '#0f9d74',
  MANUAL_TRANSFER: '#c0342b', CANCELLED: '#5a6a7d',
  OPEN: '#c0342b', UNDER_REVIEW: '#c77700', REPORT_READY: '#1e6fd9',
  SUBMITTED: '#155aad', RESOLVED: '#0f9d74',
};

export function StatusChip({ status }: { status: string }) {
  const color = STATUS_TONE[status] ?? '#5a6a7d';
  return (
    <Chip
      size="small"
      label={status.replace(/_/g, ' ').toLowerCase().replace(/^./, (c) => c.toUpperCase())}
      sx={{ color, bgcolor: `${color}14`, border: `1px solid ${color}33` }}
    />
  );
}
