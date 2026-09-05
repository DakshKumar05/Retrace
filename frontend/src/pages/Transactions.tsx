import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box, Card, InputAdornment, Table, TableBody, TableCell, TableHead, TableRow,
  Tab, Tabs, TextField, Typography,
} from '@mui/material';
import { Inbox, Search } from 'lucide-react';
import { useAsync } from '../hooks/useAsync';
import { api } from '../services/api';
import { dateTime, rupees } from '../utils/format';
import { EmptyState, ErrorState, LoadingState } from '../components/StateViews';
import { RiskBadge, StatusChip } from '../components/RiskBadge';

const FILTERS = [
  { key: 'all', label: 'All' },
  { key: 'safe', label: 'Safe' },
  { key: 'suspicious', label: 'Suspicious' },
  { key: 'high_risk', label: 'High risk' },
];

export function Transactions() {
  const navigate = useNavigate();
  const [filter, setFilter] = useState('all');
  const [search, setSearch] = useState('');
  const { data, loading, error, reload } = useAsync(
    () => api.transactions({ filter, search: search || undefined }),
    [filter, search],
  );

  return (
    <Box sx={{ display: 'grid', gap: 2.5 }}>
      <Box>
        <Typography variant="h2">Transactions</Typography>
        <Typography color="text.secondary">Every payment on this account, with the risk the engine assigned.</Typography>
      </Box>

      <Card>
        <Box sx={{ px: 2, pt: 1, display: 'flex', gap: 2, alignItems: 'center', flexWrap: 'wrap', borderBottom: '1px solid', borderColor: 'divider' }}>
          <Tabs value={filter} onChange={(_, value) => setFilter(value)} sx={{ minHeight: 44 }}>
            {FILTERS.map((entry) => <Tab key={entry.key} value={entry.key} label={entry.label} sx={{ minHeight: 44 }} />)}
          </Tabs>
          <Box sx={{ flex: 1 }} />
          <TextField
            size="small" placeholder="Reference or UPI handle" value={search}
            onChange={(event) => setSearch(event.target.value)}
            sx={{ my: 1, minWidth: 240 }}
            InputProps={{ startAdornment: <InputAdornment position="start"><Search size={15} /></InputAdornment> }}
          />
        </Box>

        {loading ? <LoadingState label="Loading transactions" /> : null}
        {error ? <Box sx={{ p: 2 }}><ErrorState message={error} onRetry={reload} /></Box> : null}

        {data && data.length === 0 ? (
          <Box sx={{ p: 3 }}>
            <EmptyState
              icon={<Inbox size={30} />}
              title={search || filter !== 'all' ? 'Nothing matches that' : 'No transactions yet'}
              body={search || filter !== 'all'
                ? 'Try a different filter or clear the search.'
                : 'Run the scam simulation to populate this account with a worked example.'}
            />
          </Box>
        ) : null}

        {data && data.length > 0 ? (
          <Box sx={{ overflowX: 'auto' }}>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Reference</TableCell>
                  <TableCell>Date</TableCell>
                  <TableCell>Counterparty</TableCell>
                  <TableCell align="right">Amount</TableCell>
                  <TableCell>Method</TableCell>
                  <TableCell>Status</TableCell>
                  <TableCell align="right">Risk</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {data.map((tx) => (
                  <TableRow key={tx.id} hover sx={{ cursor: 'pointer' }}
                    onClick={() => navigate(`/app/transactions/${tx.reference}`)}>
                    <TableCell className="mono" sx={{ fontWeight: 600 }}>{tx.reference}</TableCell>
                    <TableCell sx={{ whiteSpace: 'nowrap' }}><Typography variant="body2" color="text.secondary">{dateTime(tx.created_at)}</Typography></TableCell>
                    <TableCell className="mono"><Typography variant="body2">{tx.direction === 'credit' ? tx.sender_handle : tx.receiver_handle}</Typography></TableCell>
                    <TableCell align="right" className="tabular" sx={{ fontWeight: 600, color: tx.direction === 'credit' ? '#0f9d74' : 'inherit', whiteSpace: 'nowrap' }}>
                      {tx.direction === 'credit' ? '+' : '−'}{rupees(tx.amount)}
                    </TableCell>
                    <TableCell><Typography variant="body2" color="text.secondary">{tx.payment_method}</Typography></TableCell>
                    <TableCell><StatusChip status={tx.label} /></TableCell>
                    <TableCell align="right"><RiskBadge score={tx.risk_score} /></TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </Box>
        ) : null}
      </Card>
    </Box>
  );
}
