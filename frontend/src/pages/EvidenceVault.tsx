import { useRef, useState } from 'react';
import {
  Alert, Box, Button, Card, Chip, Divider, MenuItem, Select, Table, TableBody,
  TableCell, TableHead, TableRow, Tooltip, Typography,
} from '@mui/material';
import { Archive, Check, Download, Trash2, Upload } from 'lucide-react';
import { useAsync } from '../hooks/useAsync';
import { api, errorMessage } from '../services/api';
import { bytes, dateTime, shortHash, titleCase } from '../utils/format';
import { EmptyState, ErrorState, LoadingState } from '../components/StateViews';
import { SectionCard } from '../components/SectionCard';
import { EvidenceMeter } from '../components/EvidenceMeter';

const TYPES = [
  { value: 'bank_statement', label: 'Bank statement' },
  { value: 'original_transaction', label: 'Original transaction screenshot' },
  { value: 'refund_transaction', label: 'Refund screenshot' },
  { value: 'payment_receipt', label: 'Payment receipt' },
  { value: 'whatsapp', label: 'WhatsApp conversation' },
  { value: 'sms', label: 'SMS messages' },
  { value: 'call_log', label: 'Call log' },
  { value: 'call_recording', label: 'Call recording' },
  { value: 'bank_complaint', label: 'Bank complaint' },
  { value: 'bank_email', label: 'Bank email' },
  { value: 'complaint_acknowledgement', label: 'Complaint acknowledgement' },
  { value: 'supporting_document', label: 'Other supporting document' },
];

export function EvidenceVault() {
  const input = useRef<HTMLInputElement>(null);
  const [type, setType] = useState('bank_statement');
  const [busy, setBusy] = useState(false);
  const [failure, setFailure] = useState<string | null>(null);
  const [verified, setVerified] = useState<Record<number, boolean>>({});

  const files = useAsync(() => api.evidence(), []);
  const stats = useAsync(() => api.completeness(), []);

  const reloadBoth = () => { files.reload(); stats.reload(); };

  const upload = async (file: File) => {
    setBusy(true); setFailure(null);
    try { await api.uploadEvidence(file, type); reloadBoth(); }
    catch (err) { setFailure(errorMessage(err)); }
    finally { setBusy(false); if (input.current) input.current.value = ''; }
  };

  const verify = async (id: number) => {
    try { const result = await api.verifyEvidence(id); setVerified((prev) => ({ ...prev, [id]: result.unchanged })); }
    catch (err) { setFailure(errorMessage(err)); }
  };

  const uploaded = files.data?.filter((item) => !item.placeholder) ?? [];

  return (
    <Box sx={{ display: 'grid', gap: 2.5 }}>
      <Box>
        <Typography variant="h2">Evidence vault</Typography>
        <Typography color="text.secondary">
          Files are stored exactly as you supply them. Retrace records a SHA-256 fingerprint instead of editing them.
        </Typography>
      </Box>

      <Alert severity="info">
        Upload only what a case actually needs. You can delete any file at any time.
      </Alert>

      {failure ? <ErrorState message={failure} /> : null}

      <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: '1fr 1.9fr' }, gap: 3, alignItems: 'start' }}>
        <Box sx={{ display: 'grid', gap: 3 }}>
          <SectionCard title="Completeness">
            {stats.loading ? <LoadingState label="Checking" /> : null}
            {stats.data ? <EvidenceMeter data={stats.data} /> : null}
          </SectionCard>

          <SectionCard title="Add evidence">
            <Select size="small" fullWidth value={type} onChange={(event) => setType(event.target.value)} sx={{ mb: 1.75 }}>
              {TYPES.map((entry) => <MenuItem key={entry.value} value={entry.value}>{entry.label}</MenuItem>)}
            </Select>
            <input ref={input} type="file" hidden
              accept=".pdf,.png,.jpg,.jpeg,.webp,.txt,.csv,.eml,.mp3,.m4a,.ogg"
              onChange={(event) => { const file = event.target.files?.[0]; if (file) void upload(file); }} />
            <Button fullWidth variant="contained" startIcon={<Upload size={16} />} disabled={busy}
              onClick={() => input.current?.click()}>
              {busy ? 'Uploading…' : 'Choose a file'}
            </Button>
            <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 1.25 }}>
              PDF, images, text, CSV, email or audio. Up to 15 MB.
            </Typography>
          </SectionCard>
        </Box>

        <Card>
          <Box sx={{ px: 2.5, pt: 2.25, pb: 1.5 }}>
            <Typography variant="h5">Preserved files</Typography>
          </Box>
          <Divider />
          {files.loading ? <LoadingState label="Loading the vault" /> : null}
          {files.error ? <Box sx={{ p: 2 }}><ErrorState message={files.error} onRetry={files.reload} /></Box> : null}

          {files.data && uploaded.length === 0 ? (
            <Box sx={{ p: 3 }}>
              <EmptyState icon={<Archive size={30} />} title="The vault is empty"
                body="Add a bank statement or a screenshot to start building the record for a case." />
            </Box>
          ) : null}

          {uploaded.length ? (
            <Box sx={{ overflowX: 'auto' }}>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>#</TableCell>
                    <TableCell>Evidence</TableCell>
                    <TableCell>Uploaded</TableCell>
                    <TableCell>Size</TableCell>
                    <TableCell>SHA-256</TableCell>
                    <TableCell align="right">Actions</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {uploaded.map((item, index) => (
                    <TableRow key={item.id} hover>
                      <TableCell className="mono">{String(index + 1).padStart(2, '0')}</TableCell>
                      <TableCell>
                        <Typography variant="body2" sx={{ fontWeight: 600 }}>{item.label}</Typography>
                        <Box sx={{ display: 'flex', gap: 0.75, alignItems: 'center', mt: 0.25 }}>
                          <Chip size="small" label={titleCase(item.category)} sx={{ height: 18, fontSize: '0.66rem' }} />
                          <Typography variant="caption" color="text.secondary">{item.original_filename}</Typography>
                        </Box>
                      </TableCell>
                      <TableCell sx={{ whiteSpace: 'nowrap' }}>
                        <Typography variant="caption" color="text.secondary">{dateTime(item.uploaded_at)}</Typography>
                      </TableCell>
                      <TableCell className="tabular"><Typography variant="caption">{bytes(item.size_bytes)}</Typography></TableCell>
                      <TableCell>
                        <Tooltip title={item.sha256 ?? ''}>
                          <Typography className="mono" variant="caption">{shortHash(item.sha256)}</Typography>
                        </Tooltip>
                        {verified[item.id] !== undefined ? (
                          <Chip size="small" icon={<Check size={11} />}
                            label={verified[item.id] ? 'Unchanged' : 'Altered'}
                            sx={{ ml: 0.75, height: 18, fontSize: '0.64rem',
                              color: verified[item.id] ? '#0f9d74' : '#c0342b',
                              bgcolor: verified[item.id] ? '#0f9d7414' : '#c0342b14' }} />
                        ) : null}
                      </TableCell>
                      <TableCell align="right" sx={{ whiteSpace: 'nowrap' }}>
                        <Tooltip title="Re-check the fingerprint">
                          <Button size="small" onClick={() => verify(item.id)}>Verify</Button>
                        </Tooltip>
                        <Tooltip title="Download">
                          <Button size="small" onClick={() => api.downloadEvidence(item.id, item.original_filename ?? 'evidence')}>
                            <Download size={14} />
                          </Button>
                        </Tooltip>
                        <Tooltip title="Delete">
                          <Button size="small" color="error"
                            onClick={async () => { await api.deleteEvidence(item.id); reloadBoth(); }}>
                            <Trash2 size={14} />
                          </Button>
                        </Tooltip>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </Box>
          ) : null}
        </Card>
      </Box>
    </Box>
  );
}
