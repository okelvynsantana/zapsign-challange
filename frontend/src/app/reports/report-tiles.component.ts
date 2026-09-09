import { ChangeDetectionStrategy, Component, computed, input } from '@angular/core';

import { SummaryReport } from '../core/models/report.model';

/**
 * The four numbers the report opens with (FR-014).
 *
 * Two are read straight off the payload and two are derived, so every tile also
 * states the basis it was counted on — a hero number nobody can reconstruct is
 * a number nobody can act on.
 *
 * Layer: organism. Only the report screen shows these, so it lives beside it
 * rather than in `ui/organisms/` (contracts/ui-components.md).
 */

/** Signature values that mean the signing is over, one way or the other. */
const SETTLED = new Set(['signed', 'assinado', 'refused', 'rejected', 'recusado']);

@Component({
  selector: 'app-report-tiles',
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './report-tiles.component.html',
  styleUrl: './report-tiles.component.scss',
})
export class ReportTilesComponent {
  readonly report = input.required<SummaryReport>();

  /**
   * Outstanding is defined by exclusion, not by a list of pending words: the
   * provider owns this vocabulary and extends it, so a value we have never seen
   * has to keep counting as outstanding instead of dropping out of the total.
   */
  private readonly awaitingEntries = computed(() =>
    Object.entries(this.report().by_signature_status).filter(
      ([value, count]) => count > 0 && !SETTLED.has(value.trim().toLowerCase()),
    ),
  );

  readonly awaiting = computed(() =>
    this.awaitingEntries().reduce((total, [, count]) => total + count, 0),
  );

  /** Named in the support line so the derivation above stays inspectable. */
  readonly awaitingValues = computed(() => this.awaitingEntries().map(([value]) => value));

  readonly failed = computed(() => this.report().by_provider_status['failed'] ?? 0);
}
