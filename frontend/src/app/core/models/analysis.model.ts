/** One insight from an analysis run; `risk` drives the alerts view. */
export interface Insight {
  text: string;
  risk: boolean;
}

/** How an analysis was produced (FR-021). */
export type AnalysisSource = 'llm' | 'regex' | 'llm+regex';

/** One analysis run. Runs are append-only — a retry creates a new one (FR-017). */
export interface DocumentAnalysis {
  id: string;
  state: 'succeeded' | 'failed';
  summary: string;
  missing_topics: string[];
  insights: Insight[];
  source: AnalysisSource;
  model: string | null;
  /** Populated only when `state` is `failed`. */
  error_reason: string | null;
  created_at: string;
}
