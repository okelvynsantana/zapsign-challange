import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { DocumentAnalysis } from '../models/analysis.model';
import { Paginated } from '../models/api.model';
import {
  Document,
  DocumentCreate,
  DocumentFilters,
  DocumentUpdate,
} from '../models/document.model';
import { HttpService } from './http.service';

/** Typed client for `/api/documents/`. */
@Injectable({ providedIn: 'root' })
export class DocumentService {
  private readonly http = inject(HttpService);

  list(filters: DocumentFilters = {}): Observable<Paginated<Document>> {
    return this.http.get<Paginated<Document>>('/documents/', { ...filters });
  }

  get(id: string): Observable<Document> {
    return this.http.get<Document>(`/documents/${id}/`);
  }

  create(payload: DocumentCreate): Observable<Document> {
    return this.http.post<Document>('/documents/', payload);
  }

  update(id: string, payload: DocumentUpdate): Observable<Document> {
    return this.http.patch<Document>(`/documents/${id}/`, payload);
  }

  remove(id: string): Observable<void> {
    return this.http.delete(`/documents/${id}/`);
  }

  /** Re-submit a failed document, or refresh a submitted one (FR-010). */
  resync(id: string): Observable<Document> {
    return this.http.post<Document>(`/documents/${id}/resync/`, {});
  }

  /** Run a fresh analysis; the previous ones are kept as history (FR-016, FR-017). */
  analyze(id: string): Observable<DocumentAnalysis> {
    return this.http.post<DocumentAnalysis>(`/documents/${id}/analyze/`, {});
  }

  /** The document's analysis history, newest first (FR-018). */
  analyses(id: string): Observable<Paginated<DocumentAnalysis>> {
    return this.http.get<Paginated<DocumentAnalysis>>(`/documents/${id}/analyses/`);
  }
}
