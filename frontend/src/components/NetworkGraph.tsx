import { useState } from 'react';
import { Box, Chip, Paper, Typography, useTheme } from '@mui/material';
import type { Cluster, GraphNode } from '../types';
import { rupees } from '../utils/format';

const NODE_STYLE: Record<string, { fill: string; r: number; label: string }> = {
  sender: { fill: '#c0342b', r: 15, label: 'Paying account' },
  victim: { fill: '#1e6fd9', r: 11, label: 'Account paid' },
  transaction: { fill: '#8ea3bb', r: 7, label: 'Payment' },
  destination: { fill: '#c77700', r: 12, label: 'Refund destination' },
};

/** Layout arrives pre-computed from NetworkX on the server, so this is a plain
 *  SVG render with no client-side graph library. */
export function NetworkGraph({ cluster }: { cluster: Cluster }) {
  const theme = useTheme();
  const [selected, setSelected] = useState<GraphNode | null>(null);
  const { nodes, edges, width, height } = cluster.graph;
  const byId = new Map(nodes.map((node) => [node.id, node]));
  // The node ring punches through to whatever's behind it, so it should match
  // the surface it's drawn on rather than assume that surface is always white.
  const nodeRing = theme.palette.background.paper;
  const labelColor = theme.palette.text.secondary;
  const edgeColor = theme.palette.mode === 'dark' ? 'rgba(255,255,255,0.22)' : '#c2d0e0';

  return (
    <Box>
      <Box sx={{ overflowX: 'auto', border: '1px solid', borderColor: 'divider', borderRadius: 2, bgcolor: 'action.hover' }}>
        <svg viewBox={`0 0 ${width} ${height}`} width="100%" height={Math.min(height, 520)} role="img" aria-label="Fraud network graph">
          {edges.map((edge, index) => {
            const from = byId.get(edge.source);
            const to = byId.get(edge.target);
            if (!from || !to) return null;
            const dashed = edge.relation === 'connected_to';
            return (
              <line
                key={`${edge.source}-${edge.target}-${index}`}
                x1={from.x} y1={from.y} x2={to.x} y2={to.y}
                stroke={dashed ? '#c0342b' : edgeColor}
                strokeWidth={dashed ? 1.6 : 1.2}
                strokeDasharray={dashed ? '5 4' : undefined}
              />
            );
          })}
          {nodes.map((node) => {
            const style = NODE_STYLE[node.type] ?? NODE_STYLE.transaction;
            const active = selected?.id === node.id;
            return (
              <g key={node.id} onClick={() => setSelected(node)} style={{ cursor: 'pointer' }}>
                <circle
                  cx={node.x} cy={node.y} r={style.r + (active ? 4 : 0)}
                  fill={style.fill} fillOpacity={active ? 1 : 0.88}
                  stroke={nodeRing} strokeWidth={active ? 3 : 2}
                />
                <text x={node.x} y={node.y + style.r + 13} textAnchor="middle" fontSize="10.5" fill={labelColor}>
                  {node.label.length > 20 ? `${node.label.slice(0, 19)}…` : node.label}
                </text>
              </g>
            );
          })}
        </svg>
      </Box>

      <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', mt: 1.5 }}>
        {Object.entries(NODE_STYLE).map(([key, style]) => (
          <Chip
            key={key} size="small" label={style.label}
            sx={{ bgcolor: `${style.fill}14`, color: style.fill, border: `1px solid ${style.fill}33` }}
          />
        ))}
      </Box>

      {selected ? (
        <Paper variant="outlined" sx={{ mt: 2, p: 2 }}>
          <Typography variant="body2" color="text.secondary">
            {NODE_STYLE[selected.type]?.label ?? 'Node'}
          </Typography>
          <Typography className="mono" sx={{ fontWeight: 600 }}>{selected.label}</Typography>
          <Box sx={{ display: 'flex', gap: 2.5, mt: 1, flexWrap: 'wrap' }}>
            <Typography variant="caption" color="text.secondary">Connections: {selected.degree}</Typography>
            {selected.amount ? (
              <Typography variant="caption" color="text.secondary">Amount: {rupees(selected.amount)}</Typography>
            ) : null}
            {selected.risk !== null && selected.risk !== undefined ? (
              <Typography variant="caption" color="text.secondary">Risk: {selected.risk}</Typography>
            ) : null}
            {selected.suspicious ? (
              <Typography variant="caption" sx={{ color: '#c0342b', fontWeight: 600 }}>Flagged in earlier activity</Typography>
            ) : null}
          </Box>
        </Paper>
      ) : (
        <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 1.5 }}>
          Select a node to see what it is connected to.
        </Typography>
      )}
    </Box>
  );
}
