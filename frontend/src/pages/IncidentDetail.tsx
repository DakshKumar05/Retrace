import { useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import {
  Alert, Box, Button, Divider, MenuItem, Select, Step, StepLabel, Stepper, TextField, Typography,
} from '@mui/material';
import { ArrowLeft, FileText } from 'lucide-react';
import { useAsync } from '../hooks/useAsync';
import { api, errorMessage } from '../services/api';
import { dateTime, rupees } from '../utils/format';
import { ErrorState, LoadingState } from '../components/StateViews';
import { RiskBadge, StatusChip } from '../components/RiskBadge';
import { SectionCard, StatCard } from '../components/SectionCard';
import { BehaviorTimeline } from '../components/BehaviorTimeline';
import { EvidenceMeter } from '../components/EvidenceMeter';

const STAGES = ['OPEN', 'UNDER_REVIEW', 'REPORT_READY', 'SUBMITTED', 'RESOLVED'];

export function IncidentDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { data, loading, error, reload } = useAsync(() => api.incident(Number(id)), [id]);
  const [busy, setBusy] = useState(false);
  const [failure, setFailure] = useState<string | null>(null);
  const [notes, setNotes] = useState<string | null>(null);
  const [complaint, setComplaint] = useState<string | null>(null);

  if (loading) return <LoadingState label="Loading the case" />;
  if (error) return <ErrorState message={error} onRetry={reload} />;
  if (!data) return null;

  const save = async (body: object) => {
    setBusy(true); setFailure(null);
    try { await api.updateIncident(data.id, body); reload(); }
    catch (err) { setFailure(errorMessage(err)); }
    finally { setBusy(false); }
  };

  const generate = async () => {
    setBusy(true); setFailure(null);
    try { const report = await api.generateReport(data.id); await api.downloadReportPdf(report); reload(); }
    catch (err) { setFailure(errorMessage(err)); }
    finally { setBusy(false); }
  };

  return (
    <Box sx={{ display: 'grid', gap: 2.5 }}>
      <Button startIcon={<ArrowLeft size={16} />} onClick={() => navigate('/app/incidents')} sx={{ justifySelf: 'start', px: 0 }}>
        All incidents
      </Button>

      <Box sx={{ display: 'flex', justifyContent: 'space-between', gap: 2, flexWrap: 'wrap', alignItems: 'flex-start' }}>
        <Box>
          <Typography variant="h2" className="mono">{data.case_id}</Typography>
          <Typography color="text.secondary">Opened {dateTime(data.created_at)}</Typography>
        </Box>
        <Box sx={{ display: 'flex', gap: 1.5, alignItems: 'center', flexWrap: 'wrap' }}>
          <RiskBadge level={data.risk_level} score={data.risk_score} size="medium" />
          <Select size="small" value={data.status} disabled={busy}
            onChange={(event) => save({ status: event.target.value })}>
            {STAGES.map((stage) => (
              <MenuItem key={stage} value={stage}>{stage.replace(/_/g, ' ').toLowerCase().replace(/^./, (c) => c.toUpperCase())}</MenuItem>
            ))}
          </Select>
          <Button variant="contained" startIcon={<FileText size={16} />} disabled={busy} onClick={generate}>
            Generate report
          </Button>
        </Box>
      </Box>

      {failure ? <ErrorState message={failure} /> : null}

      <Box sx={{ overflowX: 'auto', pb: 1 }}>
        <Stepper activeStep={STAGES.indexOf(data.status)} alternativeLabel sx={{ minWidth: 620 }}>
          {STAGES.map((stage) => (
            <Step key={stage}>
              <StepLabel>{stage.replace(/_/g, ' ').toLowerCase().replace(/^./, (c) => c.toUpperCase())}</StepLabel>
            </Step>
          ))}
        </Stepper>
      </Box>

      <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr 1fr', md: 'repeat(4, 1fr)' }, gap: 2 }}>
        <StatCard label="Potential loss" value={rupees(data.potential_loss)} tone="#c0342b" />
        <StatCard label="Suspect handle" value={data.suspect_handle ?? '—'} />
        <StatCard label="Connected transactions" value={String(data.connected_transactions)} />
        <StatCard label="Evidence files" value={String(data.completeness.total_files)} />
      </Box>

      <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', lg: '1.5fr 1fr' }, gap: 3, alignItems: 'start' }}>
        <Box sx={{ display: 'grid', gap: 3 }}>
          <SectionCard title="What happened">
            <Typography variant="body2" sx={{ mb: 2 }}>{data.summary}</Typography>
            {data.scam_message ? (
              <Box sx={{ p: 2, bgcolor: 'action.hover', borderRadius: 1.5, borderLeft: '3px solid #c0342b' }}>
                <Typography variant="caption" color="text.secondary">Message received</Typography>
                <Typography variant="body2" sx={{ fontStyle: 'italic' }}>"{data.scam_message}"</Typography>
              </Box>
            ) : null}
          </SectionCard>

          <SectionCard title="Incident timeline" subtitle="Transaction, refund, message and system events in one sequence.">
            {data.events.length ? <BehaviorTimeline items={data.events} showDate /> : (
              <Typography variant="body2" color="text.secondary">No events recorded.</Typography>
            )}
          </SectionCard>
        </Box>

        <Box sx={{ display: 'grid', gap: 3 }}>
          <SectionCard title="Evidence">
            <EvidenceMeter data={data.completeness} />
            <Button size="small" sx={{ mt: 2, px: 0 }} onClick={() => navigate('/app/evidence')}>Open the vault</Button>
          </SectionCard>

          <SectionCard title="Case notes">
            <TextField
              size="small" fullWidth label="Bank complaint reference"
              value={complaint ?? data.bank_complaint_ref ?? ''}
              onChange={(event) => setComplaint(event.target.value)}
              sx={{ mb: 2 }}
            />
            <TextField
              size="small" fullWidth multiline minRows={4} label="Notes"
              value={notes ?? data.notes ?? ''}
              onChange={(event) => setNotes(event.target.value)}
            />
            <Button
              size="small" variant="outlined" sx={{ mt: 1.75 }} disabled={busy}
              onClick={() => save({ notes: notes ?? data.notes, bank_complaint_ref: complaint ?? data.bank_complaint_ref })}
            >
              Save
            </Button>
          </SectionCard>

          <Alert severity="info">
            The report is a structured evidence summary. It is not an official police report or a
            determination of fraud.
          </Alert>
        </Box>
      </Box>
    </Box>
  );
}
