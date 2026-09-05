import { Navigate, Route, Routes } from 'react-router-dom';
import { Box, CircularProgress } from '@mui/material';
import type { ReactNode } from 'react';
import { useAuth } from './hooks/useAuth';
import { AppLayout } from './layouts/AppLayout';
import { Landing } from './pages/Landing';
import { Login } from './pages/Login';
import { Dashboard } from './pages/Dashboard';
import { Transactions } from './pages/Transactions';
import { TransactionDetail } from './pages/TransactionDetail';
import { RefundSafety } from './pages/RefundSafety';
import { SafeMode } from './pages/SafeMode';
import { EvidenceVault } from './pages/EvidenceVault';
import { Incidents } from './pages/Incidents';
import { IncidentDetail } from './pages/IncidentDetail';
import { Reports } from './pages/Reports';
import { ScamLab } from './pages/ScamLab';
import { Simulate } from './pages/Simulate';
import { RiskIntelligence } from './pages/admin/RiskIntelligence';
import { FraudNetwork } from './pages/admin/FraudNetwork';

function Protected({ children, adminOnly }: { children: ReactNode; adminOnly?: boolean }) {
  const { user, ready } = useAuth();
  if (!ready) {
    return (
      <Box sx={{ display: 'grid', placeItems: 'center', minHeight: '100vh' }}>
        <CircularProgress size={28} />
      </Box>
    );
  }
  if (!user) return <Navigate to="/login" replace />;
  if (adminOnly && user.role !== 'admin') return <Navigate to="/app/dashboard" replace />;
  return <>{children}</>;
}

export function App() {
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/login" element={<Login />} />
      <Route path="/app" element={<Protected><AppLayout /></Protected>}>
        <Route index element={<Navigate to="/app/dashboard" replace />} />
        <Route path="dashboard" element={<Dashboard />} />
        <Route path="transactions" element={<Transactions />} />
        <Route path="transactions/:reference" element={<TransactionDetail />} />
        <Route path="refund-safety" element={<RefundSafety />} />
        {/* Message analysis moved into Refund Safety's "Check a message" panel. */}
        <Route path="message-analyzer" element={<Navigate to="/app/refund-safety" replace />} />
        <Route path="safe-mode" element={<SafeMode />} />
        <Route path="evidence" element={<EvidenceVault />} />
        <Route path="incidents" element={<Incidents />} />
        <Route path="incidents/:id" element={<IncidentDetail />} />
        <Route path="reports" element={<Reports />} />
        <Route path="simulate" element={<Simulate />} />
        <Route path="lab" element={<ScamLab />} />
        <Route path="admin/risk" element={<Protected adminOnly><RiskIntelligence /></Protected>} />
        <Route path="admin/network" element={<Protected adminOnly><FraudNetwork /></Protected>} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
