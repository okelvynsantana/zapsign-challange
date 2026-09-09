import { ChangeDetectionStrategy, Component, OnInit, computed, inject, signal } from '@angular/core';

import { ReportService } from '../core/api/report.service';
import { ApiError } from '../core/models/api.model';
import { SummaryReport } from '../core/models/report.model';
import { IconComponent } from '../ui/atoms/icon.component';
import { ErrorMessageComponent } from '../ui/molecules/error-message.component';
import { DistributionEntry, ReportDistributionComponent } from './report-distribution.component';
import { ReportTilesComponent } from './report-tiles.component';

/**
 * The aggregated report (US4) — the same data automation pulls from the API.
 *
 * The page fetches and unpacks; the tiles and the two figures do the reading
 * (contracts/ui-components.md).
 */
@Component({
  selector: 'app-reports',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    ErrorMessageComponent,
    IconComponent,
    ReportTilesComponent,
    ReportDistributionComponent,
  ],
  templateUrl: './reports.component.html',
  styleUrl: './reports.component.scss',
})
export class ReportsComponent implements OnInit {
  private readonly reports = inject(ReportService);

  readonly summary = signal<SummaryReport | null>(null);
  readonly error = signal<ApiError | null>(null);

  /** Kept in the order the API sent them: the sequence is part of the answer. */
  readonly providerEntries = computed(() => this.toEntries(this.summary()?.by_provider_status));
  readonly signatureEntries = computed(() => this.toEntries(this.summary()?.by_signature_status));

  ngOnInit(): void {
    this.reports.summary().subscribe({
      next: (summary) => this.summary.set(summary),
      error: (err: ApiError) => this.error.set(err),
    });
  }

  /** An instant is shown as the machine recorded it; only the seconds go. */
  timestamp(iso: string): string {
    return iso.slice(0, 16).replace('T', ' ');
  }

  private toEntries(counts: Record<string, number> | undefined): DistributionEntry[] {
    return Object.entries(counts ?? {}).map(([value, count]) => ({ value, count }));
  }
}
