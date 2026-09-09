import { ChangeDetectionStrategy, Component, input } from '@angular/core';

import { IconComponent } from '../atoms/icon.component';
import { Insight } from '../../core/models/analysis.model';

/**
 * One insight from an analysis run.
 *
 * A flagged insight is a finding about *the contract* — something a person has
 * to weigh — whereas the red family is reserved for a defect in our own
 * processing (data-model §3, FR-008). So this component stays inside the ochre
 * `--warn-*` family and the `risk` triangle, and never reaches for the red
 * failure family or the `alert` mark: a demanding clause in a contract must not
 * read as a broken system.
 *
 * The triangle and the `RISCO` word carry the flag together, so the meaning
 * survives when the colour does not (accessibility contract — colour is never
 * the sole carrier).
 *
 * Layer: molecule. It binds one domain value to atoms and injects nothing.
 * `role="listitem"` keeps the count intact for a screen reader, since the host
 * element sits between the caller's list and its rows.
 */
@Component({
  selector: 'app-insight-item',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [IconComponent],
  host: {
    role: 'listitem',
    '[class.insight--risk]': 'insight().risk',
  },
  template: `
    @if (insight().risk) {
      <app-icon name="risk" />
      <span class="insight__body">
        <span class="eyebrow insight__flag">RISCO</span>
        <span class="t-body">{{ insight().text }}</span>
      </span>
    } @else {
      <span class="insight__dot" aria-hidden="true"></span>
      <span class="t-body">{{ insight().text }}</span>
    }
  `,
  styles: [
    `
      :host {
        display: flex;
        align-items: flex-start;
        gap: var(--space-2);
        /* The dot and the triangle both paint with currentColor, so the whole
         * variant switches family from this one declaration. */
        color: var(--ink-2);
      }

      :host(.insight--risk) {
        padding: var(--space-2);
        border: 1px solid var(--warn-line);
        border-radius: var(--radius-control);
        background: var(--warn-bg);
        color: var(--warn-ink);
      }

      .insight__dot {
        flex-shrink: 0;
        /* Aligns the dot with the first line of text, not the block. */
        margin-top: var(--space-2);
        width: var(--space-1);
        height: var(--space-1);
        border-radius: 50%;
        background: currentColor;
      }

      .insight__body {
        display: flex;
        flex-direction: column;
        gap: var(--space-1);
      }

      /* .eyebrow is muted by default; the flag belongs to the ochre family. */
      .insight__flag {
        color: inherit;
      }
    `,
  ],
})
export class InsightItemComponent {
  readonly insight = input.required<Insight>();
}
