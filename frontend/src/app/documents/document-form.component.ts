import { ChangeDetectionStrategy, Component, computed, input, output } from '@angular/core';
import { toObservable, toSignal } from '@angular/core/rxjs-interop';
import { FormGroup, ReactiveFormsModule } from '@angular/forms';
import { switchMap } from 'rxjs';

import { Company } from '../core/models/company.model';
import { IconComponent } from '../ui/atoms/icon.component';
import { SignerForm } from '../signers/signer-form';
import { SignerRowsComponent } from '../signers/signer-rows.component';

/**
 * The `form` mode of the rail: create or edit, in the same region the detail
 * uses (FR-017).
 *
 * The group itself stays on the page, because the page is what decides between
 * a create and a patch and what resets the fields afterwards. This component
 * renders it and reports intent.
 */
@Component({
  selector: 'app-document-form',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [ReactiveFormsModule, IconComponent, SignerRowsComponent],
  templateUrl: './document-form.component.html',
  styleUrl: './document-form.component.scss',
})
export class DocumentFormComponent {
  readonly form = input.required<FormGroup>();
  readonly companies = input<Company[]>([]);
  readonly editing = input(false);
  readonly makeRow = input.required<() => SignerForm>();

  readonly submitted = output<void>();
  readonly cancelled = output<void>();

  /**
   * The page resets the group from outside this view, which OnPush cannot see,
   * so validity is followed through the stream rather than read during change
   * detection — otherwise the button stays stale after a successful create.
   */
  private readonly status = toSignal(
    toObservable(this.form).pipe(switchMap((form) => form.statusChanges)),
    { initialValue: null },
  );

  readonly invalid = computed(() => {
    this.status();
    return this.form().invalid;
  });
}
