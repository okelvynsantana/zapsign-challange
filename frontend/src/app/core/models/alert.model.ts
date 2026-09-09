/** A dashboard alert: derived per request, never a stored record (bonus US5). */
export interface Alert {
  type: 'stalled' | 'risk';
  document_id: string;
  document_name: string;
  detail: string;
  since: string;
}
