/** Organization profile as returned by `/api/companies/` (contracts/rest-api.md). */
export interface Company {
  id: string;
  name: string;
  /** Only the masked form is ever sent back — the raw token is write-only (FR-002). */
  api_token_masked: string;
  created_at: string;
  last_updated_at: string;
}

/** Payload for creating a company: the credential is required here. */
export interface CompanyCreate {
  name: string;
  api_token: string;
}

/** Payload for updating: omit `api_token` to keep the stored credential. */
export interface CompanyUpdate {
  name?: string;
  api_token?: string;
}
