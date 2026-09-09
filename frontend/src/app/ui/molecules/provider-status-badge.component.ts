import { ChangeDetectionStrategy, Component, computed, input } from '@angular/core';

import { ProviderStatus } from '../../core/models/document.model';
import { IconComponent, IconName } from '../atoms/icon.component';

interface Mark {
  modifier: string;
  icon: IconName;
}

/**
 * The one scale we own: whether the document reached the signature provider.
 *
 * It is the only status drawn as a badge, because it is the only one carrying a
 * recovery action of ours (Constitution Principle IX, data-model section 1).
 * An unexpected value is a defect rather than a display case, so it falls back
 * to the muted family — visibly odd beats silently mapped to a wrong meaning.
 *
 * The input takes a plain string on purpose. Our own writes only ever produce
 * the three values above, but the aggregated report keys its distribution off
 * whatever the API returned, so a renderer that refused an unknown string would
 * either fail to compile there or force a cast that throws the fallback away.
 */
const MARKS: Record<ProviderStatus, Mark> = {
  pending_integration: { modifier: 'badge--pending', icon: 'dashed-circle' },
  submitted: { modifier: 'badge--ok', icon: 'check' },
  failed: { modifier: 'badge--bad', icon: 'cross' },
};

@Component({
  selector: 'app-provider-status-badge',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [IconComponent],
  template: `
    <span class="badge {{ mark().modifier }}">
      <app-icon [name]="mark().icon" />{{ status() }}
    </span>
  `,
  styles: [
    `
      :host {
        display: inline-flex;
      }
    `,
  ],
})
export class ProviderStatusBadgeComponent {
  readonly status = input.required<ProviderStatus | (string & {})>();

  /** The label stays the raw value: it is our own vocabulary, never translated (FR-003). */
  readonly mark = computed<Mark>(
    () => MARKS[this.status() as ProviderStatus] ?? MARKS.pending_integration,
  );
}
