import { Component, inject, input, output, signal } from '@angular/core';

import { DocumentService } from '../core/api/document.service';
import { DocumentAnalysis } from '../core/models/analysis.model';
import { ApiError } from '../core/models/api.model';
import { Document } from '../core/models/document.model';
import { ErrorMessageComponent } from '../shared/error-message.component';

/**
 * The AI analysis view for one document (US3).
 *
 * Shows the latest run by default and loads the append-only history on demand (FR-018).
 * "Re-analyze" emits the new run upward so the parent can refresh the document row —
 * this component never mutates the document it was given.
 */
@Component({
  selector: 'app-analysis-panel',
  imports: [ErrorMessageComponent],
  templateUrl: './analysis-panel.component.html',
})
export class AnalysisPanelComponent {
  private readonly documents = inject(DocumentService);

  readonly document = input.required<Document>();
  readonly analyzed = output<DocumentAnalysis>();

  readonly history = signal<DocumentAnalysis[]>([]);
  readonly historyVisible = signal(false);
  readonly pending = signal(false);
  readonly error = signal<ApiError | null>(null);

  analyze(): void {
    this.pending.set(true);
    this.error.set(null);

    this.documents.analyze(this.document().id).subscribe({
      next: (analysis) => {
        this.pending.set(false);
        // A run is appended, never an overwrite (FR-017).
        this.history.update((runs) => [analysis, ...runs]);
        this.analyzed.emit(analysis);
      },
      error: (err: ApiError) => {
        this.pending.set(false);
        this.error.set(err);
      },
    });
  }

  toggleHistory(): void {
    const nextVisible = !this.historyVisible();
    this.historyVisible.set(nextVisible);
    if (nextVisible) {
      this.documents.analyses(this.document().id).subscribe({
        next: (page) => this.history.set(page.results),
        error: (err: ApiError) => this.error.set(err),
      });
    }
  }

  riskCount(analysis: DocumentAnalysis): number {
    return analysis.insights.filter((insight) => insight.risk).length;
  }
}
