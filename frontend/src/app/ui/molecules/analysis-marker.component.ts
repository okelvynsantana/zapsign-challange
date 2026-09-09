import { ChangeDetectionStrategy, Component, computed, input } from '@angular/core';

import { DocumentAnalysis } from '../../core/models/analysis.model';
import { IconComponent } from '../atoms/icon.component';

/**
 * The outcome of the newest analysis run — icon plus text, never a badge.
 *
 * A risk is a finding about the contract and asks for human judgement; a
 * failure is a defect in our processing and asks for a retry. They share
 * neither mark nor colour family, so the two can never be read for one another
 * (FR-008, data-model section 3).
 */
@Component({
  selector: 'app-analysis-marker',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [IconComponent],
  template: `
    @if (analysis(); as run) {
      @if (run.state === 'failed') {
        <span class="mark mark--failed"><app-icon name="alert" />falhou</span>
      } @else if (risks() > 0) {
        <span class="mark mark--risk"><app-icon name="risk" />{{ riskLabel() }}</span>
      } @else {
        <span class="mark"><app-icon name="check-circle" />sem risco</span>
      }
    } @else {
      <span class="mark mark--none">—</span>
    }
  `,
  styles: [
    `
      :host {
        display: inline-flex;
      }
    `,
  ],
})
export class AnalysisMarkerComponent {
  readonly analysis = input.required<DocumentAnalysis | null>();

  /** Earlier runs live in history; only the latest one may raise a marker. */
  readonly risks = computed(() => (this.analysis()?.insights ?? []).filter((i) => i.risk).length);

  readonly riskLabel = computed(() => {
    const n = this.risks();
    return `${n} ${n === 1 ? 'risco' : 'riscos'}`;
  });
}
