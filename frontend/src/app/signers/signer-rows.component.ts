import { Component, input } from '@angular/core';
import { FormArray, FormGroup, ReactiveFormsModule } from '@angular/forms';

import { SignerForm } from './signer-form';

/**
 * Repeatable signer rows inside the document form (US2, FR-006).
 *
 * Owns no state of its own — it renders and edits the `FormArray` the document form
 * passes in, so validation and submission stay in one place.
 */
@Component({
  selector: 'app-signer-rows',
  imports: [ReactiveFormsModule],
  template: `
    <fieldset [formGroup]="parent()">
      <legend>Signers</legend>
      <div formArrayName="signers">
        @for (row of rows().controls; track $index) {
          <div class="signer-row" [formGroupName]="$index">
            <input
              type="text"
              formControlName="name"
              placeholder="Full name"
              [attr.data-testid]="'signer-name-' + $index"
            />
            <input
              type="email"
              formControlName="email"
              placeholder="email@example.com"
              [attr.data-testid]="'signer-email-' + $index"
            />
            <button
              type="button"
              (click)="remove($index)"
              [disabled]="rows().length === 1"
              data-testid="signer-remove"
            >
              Remove
            </button>
          </div>
        }
      </div>
      <button type="button" (click)="add()" data-testid="signer-add">Add signer</button>
    </fieldset>
  `,
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
