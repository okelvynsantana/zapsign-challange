import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { DocumentReport, SummaryReport } from '../models/report.model';
import { HttpService } from './http.service';

/** Typed client for the report endpoints (shared with automation consumers). */
@Injectable({ providedIn: 'root' })
export class ReportService {
  private readonly http = inject(HttpService);

  summary(): Observable<SummaryReport> {
    return this.http.get<SummaryReport>('/reports/summary/');
  }

  forDocument(id: string): Observable<DocumentReport> {
    return this.http.get<DocumentReport>(`/documents/${id}/report/`);
  }
}
