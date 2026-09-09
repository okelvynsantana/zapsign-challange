import { DatePipe } from '@angular/common';
import { Component, computed, inject, input, output, signal } from '@angular/core';

import { DocumentService } from '../core/api/document.service';
import { DocumentAnalysis } from '../core/models/analysis.model';
import { ApiError } from '../core/models/api.model';
import { Document } from '../core/models/document.model';
import { IconComponent } from '../ui/atoms/icon.component';
import { ProgressStepComponent } from '../ui/atoms/progress-step.component';
import { AnalysisRunItemComponent } from '../ui/molecules/analysis-run-item.component';
import { ErrorMessageComponent } from '../ui/molecules/error-message.component';
import { InsightItemComponent } from '../ui/molecules/insight-item.component';

/** The four legal states of the panel (data-model §4). Derived, never stored. */
export type AnalysisPanelState = 'never-run' | 'in-progress' | 'produced' | 'failed';

/**
 * The plain-language reading of each reason the backend records.
 *
 * The map is exhaustive over the five recorded reasons, but the lookup is not
 * total on purpose: `error_reason` is a backend string, and a value we have not
 * met yet must still leave the panel readable rather than blank (FR-004's rule,
 * applied to the analysis scale).
 */
const FAILURE_EXPLANATIONS: Record<string, string> = {
  unreachable: 'O PDF não pôde ser baixado a partir do endereço informado.',
  not_pdf: 'O arquivo no endereço informado não é um PDF.',
  too_large: 'O arquivo passou do limite de tamanho aceito pela análise.',
  no_text:
    'O PDF não tem camada de texto — provavelmente é um documento digitalizado. ' +
    'Leitura de imagem (OCR) está fora do escopo.',
  timeout: 'A análise passou do tempo limite antes de o modelo responder.',
};

/**
 * The AI analysis view for one document (US3).
 *
 * The panel has exactly four states and each one is drawn (FR-010): the state is
 * derived from `latest_analysis` plus the in-flight flag, so there is nothing to
 * keep in sync and no way to land between two of them.
 *
 * The two failure vocabularies are kept apart here as everywhere else: a flagged
 * insight is a judgement about the contract and stays ochre; a failed run is a
 * defect in our processing and is the only thing painted red (FR-008).
 *
 * "Re-analyze" emits the new run upward so the parent can refresh the document
 * row — this component never mutates the document it was given.
 */
@Component({
  selector: 'app-analysis-panel',
  imports: [
    DatePipe,
    IconComponent,
    ProgressStepComponent,
    AnalysisRunItemComponent,
    ErrorMessageComponent,
    InsightItemComponent,
  ],
  templateUrl: './analysis-panel.component.html',
  styleUrl: './analysis-panel.component.scss',
})
export class AnalysisPanelComponent {
  private readonly documents = inject(DocumentService);

  readonly document = input.required<Document>();
  readonly analyzed = output<DocumentAnalysis>();

  readonly history = signal<DocumentAnalysis[]>([]);
  readonly historyVisible = signal(false);
  readonly pending = signal(false);
  readonly error = signal<ApiError | null>(null);

  /** In-flight wins over the stored outcome: the older run is no longer the news. */
  readonly state = computed<AnalysisPanelState>(() => {
    if (this.pending()) {
      return 'in-progress';
    }
    const latest = this.document().latest_analysis;
    if (latest === null) {
      return 'never-run';
    }
    return latest.state === 'failed' ? 'failed' : 'produced';
  });

  readonly latest = computed(() => this.document().latest_analysis);

  readonly actionLabel = computed(() => {
    switch (this.state()) {
      case 'in-progress':
        return 'Analisando…';
      case 'produced':
        return 'Reanalisar';
      case 'failed':
        return 'Tentar novamente';
      default:
        return 'Analisar agora';
    }
  });

  /** A failed run makes the retry the panel's primary action (FR-009). */
  readonly actionIsPrimary = computed(
    () => this.state() === 'failed' || this.state() === 'never-run',
  );

  readonly failureExplanation = computed(() => {
    const reason = this.latest()?.error_reason;
    return (
      (reason && FAILURE_EXPLANATIONS[reason]) ||
      'A execução não foi concluída e o motivo não foi reconhecido.'
    );
  });

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
}
