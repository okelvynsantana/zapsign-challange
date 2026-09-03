import { Component, OnInit, inject, signal } from '@angular/core';

import { ReportService } from '../core/api/report.service';
import { ApiError } from '../core/models/api.model';
import { SummaryReport } from '../core/models/report.model';
import { ErrorMessageComponent } from '../shared/error-message.component';

/** The aggregated report (US4) — the same data automation pulls from the API. */
@Component({
  selector: 'app-reports',
  imports: [ErrorMessageComponent],
  templateUrl: './reports.component.html',
})
export class ReportsComponent implements OnInit {
  private readonly reports = inject(ReportService);

  readonly summary = signal<SummaryReport | null>(null);
  readonly error = signal<ApiError | null>(null);

  ngOnInit(): void {
    this.reports.summary().subscribe({
      next: (summary) => this.summary.set(summary),
      error: (err: ApiError) => this.error.set(err),
    });
  }

  entries(counts: Record<string, number>): [string, number][] {
    return Object.entries(counts);
  }
}
