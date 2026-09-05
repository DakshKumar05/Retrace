import axios, { AxiosError } from 'axios';
import type {
  AdminStatistics, Alert, AuthResponse, Cluster, Completeness, Dashboard, Evidence,
  Incident, IncidentDetail, MessageAnalysis, PaymentOrder, PaymentsConfig, ProtectionSetting,
  RefundAnalysis, RefundRequest, Report, RiskFeedItem, LabBatchRow, LabResolveResult, LabScamResult,
  ScamPreset, SimulationResult, Transaction, TransactionDetail, User,
} from '../types';

const TOKEN_KEY = 'retrace.token';

export const tokenStore = {
  get: () => localStorage.getItem(TOKEN_KEY),
  set: (token: string) => localStorage.setItem(TOKEN_KEY, token),
  clear: () => localStorage.removeItem(TOKEN_KEY),
};

export const http = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '',
  headers: { 'Content-Type': 'application/json' },
});

http.interceptors.request.use((config) => {
  const token = tokenStore.get();
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

http.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (error.response?.status === 401 && !window.location.pathname.startsWith('/login')) {
      tokenStore.clear();
      window.location.assign('/login');
    }
    return Promise.reject(error);
  },
);

/** Turn any axios failure into a sentence worth showing a person.
 *  "Request failed with status code 500" tells someone nothing they can act on. */
export const errorMessage = (error: unknown): string => {
  const err = error as AxiosError<{ detail?: string }>;
  if (err?.response?.data?.detail) return err.response.data.detail;
  if (err?.code === 'ERR_NETWORK') return 'Cannot reach the Retrace API. Is the backend running on port 8000?';

  switch (err?.response?.status) {
    case 400:
    case 422:
      return 'Some of the details are missing or not valid. Fill in every required field and try again.';
    case 401:
      return 'Your session has expired. Sign in again to continue.';
    case 403:
      return 'This account does not have access to that.';
    case 404:
      return 'That record no longer exists. Refresh and try again.';
    case 409:
      return 'That has already been done, so it cannot be repeated.';
    case 500:
      return 'Something went wrong on the server while handling that. Nothing was saved — try again.';
    case 502:
    case 503:
      return 'The service is not reachable right now. Try again in a moment.';
    default:
      return err?.message || 'Something went wrong.';
  }
};

const get = async <T>(url: string, params?: object): Promise<T> =>
  (await http.get<T>(url, { params })).data;
const post = async <T>(url: string, body?: object): Promise<T> => (await http.post<T>(url, body)).data;
const patch = async <T>(url: string, body?: object): Promise<T> => (await http.patch<T>(url, body)).data;

/** Fetch a protected file and hand it to the browser as a download. */
const download = async (url: string, filename: string) => {
  const response = await http.get(url, { responseType: 'blob' });
  const href = URL.createObjectURL(response.data as Blob);
  const anchor = document.createElement('a');
  anchor.href = href;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(href);
};

export const api = {
  health: () => get<{ status: string; refund_mode: string; version: string }>('/api/health'),
  privacy: () => get<{ summary: string; points: string[]; report_disclaimer: string }>('/api/privacy'),

  login: (email: string, password: string) => post<AuthResponse>('/api/auth/login', { email, password }),
  register: (email: string, full_name: string, password: string) =>
    post<AuthResponse>('/api/auth/register', { email, full_name, password }),
  me: () => get<User>('/api/auth/me'),
  createLabAccount: (body: {
    full_name: string; upi_handle?: string; opening_balance: number; as_admin: boolean;
  }) => post<AuthResponse & { password: string }>('/api/lab/account', body),

  dashboard: () => get<Dashboard>('/api/dashboard'),
  transactions: (params: { filter?: string; search?: string }) =>
    get<Transaction[]>('/api/transactions', params),
  transaction: (reference: string) => get<TransactionDetail>(`/api/transactions/${reference}`),

  analyzeRefund: (body: {
    transaction_id: string; refund_amount: number; original_sender: string;
    refund_destination: string; time_since_payment: number; message?: string | null; persist?: boolean;
  }) => post<RefundAnalysis>('/api/risk/analyze-refund', body),
  analyzeMessage: (message: string) => post<MessageAnalysis>('/api/risk/analyze-message', { message }),
  modelInfo: () => get<Record<string, unknown>>('/api/risk/model-info'),

  refunds: () => get<RefundRequest[]>('/api/refunds'),
  safeRefund: (refund_request_id: number) =>
    post<{ refund_id: string; status: string; amount: number; destination: string; mode: string; message: string }>(
      '/api/refunds/safe', { refund_request_id },
    ),
  manualRefund: (refund_request_id: number) =>
    post<RefundRequest>('/api/refunds/manual', { refund_request_id, confirm: true }),
  cancelRefund: (id: number) => post<RefundRequest>(`/api/refunds/${id}/cancel`),

  alerts: () => get<Alert[]>('/api/alerts'),
  setSafeMode: (enabled: boolean, reason?: string) => post<User>('/api/safe-mode', { enabled, reason }),

  protection: () => get<ProtectionSetting>('/api/protection'),
  updateProtection: (body: Partial<ProtectionSetting>) => patch<ProtectionSetting>('/api/protection', body),
  activateProtection: (amount?: number) => post<ProtectionSetting>('/api/protection/activate', { amount }),
  releaseProtection: () => post<ProtectionSetting>('/api/protection/release'),

  evidence: (incident_id?: number) => get<Evidence[]>('/api/evidence', incident_id ? { incident_id } : undefined),
  evidenceCategories: () => get<{ categories: Record<string, string[]> }>('/api/evidence/categories'),
  completeness: (incident_id?: number) =>
    get<Completeness>('/api/evidence/completeness', incident_id ? { incident_id } : undefined),
  uploadEvidence: async (file: File, evidence_type: string, incident_id?: number, description?: string) => {
    const form = new FormData();
    form.append('file', file);
    form.append('evidence_type', evidence_type);
    if (incident_id) form.append('incident_id', String(incident_id));
    if (description) form.append('description', description);
    const { data } = await http.post<Evidence>('/api/evidence/upload', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return data;
  },
  verifyEvidence: (id: number) => get<{ evidence_id: number; sha256: string; unchanged: boolean }>(`/api/evidence/${id}/verify`),
  downloadEvidence: (id: number, filename: string) => download(`/api/evidence/${id}/download`, filename),
  deleteEvidence: async (id: number) => { await http.delete(`/api/evidence/${id}`); },

  incidents: () => get<Incident[]>('/api/incidents'),
  incident: (id: number) => get<IncidentDetail>(`/api/incidents/${id}`),
  updateIncident: (id: number, body: object) => patch<IncidentDetail>(`/api/incidents/${id}`, body),

  reports: () => get<Report[]>('/api/reports'),
  generateReport: (incident_id: number) =>
    post<Report>('/api/reports/generate', { incident_id, include_package: true }),
  downloadReportPdf: (report: Report) => download(`/api/reports/${report.id}/pdf`, report.pdf_filename),
  downloadReportPackage: (report: Report) =>
    download(`/api/reports/${report.id}/package`, report.package_filename ?? 'evidence-package.zip'),

  adminStatistics: () => get<AdminStatistics>('/api/admin/statistics'),
  riskFeed: () => get<RiskFeedItem[]>('/api/admin/risk-feed'),
  fraudNetwork: () => get<{ clusters: Cluster[]; totals: Record<string, number>; note: string }>('/api/admin/fraud-network'),

  paymentsConfig: () => get<PaymentsConfig>('/api/payments/config'),
  createPaymentOrder: (amount: number, sender_handle: string) =>
    post<PaymentOrder>('/api/payments/order', { amount, sender_handle }),
  verifyPayment: (body: {
    razorpay_order_id: string; razorpay_payment_id: string;
    razorpay_signature: string; sender_handle: string;
  }) => post<{ verified: boolean; transaction: Transaction; message: string }>('/api/payments/verify', body),

  scamPresets: () => get<ScamPreset[]>('/api/lab/scam-presets'),
  labFunds: (body: { amount: number; from_handle: string; note?: string }) =>
    post<{ user: User; transaction: Transaction }>('/api/lab/funds', body),
  labScam: (body: {
    amount: number; sender_handle: string; refund_destination: string;
    message: string; minutes_since_payment: number;
  }) => post<LabScamResult>('/api/lab/scam', body),
  labResolve: (refund_request_id: number, action: 'safe' | 'manual') =>
    post<LabResolveResult>('/api/lab/resolve', { refund_request_id, action }),
  labBatch: (count: number) =>
    post<{ user: User; rows: LabBatchRow[] }>('/api/lab/batch', { count }),

  simulate: (unsafe: boolean) => post<SimulationResult>('/api/simulation/scam', { unsafe }),
  resetDemo: () => post<{ status: string; message: string }>('/api/simulation/reset'),
};
