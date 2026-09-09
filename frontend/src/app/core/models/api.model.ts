/** Shapes shared by every endpoint (contracts/rest-api.md "Conventions"). */

/** Standard error body: `fields` is present only on 400 validation errors. */
export interface ApiError {
  detail: string;
  code: string;
  fields?: Record<string, string[]>;
}

/** Envelope returned by every list endpoint. */
export interface Paginated<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}
