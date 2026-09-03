import { DocumentAnalysis } from './analysis.model';
import { Signer } from './signer.model';

/** `GET /api/documents/{id}/report/` (FR-025). */
export interface DocumentReport {
  document_id: string;
  name: string;
  provider_status: string;
  signature_status: string | null;
  signers: Pick<Signer, 'name' | 'email' | 'status'>[];
  latest_analysis: DocumentAnalysis | null;
  created_at: string;
  last_updated_at: string;
}

/** One risk-flagged insight with the document it came from. */
export interface RiskInsight {
  document_id: string;
  name: string;
  text: string;
  created_at: string;
}

/** `GET /api/reports/summary/` (FR-026). */
export interface SummaryReport {
  total_documents: number;
  by_provider_status: Record<string, number>;
  by_signature_status: Record<string, number>;
  documents_with_risk_insight: number;
  recent_risk_insights: RiskInsight[];
  generated_at: string;
}
