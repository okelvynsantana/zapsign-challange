import { DocumentAnalysis } from './analysis.model';
import { Signer } from './signer.model';

/** Our ZapSign hand-off lifecycle (backend `ProviderStatus`). */
export type ProviderStatus = 'pending_integration' | 'submitted' | 'failed';

/** A document as returned by `/api/documents/`. */
export interface Document {
  id: string;
  company: string;
  name: string;
  pdf_url: string;
  external_id: string | null;
  provider_status: ProviderStatus;
  /** Signature status as reported by ZapSign; null until it says otherwise. */
  status: string | null;
  open_id: number | null;
  token: string | null;
  created_by: string;
  last_provider_error: string | null;
  signers: Signer[];
  /** The newest analysis, or `null` before the first run (FR-018). */
  latest_analysis: DocumentAnalysis | null;
  created_at: string;
  last_updated_at: string;
}

export interface DocumentCreate {
  company: string;
  name: string;
  pdf_url: string;
  external_id?: string;
  signers: { name: string; email: string }[];
}

export interface DocumentUpdate {
  name?: string;
  pdf_url?: string;
  external_id?: string;
  signers?: { name: string; email: string }[];
}

/** Filters accepted by the document list endpoint. */
export interface DocumentFilters {
  provider_status?: ProviderStatus;
  status?: string;
  company?: string;
  /** 1-based; the list endpoint paginates and the SPA walks it (FR-016). */
  page?: number;
}
