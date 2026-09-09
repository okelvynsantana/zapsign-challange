import { ChangeDetectionStrategy, Component, input } from '@angular/core';
import { FormArray, FormGroup, ReactiveFormsModule } from '@angular/forms';

import { IconComponent } from '../ui/atoms/icon.component';
import { SignerForm } from './signer-form';

/**
 * Repeatable signer rows inside the document form (US2, FR-006).
 *
 * Owns no state of its own — it renders and edits the `FormArray` the document form
 * passes in, so validation and submission stay in one place.
 */
@Component({
  selector: 'app-signer-rows',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [ReactiveFormsModule, IconComponent],
  template: `
    <fieldset class="signers" [formGroup]="parent()">
      <legend class="eyebrow">Signatários</legend>
      <div class="signers__list" formArrayName="signers">
        @for (row of rows().controls; track $index) {
          <div class="signer-row" [formGroupName]="$index">
            <label class="field">
              <span class="visually-hidden">Nome do signatário {{ $index + 1 }}</span>
              <input
                class="inp"
                type="text"
                formControlName="name"
                placeholder="Nome completo"
                [attr.data-testid]="'signer-name-' + $index"
              />
            </label>
            <label class="field">
              <span class="visually-hidden">E-mail do signatário {{ $index + 1 }}</span>
              <input
                class="inp"
                type="email"
                formControlName="email"
                placeholder="email@exemplo.com"
                [attr.data-testid]="'signer-email-' + $index"
              />
            </label>
            <button
              type="button"
              class="btn btn--sm btn--icon"
              (click)="remove($index)"
              [disabled]="rows().length === 1"
              [attr.aria-label]="'Remover signatário ' + ($index + 1)"
              data-testid="signer-remove"
            >
              <app-icon name="minus" />
            </button>
          </div>
        }
      </div>
      <button type="button" class="btn btn--sm signers__add" (click)="add()" data-testid="signer-add">
        <app-icon name="plus" />Adicionar signatário
      </button>
    </fieldset>
  `,
  styles: [
    `
      .signers {
        display: flex;
        flex-direction: column;
        gap: var(--space-2);
        margin: 0;
        padding: 0;
        border: 0;
      }

      .signers__list {
        display: flex;
        flex-direction: column;
        gap: var(--space-2);
      }

      /* Name is given twice the room of the address: it wraps sooner and is the
         part a person scans the list by. */
      .signer-row {
        display: grid;
        grid-template-columns: minmax(0, 1.1fr) minmax(0, 1fr) auto;
        gap: var(--space-2);
        align-items: center;
      }

      .signers__add {
        align-self: flex-start;
      }
    `,
  ],
})
export class SignerRowsComponent {
  readonly parent = input.required<FormGroup>();
  /** Factory supplied by the parent so the row shape stays owned by the form. */
  readonly makeRow = input.required<() => SignerForm>();

  rows(): FormArray<SignerForm> {
    return this.parent().get('signers') as FormArray<SignerForm>;
  }

  add(): void {
    this.rows().push(this.makeRow()());
  }

  remove(index: number): void {
    // A document always needs at least one signer (FR-007).
    if (this.rows().length > 1) {
      this.rows().removeAt(index);
    }
  }
}
