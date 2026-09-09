import { ChangeDetectionStrategy, Component, input } from '@angular/core';

/**
 * The in-progress form of a long-running action.
 *
 * The ring turns but claims no percentage: the backend reports no progress, and
 * a bar that invented one would be a lie the reader could time (contract —
 * atoms, `app-progress-step`).
 *
 * `role="status"` because the work started in response to the reader's own
 * click — they should hear that it is running without having to look for it.
 *
 * Layer: atom. It knows no domain model and injects nothing; the caller decides
 * what is in progress and supplies the words.
 */
@Component({
  selector: 'app-progress-step',
  changeDetection: ChangeDetectionStrategy.OnPush,
  host: { role: 'status' },
  template: `
    <span class="step__ring" aria-hidden="true"></span>
    <span class="step__text">
      <span class="t-body">{{ label() }}</span>
      @if (hint()) {
        <span class="t-support">{{ hint() }}</span>
      }
    </span>
  `,
  styles: [
    `
      :host {
        display: inline-flex;
        align-items: flex-start;
        gap: var(--space-2);
      }

      .step__ring {
        flex-shrink: 0;
        /* Optically centred on the label's first line rather than its box. */
        margin-top: var(--space-1);
        width: var(--space-3);
        height: var(--space-3);
        border: 1px solid var(--line-2);
        /* One darker arc is what makes the rotation visible at all. */
        border-top-color: var(--ink-2);
        border-radius: 50%;
        animation: progress-step-spin 0.8s linear infinite;
      }

      .step__text {
        display: flex;
        flex-direction: column;
        gap: var(--space-1);
      }

      @keyframes progress-step-spin {
        to {
          transform: rotate(1turn);
        }
      }

      /* A spinner is decoration on top of the text, so it is safe to stop it
       * outright for a reader who asked for less motion (accessibility
       * contract). The ring stays as a static mark. */
      @media (prefers-reduced-motion: reduce) {
        .step__ring {
          animation: none;
        }
      }
    `,
  ],
})
export class ProgressStepComponent {
  readonly label = input.required<string>();
  readonly hint = input('');
}
