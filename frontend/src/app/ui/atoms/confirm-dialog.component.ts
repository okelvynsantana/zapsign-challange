import {
  ChangeDetectionStrategy,
  Component,
  ElementRef,
  input,
  output,
  viewChild,
} from '@angular/core';

/** Only to give the heading a stable target for `aria-labelledby`. */
let nextId = 0;

/**
 * The confirmation step in front of an irreversible action.
 *
 * Built on the native `<dialog>` with `showModal()`, so the platform supplies
 * the focus trap, `Esc` to dismiss, the inertness of the page behind and the
 * backdrop — the four things a hand-rolled overlay gets subtly wrong and no
 * dependency is worth buying (research R-004). None of them is reimplemented
 * here; what is left is the outcome bookkeeping below.
 *
 * Layer: atom. It knows no domain model and injects nothing — the caller owns
 * the action, this owns only the question.
 */
@Component({
  selector: 'app-confirm-dialog',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <dialog #dialog class="card" [attr.aria-labelledby]="titleId" (close)="onPlatformClose()">
      <div class="dlg">
        <h2 class="t-panel" [id]="titleId">{{ title() }}</h2>
        @if (message()) {
          <p class="t-body dlg__message">{{ message() }}</p>
        }
        <div class="dlg__actions">
          <button #cancel type="button" class="btn" (click)="settle('cancel')">
            {{ cancelLabel() }}
          </button>
          <button
            #confirm
            type="button"
            class="btn"
            [class.btn--danger]="destructive()"
            [class.btn--primary]="!destructive()"
            (click)="settle('confirm')"
          >
            {{ confirmLabel() }}
          </button>
        </div>
      </div>
    </dialog>
  `,
  styles: [
    `
      :host {
        display: contents;
      }

      dialog {
        max-width: var(--rail-width);
        padding: 0;
        color: var(--ink);
      }

      dialog::backdrop {
        background: var(--scrim);
      }

      .dlg {
        display: flex;
        flex-direction: column;
        gap: var(--space-3);
        padding: var(--space-4);
      }

      .dlg__message {
        color: var(--ink-2);
      }

      .dlg__actions {
        display: flex;
        justify-content: flex-end;
        gap: var(--space-2);
        margin-top: var(--space-1);
      }
    `,
  ],
})
export class ConfirmDialogComponent {
  readonly title = input.required<string>();
  readonly message = input('');
  readonly confirmLabel = input('Confirmar');
  readonly cancelLabel = input('Cancelar');
  /** Colours confirm as dangerous and hands the initial focus to cancel. */
  readonly destructive = input(false);

  readonly confirmed = output<void>();
  readonly cancelled = output<void>();

  protected readonly titleId = `confirm-dialog-title-${nextId++}`;

  private readonly dialogRef = viewChild.required<ElementRef<HTMLDialogElement>>('dialog');
  private readonly confirmRef = viewChild.required<ElementRef<HTMLButtonElement>>('confirm');
  private readonly cancelRef = viewChild.required<ElementRef<HTMLButtonElement>>('cancel');

  /**
   * Every route out of the dialog converges here, and only the first one
   * counts: pressing confirm closes the dialog, which makes the platform fire
   * `close`, which arrives as a second dismissal. Without the latch a single
   * confirm would also emit a cancellation.
   */
  private settled = true;

  open(): void {
    this.settled = false;
    this.dialogRef().nativeElement.showModal();
    // The platform focuses the first control; on a destructive action that must
    // be the way out, so destroying something is never one stray Enter away.
    (this.destructive() ? this.cancelRef() : this.confirmRef()).nativeElement.focus();
  }

  /** `Esc`, the backdrop, or anything else the platform treats as a dismissal. */
  protected onPlatformClose(): void {
    this.settle('cancel');
  }

  protected settle(outcome: 'confirm' | 'cancel'): void {
    if (this.settled) {
      return;
    }
    // Latched before close() so the `close` event it triggers finds it shut.
    this.settled = true;

    const dialog = this.dialogRef().nativeElement;
    if (dialog.open) {
      dialog.close();
    }

    if (outcome === 'confirm') {
      this.confirmed.emit();
    } else {
      this.cancelled.emit();
    }
  }
}
