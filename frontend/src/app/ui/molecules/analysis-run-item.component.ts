import { DatePipe } from '@angular/common';
import { ChangeDetectionStrategy, Component, computed, input } from '@angular/core';

import { DocumentAnalysis } from '../../core/models/analysis.model';

/**
 * One row of the append-only analysis history (data-model §4, FR-017).
 *
 * A run is a record, not a live state, so the row reports rather than acts: the
 * date, the outcome, how it was produced, and how much it found. `state` and
 * `source` are the backend's own words and stay verbatim in mono — translating
 * them would hide which value the API actually returned (FR-003, FR-021).
 *
 * The risk count is the one number derived here, and it is counted per run: the
 * document's marker only ever reflects the latest one, so an old row must show
 * its own total rather than borrow the current figure.
 *
 * Layer: molecule. It binds one domain value and injects nothing; the parent
 * decides which run is `current`.
 */
@Component({
  selector: 'app-analysis-run-item',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [DatePipe],
  host: { role: 'listitem' },
  template: `
    <span class="mono t-support">{{ run().created_at | date: 'dd/MM HH:mm' }}</span>

    <span
      class="badge"
      [class.badge--ok]="run().state === 'succeeded'"
      [class.badge--bad]="run().state === 'failed'"
      >{{ run().state }}</span
    >

    <span class="mono t-support">{{ run().source }}</span>

    <span class="t-support">{{ riskLabel() }}</span>

    @if (current()) {
      <span class="eyebrow">atual</span>
    }
  `,
  styles: [
    `
      :host {
        display: flex;
        align-items: center;
        /* Wraps rather than scrolls: the row is four short facts, and a narrow
         * window should stack them (FR-027, FR-028). */
        flex-wrap: wrap;
        gap: var(--space-2);
        padding: var(--space-2) 0;
      }

      :host(:not(:first-child)) {
        border-top: 1px solid var(--line-2);
      }
    `,
  ],
})
export class AnalysisRunItemComponent {
  readonly run = input.required<DocumentAnalysis>();
  /** Marks the run the panel is currently showing, so history reads in context. */
  readonly current = input(false);

  private readonly riskCount = computed(
    () => this.run().insights.filter((insight) => insight.risk).length,
  );

  protected readonly riskLabel = computed(() => {
    const count = this.riskCount();
    return count === 1 ? '1 risco' : `${count} riscos`;
  });
}
