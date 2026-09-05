import { Box, Chip, Divider, LinearProgress, Tooltip, Typography } from '@mui/material';
import { Brain, MessageSquare, Share2, SlidersHorizontal } from 'lucide-react';
import { riskColor } from '../theme';
import type { RiskComponent, Signal } from '../types';

const CATEGORY_META: Record<string, { label: string; icon: typeof Brain; color: string }> = {
  RULE: { label: 'Rule', icon: SlidersHorizontal, color: '#1e6fd9' },
  ML: { label: 'Model', icon: Brain, color: '#7048c4' },
  NLP: { label: 'Message', icon: MessageSquare, color: '#c77700' },
  NETWORK: { label: 'Network', icon: Share2, color: '#0f9d74' },
};

/**
 * Reused everywhere a score is shown. A number on its own is not actionable,
 * so the weights that produced it are always in reach.
 */
export function RiskExplanation({
  signals, components, mlDisclaimer, limit,
}: {
  signals: Signal[];
  components?: RiskComponent[];
  mlDisclaimer?: string;
  limit?: number;
}) {
  const shown = limit ? signals.slice(0, limit) : signals;

  return (
    <Box>
      {components?.length ? (
        <Box sx={{ display: 'grid', gap: 1.25, mb: 2.5 }}>
          {components.map((component) => (
            <Box key={component.name}>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.4 }}>
                <Typography variant="caption" color="text.secondary">
                  {component.name}
                  <Typography component="span" variant="caption" sx={{ ml: 0.75, color: 'text.disabled' }}>
                    {Math.round(component.weight * 100)}% of the blend
                  </Typography>
                </Typography>
                <Typography variant="caption" className="tabular" sx={{ fontWeight: 650 }}>
                  {component.value === null ? 'not used' : component.unit === 'probability' ? `${component.value}%` : component.value}
                </Typography>
              </Box>
              <LinearProgress
                variant="determinate"
                value={component.value ?? 0}
                sx={{ height: 6, bgcolor: 'divider', '& .MuiLinearProgress-bar': { bgcolor: riskColor(component.value && component.value > 80 ? 'CRITICAL' : component.value && component.value > 60 ? 'HIGH' : component.value && component.value > 30 ? 'MEDIUM' : 'LOW') } }}
              />
            </Box>
          ))}
          <Divider sx={{ mt: 1 }} />
        </Box>
      ) : null}

      <Typography variant="body2" sx={{ fontWeight: 650, mb: 1.25 }}>Why this was flagged</Typography>

      <Box sx={{ display: 'grid', gap: 1 }}>
        {shown.map((signal) => {
          const meta = CATEGORY_META[signal.category] ?? CATEGORY_META.RULE;
          const positive = signal.weight >= 0;
          return (
            <Box key={`${signal.code}-${signal.label}`} sx={{ display: 'flex', gap: 1.5, alignItems: 'flex-start' }}>
              <Typography
                className="mono tabular"
                sx={{
                  minWidth: 34, textAlign: 'right', fontSize: '0.82rem', fontWeight: 600, pt: '1px',
                  color: positive ? '#c0342b' : '#0f9d74',
                }}
              >
                {positive ? '+' : ''}{signal.weight}
              </Typography>
              <Box sx={{ minWidth: 0 }}>
                <Box sx={{ display: 'flex', gap: 0.75, alignItems: 'center', flexWrap: 'wrap' }}>
                  <Typography variant="body2" sx={{ fontWeight: 550 }}>{signal.label}</Typography>
                  <Tooltip title={`Detected by the ${meta.label.toLowerCase()} layer`}>
                    <Chip size="small" icon={<meta.icon size={11} />} label={meta.label}
                      sx={{ height: 19, fontSize: '0.66rem', color: meta.color, bgcolor: `${meta.color}12`, border: `1px solid ${meta.color}30` }} />
                  </Tooltip>
                </Box>
                {signal.detail ? (
                  <Typography variant="caption" color="text.secondary" sx={{ display: 'block', lineHeight: 1.45 }}>
                    {signal.detail}
                  </Typography>
                ) : null}
              </Box>
            </Box>
          );
        })}
      </Box>

      {mlDisclaimer ? (
        <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 2, fontStyle: 'italic' }}>
          {mlDisclaimer} A score indicates a pattern worth checking, not proof of fraud.
        </Typography>
      ) : null}
    </Box>
  );
}
