import { Box, Typography, useTheme } from '@mui/material';
import { riskColor } from '../theme';
import type { RiskLevel } from '../types';

const RECOMMENDATION_COPY: Record<string, string> = {
  SAFE_TO_REFUND: 'Safe to refund',
  VERIFY_BEFORE_REFUND: 'Verify before refunding',
  USE_SAFE_REFUND: 'Use Safe Refund instead',
  DO_NOT_REFUND: 'Do not transfer manually',
  DO_NOT_TRANSFER_MANUALLY: 'Do not transfer manually',
  VERIFY_BEFORE_ACTING: 'Verify before acting',
  NO_ACTION_NEEDED: 'Nothing to act on',
};

export const recommendationCopy = (key: string) =>
  RECOMMENDATION_COPY[key] ?? key.replace(/_/g, ' ').toLowerCase();

/**
 * The product's one bold element: a dial that answers "is it safe to refund?"
 * The arc length is the safety score, the colour is the risk level. Both are
 * shown, because they are opposite scales and conflating them is how people
 * misread a warning.
 */
export function RiskGauge({
  safetyScore,
  riskScore,
  level,
  recommendation,
  size = 236,
}: {
  safetyScore: number;
  riskScore: number;
  level: RiskLevel;
  recommendation?: string;
  size?: number;
}) {
  const stroke = 16;
  const radius = (size - stroke) / 2 - 6;
  const cx = size / 2;
  const cy = size / 2 + 14;
  const start = Math.PI * 0.82;
  const end = Math.PI * 2.18;
  const sweep = end - start;
  const arcLength = radius * sweep;
  const color = riskColor(level);
  const trackColor = useTheme().palette.divider;

  const point = (angle: number) => `${cx + radius * Math.cos(angle)} ${cy + radius * Math.sin(angle)}`;
  const track = `M ${point(start)} A ${radius} ${radius} 0 1 1 ${point(end)}`;
  const filled = Math.max(0.02, Math.min(1, safetyScore / 100));

  return (
    <Box sx={{ width: size, mx: 'auto' }}>
      {/* Fixed to the arc's own height so the round line-cap — which sits right at
          the arc's start or end point at very low or very high safety scores —
          never has a chance to reach content outside this box. */}
      <Box sx={{ position: 'relative', width: size, height: size * 0.86 }}>
        <svg
          width={size}
          height={size * 0.86}
          viewBox={`0 0 ${size} ${size * 0.86}`}
          role="img"
          aria-label={`Refund safety ${safetyScore} out of 100, risk level ${level}`}
        >
          <path d={track} fill="none" stroke={trackColor} strokeWidth={stroke} strokeLinecap="round" />
          <path
            className="rs-arc"
            d={track}
            fill="none"
            stroke={color}
            strokeWidth={stroke}
            strokeLinecap="round"
            strokeDasharray={arcLength}
            strokeDashoffset={arcLength * (1 - filled)}
            style={{ ['--rs-arc-length' as string]: `${arcLength}px` }}
          />
        </svg>

        <Box
          sx={{
            position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column',
            alignItems: 'center', justifyContent: 'center', pt: 1.5, textAlign: 'center',
          }}
        >
          <Typography
            className="tabular"
            sx={{ fontSize: size * 0.24, fontWeight: 800, lineHeight: 1, letterSpacing: '-0.04em', color }}
          >
            {safetyScore}
          </Typography>
          <Typography variant="caption" color="text.secondary" sx={{ mt: 0.25 }}>
            refund safety, out of 100
          </Typography>
          <Typography sx={{ mt: 0.75, fontWeight: 700, fontSize: '0.82rem', letterSpacing: '0.06em', color }}>
            {level} RISK
          </Typography>
          <Typography variant="caption" color="text.secondary" className="tabular">
            risk score {riskScore}
          </Typography>
        </Box>
      </Box>

      {recommendation ? (
        <Typography
          sx={{ mt: 1.5, textAlign: 'center', fontWeight: 650, fontSize: '0.9rem', color }}
        >
          {recommendationCopy(recommendation)}
        </Typography>
      ) : null}
    </Box>
  );
}
