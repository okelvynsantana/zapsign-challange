import { ChangeDetectionStrategy, Component, input } from '@angular/core';
import { RouterLink } from '@angular/router';

import { Alert } from '../core/models/alert.model';
import { IconComponent, IconName } from '../ui/atoms/icon.component';

/**
 * One attention group: a stalled list or a risk list, never both.
 *
 * The two groups are separate components on screen because they are separate
 * problems with separate fixes — a document that is late and a document whose
 * analysis found a risk are answered differently, and the same document may
 * legitimately appear in both lists at once (backend `build_alerts`, FR-030).
 * Merging them into one list would hide that.
 *
 * `tone` is what carries the distinction visually: risk is the ochre family,
 * which the token contract reserves for a finding about the contract — never
 * red, which means our own processing failed (Constitution Principle IX).
 *
 * Layer: organism. It binds the domain model and injects nothing.
 */
@Component({
  selector: 'app-alert-group',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink, IconComponent],
  templateUrl: './alert-group.component.html',
  styleUrl: './alert-group.component.scss',
})
export class AlertGroupComponent {
  readonly title = input.required<string>();
  readonly icon = input.required<IconName>();
  readonly alerts = input.required<Alert[]>();
  /** The page's own tally, so the header states what the page counted. */
  readonly count = input.required<number>();
  /** What makes this group's rule legible: a threshold, a source. */
  readonly hint = input('');
  readonly tone = input<'neutral' | 'risk'>('neutral');
  /** The list keeps the identifier the group was known by (identifier contract). */
  readonly listTestId = input.required<string>();
}
