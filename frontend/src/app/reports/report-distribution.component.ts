import { ChangeDetectionStrategy, Component, computed, input } from '@angular/core';

import { ProviderStatusBadgeComponent } from '../ui/molecules/provider-status-badge.component';
import { SignatureStatusComponent } from '../ui/molecules/signature-status.component';

/**
 * One distribution, drawn as labelled bars (FR-014).
 *
 * Every bar carries its own label and count, so nothing here depends on a key,
 * an axis or a gridline: the colour is a second reading of a fact the row
 * already states in words (FR-002).
 *
 * The two distributions on the screen are different scales and must not look
 * alike, so the label is rendered by the molecule that owns the vocabulary —
 * the badge for the hand-off we perform, the dot for the signature the provider
 * reports (Principle IX).
 *
 * Layer: organism, private to the report screen.
 */

export interface DistributionEntry {
  /** The provider's own word, never translated. */
  value: string;
  count: number;
}

export type DistributionScale = 'provider' | 'signature';

/**
 * The four fills are theme-invariant marks on a known ground and are the
 * documented exception to the token rule (contracts/design-tokens.md). Keeping
 * the set closed here is what stops a later distribution inventing a fifth.
 */
type BarTone = 'ok' | 'neutral' | 'bad' | 'risk';

interface Bar extends DistributionEntry {
  tone: BarTone;
  share: number;
}

/** The fill only has to agree with the mark beside it; it never replaces it. */
const toneOf = (scale: DistributionScale, value: string): BarTone => {
  const normalised = value.trim().toLowerCase();
  const ok = scale === 'provider' ? ['submitted'] : ['signed', 'assinado'];
  const bad = scale === 'provider' ? ['failed'] : ['refused', 'rejected', 'recusado'];

  if (ok.includes(normalised)) {
    return 'ok';
  }
  return bad.includes(normalised) ? 'bad' : 'neutral';
};

@Component({
  selector: 'app-report-distribution',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [ProviderStatusBadgeComponent, SignatureStatusComponent],
  templateUrl: './report-distribution.component.html',
  styleUrl: './report-distribution.component.scss',
})
export class ReportDistributionComponent {
  readonly heading = input.required<string>();
  readonly description = input.required<string>();
  readonly entries = input.required<DistributionEntry[]>();
  readonly scale = input.required<DistributionScale>();
  /** FR-013: the caller words the absence, because only it knows what is absent. */
  readonly empty = input('Nenhum dado ainda.');

  /**
   * Width is the share of this distribution's own total, so the bars of one
   * figure add up to the whole and can be read against each other — never
   * against the bars of the other figure, which counts a different set.
   */
  readonly bars = computed<Bar[]>(() => {
    const entries = this.entries();
    const total = entries.reduce((sum, entry) => sum + entry.count, 0);

    return entries.map((entry) => ({
      ...entry,
      tone: toneOf(this.scale(), entry.value),
      share: total === 0 ? 0 : (entry.count / total) * 100,
    }));
  });
}
