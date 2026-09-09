/** A signer as returned by the API. */
export interface Signer {
  id: string;
  document: string;
  name: string;
  email: string;
  /** Written only from ZapSign data — null until the document is submitted. */
  token: string | null;
  status: string | null;
  external_id: string | null;
}

/** A signer as sent inside a document payload (the document is implied). */
export interface SignerInput {
  name: string;
  email: string;
}
