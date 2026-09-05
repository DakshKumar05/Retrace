import { useState } from 'react';
import { Box, Button, Card, Divider, Typography } from '@mui/material';
import { Download, FileText, Package } from 'lucide-react';
import { useAsync } from '../hooks/useAsync';
import { api, errorMessage } from '../services/api';
import { dateTime } from '../utils/format';
import { EmptyState, ErrorState, LoadingState } from '../components/StateViews';

export function Reports() {
  const { data, loading, error, reload } = useAsync(() => api.reports(), []);
  const incidents = useAsync(() => api.incidents(), []);
  const [busy, setBusy] = useState(false);
  const [failure, setFailure] = useState<string | null>(null);

  const generate = async (incidentId: number) => {
    setBusy(true); setFailure(null);
    try { await api.generateReport(incidentId); reload(); }
    catch (err) { setFailure(errorMessage(err)); }
    finally { setBusy(false); }
  };

  return (
    <Box sx={{ display: 'grid', gap: 2.5 }}>
      <Box>
        <Typography variant="h2">Reports</Typography>
        <Typography color="text.secondary">
          One structured Incident &amp; Evidence Report per case, with every file hashed and indexed.
        </Typography>
      </Box>

      {failure ? <ErrorState message={failure} /> : null}
      {loading ? <LoadingState label="Loading reports" /> : null}
      {error ? <ErrorState message={error} onRetry={reload} /> : null}

      {incidents.data?.length ? (
        <Card sx={{ p: 2.5 }}>
          <Typography variant="h5" sx={{ mb: 1.5 }}>Generate a new report</Typography>
          <Box sx={{ display: 'flex', gap: 1.5, flexWrap: 'wrap' }}>
            {incidents.data.map((incident) => (
              <Button key={incident.id} variant="outlined" size="small" disabled={busy}
                onClick={() => generate(incident.id)}>
                {incident.case_id}
              </Button>
            ))}
          </Box>
        </Card>
      ) : null}

      {data && data.length === 0 ? (
        <EmptyState icon={<FileText size={30} />} title="No reports yet"
          body="Open a case, then generate a report to package the evidence for your bank." />
      ) : null}

      <Box sx={{ display: 'grid', gap: 2 }}>
        {data?.map((report) => (
          <Card key={report.id} sx={{ p: 2.5 }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', gap: 2, flexWrap: 'wrap', alignItems: 'center' }}>
              <Box>
                <Typography variant="h5" className="mono">{report.reference}</Typography>
                <Typography variant="body2" color="text.secondary">
                  Generated {dateTime(report.generated_at)} · {report.evidence_count} file
                  {report.evidence_count === 1 ? '' : 's'} · {report.completeness}% complete
                </Typography>
              </Box>
              <Box sx={{ display: 'flex', gap: 1.5, flexWrap: 'wrap' }}>
                <Button variant="contained" startIcon={<Download size={15} />}
                  onClick={() => api.downloadReportPdf(report)}>
                  Download PDF
                </Button>
                {report.package_filename ? (
                  <Button variant="outlined" startIcon={<Package size={15} />}
                    onClick={() => api.downloadReportPackage(report)}>
                    Evidence package
                  </Button>
                ) : null}
              </Box>
            </Box>
            <Divider sx={{ my: 2 }} />
            <Typography variant="caption" color="text.secondary">
              The package contains the report, every preserved file, and a manifest.json listing the
              SHA-256 of each one.
            </Typography>
          </Card>
        ))}
      </Box>
    </Box>
  );
}
