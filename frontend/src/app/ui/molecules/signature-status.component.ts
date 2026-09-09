import { ChangeDetectionStrategy, Component, computed, input } from '@angular/core';

/**
 * What the provider reports about signing — read-only, so a dot and a label,
 * never a badge (data-model section 2).
 *
 * The vocabulary belongs to the provider, not to us: the set is open. Only the
 * signed and refused cases are recognised so they get their colour; everything
 * else falls through to the neutral dot and is shown exactly as it arrived. A
 * word we have never seen must not break the row or read as an error (FR-004).
 */
const SIGNED = new Set(['signed', 'assinado']);
const REFUSED = new Set(['refused', 'rejected', 'recusado']);

@Component({
  selector: 'app-signature-status',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    @if (key()) {
      <span class="sig">
        <span class="sig__dot {{ dot() }}"></span>{{ status() }}
      </span>
    } @else {
      <span class="sig sig--none">—</span>
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
export class SignatureStatusComponent {
  readonly status = input.required<string | null>();

  /** Folded for matching only — the label itself is always shown verbatim. */
  readonly key = computed(() => (this.status() ?? '').trim().toLowerCase());

  readonly dot = computed(() => {
    const key = this.key();
    if (SIGNED.has(key)) return 'sig__dot--signed';
    if (REFUSED.has(key)) return 'sig__dot--refused';
    return '';
  });
}
