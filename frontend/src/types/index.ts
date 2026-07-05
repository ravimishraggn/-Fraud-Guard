export interface User {
  id: string;
  tenant_id: string;
  email: string;
  full_name: string;
  role: string;
  is_active: boolean;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export type DocumentStatus =
  | "UPLOADED"
  | "PROCESSING"
  | "EXTRACTED"
  | "REVIEW_REQUIRED"
  | "APPROVED"
  | "REJECTED"
  | "FAILED";

export type RiskLevel = "unknown" | "clean" | "low" | "medium" | "high";

export interface Document {
  id: string;
  original_filename: string | null;
  mime_type: string | null;
  file_size_bytes: number | null;
  status: DocumentStatus;
  doc_type: string | null;
  overall_risk_score: number;
  risk_level: RiskLevel;
  review_decision: string | null;
  review_note: string | null;
  processing_ms: number | null;
  created_at: string;
}

export interface DocumentList {
  items: Document[];
  total: number;
  page: number;
  page_size: number;
}

export interface ExtractedField {
  id: string;
  document_id: string;
  field_name: string;
  raw_value: string | null;
  normalised_value: string | null;
  confidence: number | null;
  source: string | null;
  is_verified: boolean;
}

export type Severity = "low" | "medium" | "high" | "critical";

export interface FraudFlag {
  id: string;
  document_id: string;
  flag_type: string;
  severity: Severity;
  title: string;
  description: string;
  evidence: Record<string, unknown>;
  confidence: number | null;
  created_at: string;
}

export interface Vendor {
  id: string;
  name: string;
  gstin: string | null;
  pan: string | null;
  bank_account: string | null;
  is_whitelisted: boolean;
  risk_score: number;
  total_invoices: number;
  total_amount_paise: number;
  flagged_count: number;
  notes: string | null;
}

export interface FraudRule {
  id: string;
  rule_name: string;
  rule_type: string;
  is_active: boolean;
  config: Record<string, unknown>;
  created_at: string;
}

export interface AnalyticsSummary {
  documents_this_month: number;
  documents_total: number;
  fraud_flags_raised: number;
  money_saved_paise: number;
  automation_rate: number;
  pending_review: number;
}

export interface TrendPoint {
  date: string;
  count: number;
}
