export type RiskLevel = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';

export interface User {
  id: number;
  email: string;
  full_name: string;
  role: 'user' | 'admin';
  upi_id: string;
  balance: number;
  protected_balance: number;
  safe_mode_enabled: boolean;
  safe_mode_activated_at: string | null;
  created_at: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: User;
}

export interface Signal {
  code: string;
  label: string;
  weight: number;
  category: 'RULE' | 'ML' | 'NLP' | 'NETWORK' | string;
  detail: string | null;
}

export interface RiskComponent {
  name: string;
  value: number | null;
  weight: number;
  unit: string;
}

export interface TransactionEvent {
  id: number;
  occurred_at: string;
  kind: string;
  title: string;
  detail: string | null;
  severity: 'info' | 'warning' | 'critical' | string;
}

export interface Transaction {
  id: number;
  reference: string;
  direction: 'credit' | 'debit';
  amount: number;
  currency: string;
  sender_handle: string;
  receiver_handle: string;
  payment_method: string;
  status: string;
  label: 'SAFE' | 'SUSPICIOUS' | 'HIGH_RISK';
  risk_score: number;
  sender_known: boolean;
  sender_account_age_days: number;
  sender_suspicious_history: boolean;
  sender_prior_reports: number;
  refund_requested: boolean;
  note: string | null;
  created_at: string;
}

export interface RiskAssessment {
  id: number;
  subject: string;
  rule_score: number;
  ml_probability: number;
  message_score: number;
  network_score: number;
  risk_score: number;
  safety_score: number;
  risk_level: RiskLevel;
  recommendation: string;
  created_at: string;
  signals: Signal[];
}

export interface TransactionDetail extends Transaction {
  events: TransactionEvent[];
  refund_requests: RefundRequest[];
  latest_assessment: RiskAssessment | null;
}

export interface RefundRequest {
  id: number;
  reference: string;
  transaction_id: number;
  transaction_reference: string | null;
  amount: number;
  original_sender: string;
  refund_destination: string;
  destination_matches_sender: boolean;
  seconds_since_payment: number;
  channel: string;
  message: string | null;
  status: 'PENDING' | 'BLOCKED' | 'SAFE_REFUND_INITIATED' | 'MANUAL_TRANSFER' | 'CANCELLED';
  risk_score: number;
  safety_score: number;
  risk_level: RiskLevel;
  recommendation: string;
  provider_refund_id: string | null;
  provider_status: string | null;
  created_at: string;
}

export interface RefundAnalysis {
  transaction_id: string;
  risk_score: number;
  safety_score: number;
  risk_level: RiskLevel;
  recommendation: string;
  reasons: string[];
  signals: Signal[];
  components: RiskComponent[];
  rule_score: number;
  ml_probability: number | null;
  message_score: number;
  network_score: number;
  ml_disclaimer: string;
  destination_matches_sender: boolean;
  refund_request_id: number | null;
}

export interface MessageAnalysis {
  message_risk_score: number;
  risk_level: RiskLevel;
  recommendation: string;
  signals: Signal[];
  matched_phrases: string[];
  extracted_handles: string[];
  word_count: number;
}

export interface Alert {
  id: number;
  title: string;
  body: string | null;
  severity: string;
  read: boolean;
  created_at: string;
}

export interface Dashboard {
  greeting: string;
  protection_active: boolean;
  safe_mode_enabled: boolean;
  total_transaction_value: number;
  protected_funds: number;
  risk_alerts: number;
  open_incidents: number;
  recent_transactions: Transaction[];
  recent_alerts: Alert[];
  pending_refund_requests: RefundRequest[];
  evidence_completeness: number | null;
}

export interface Evidence {
  id: number;
  incident_id: number | null;
  label: string;
  category: 'FINANCIAL' | 'COMMUNICATION' | 'BANK' | 'OTHER' | string;
  evidence_type: string;
  original_filename: string | null;
  content_type: string | null;
  size_bytes: number;
  sha256: string | null;
  placeholder: boolean;
  description: string | null;
  uploaded_at: string;
}

export interface Completeness {
  percent: number;
  present: string[];
  missing: string[];
  total_files: number;
}

export interface IncidentEvent {
  id: number;
  occurred_at: string;
  source: string;
  title: string;
  detail: string | null;
  severity: string;
}

export interface Incident {
  id: number;
  case_id: string;
  title: string;
  summary: string | null;
  status: 'OPEN' | 'UNDER_REVIEW' | 'REPORT_READY' | 'SUBMITTED' | 'RESOLVED';
  risk_level: RiskLevel;
  risk_score: number;
  potential_loss: number;
  suspect_handle: string | null;
  bank_complaint_ref: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface IncidentDetail extends Incident {
  scam_message: string | null;
  events: IncidentEvent[];
  evidence: Evidence[];
  completeness: Completeness;
  transaction: Transaction | null;
  refund_request: RefundRequest | null;
  connected_transactions: number;
  reports: Report[];
}

export interface Report {
  id: number;
  incident_id: number;
  reference: string;
  pdf_filename: string;
  package_filename: string | null;
  evidence_count: number;
  completeness: number;
  generated_at: string;
}

export interface ProtectionSetting {
  id: number;
  enabled: boolean;
  account_last4: string;
  nickname: string;
  auto_activate_on_critical: boolean;
  protection_active: boolean;
  activated_at: string | null;
}

export interface AdminStatistics {
  total_transactions: number;
  suspicious: number;
  high_risk: number;
  open_incidents: number;
  protected_users: number;
  total_value: number;
  average_payment_to_refund_seconds: number;
  transactions_over_time: { date: string; transactions: number }[];
  risk_distribution: { level: string; count: number }[];
  refund_scam_frequency: { date: string; refund_scams: number }[];
  top_signals: { label: string; category: string; count: number }[];
  network_size: { clusters: number; victims: number; destinations: number; transactions: number };
}

export interface RiskFeedItem {
  timestamp: string;
  reference: string;
  amount: number;
  risk_score: number;
  risk_level: RiskLevel;
  sender_handle: string;
}

export interface GraphNode {
  id: string;
  label: string;
  type: 'sender' | 'victim' | 'transaction' | 'destination' | string;
  suspicious: boolean;
  amount: number | null;
  risk: number | null;
  degree: number;
  is_root: boolean;
  x: number;
  y: number;
}

export interface GraphEdge {
  source: string;
  target: string;
  relation: string;
  amount: number | null;
}

export interface Cluster {
  cluster_key: string;
  suspect_handle: string;
  victim_count: number;
  destination_count: number;
  transaction_count: number;
  risk_score: number;
  graph: { nodes: GraphNode[]; edges: GraphEdge[]; width: number; height: number };
}

export interface SimulationStep {
  step: number;
  title: string;
  detail: string;
  at: string;
}

export interface SimulationResult {
  transaction: Transaction;
  refund_request: RefundRequest;
  analysis: RefundAnalysis;
  steps: SimulationStep[];
  incident: Incident | null;
  completeness: Completeness | null;
  safe_mode_enabled: boolean;
}

export interface PaymentsConfig {
  enabled: boolean;
  mode: string;
  key_id: string | null;
  webhook_configured: boolean;
}

export interface PaymentOrder {
  order_id: string;
  amount: number;
  currency: string;
  key_id: string;
  receipt: string;
}

export interface ScamPreset {
  id: string;
  label: string;
  sender_handle: string;
  refund_destination: string;
  message: string;
}

export interface LabScamResult {
  user: User;
  transaction: Transaction;
  refund_request: RefundRequest;
  analysis: RefundAnalysis;
}

export interface LabResolveResult {
  user: User;
  refund_request: RefundRequest;
  incident: Incident | null;
  events: string[];
  loss: number;
}

export interface LabBatchRow {
  kind: 'scam' | 'borderline' | 'genuine';
  reference: string;
  refund_request_id: number;
  amount: number;
  sender_handle: string;
  refund_destination: string;
  minutes_since_payment: number;
  message: string;
  risk_score: number;
  safety_score: number;
  risk_level: RiskLevel;
  recommendation: string;
  top_reason: string;
}
