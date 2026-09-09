import { ChangeDetectionStrategy, Component, computed, input, output } from '@angular/core';
import { toObservable, toSignal } from '@angular/core/rxjs-interop';
import { FormControl, FormControlStatus, FormGroup, ReactiveFormsModule } from '@angular/forms';
import { startWith, switchMap } from 'rxjs';

import { IconComponent } from '../ui/atoms/icon.component';

/** The group the page owns and hands down; this organism only renders it. */
export type CompanyFormGroup = FormGroup<{
  name: FormControl<string>;
  api_token: FormControl<string>;
}>;

/**
 * Name plus the credential's secret treatment (FR-012, Constitution Principle V).
 *
 * The form group stays with the page because it is what the mutation reads, and
 * whether a submit is a create or a patch is not this component's decision.
 *
 * Nothing here ever holds the raw credential: only `api_token_masked` comes back
 * from the API, so that is the only value bound, and the typed token lives in the
 * control alone — never as an attribute in the DOM.
 */
@Component({
  selector: 'app-company-form',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [ReactiveFormsModule, IconComponent],
  templateUrl: './company-form.component.html',
  styleUrl: './company-form.component.scss',
})
export class CompanyFormComponent {
  readonly form = input.required<CompanyFormGroup>();
  readonly editing = input(false);
  /** Masked credential of the organization being edited; empty while creating. */
  readonly maskedToken = input('');

  readonly submitted = output<void>();
  readonly cancelled = output<void>();

  /* The page resets the group from outside this view, which OnPush cannot see,
   * so the submit gate follows the group's own status stream instead of reading
   * `invalid` during change detection. */
  private readonly status = toSignal(
    toObservable(this.form).pipe(
      switchMap((group) => group.statusChanges.pipe(startWith(group.status))),
    ),
    { initialValue: 'INVALID' as FormControlStatus },
  );

  readonly submitDisabled = computed(() => this.status() !== 'VALID');

  /** An error is only shown once the person has had a turn at the field. */
  nameFailed(): boolean {
    return this.failed('name');
  }

  tokenFailed(): boolean {
    return this.failed('api_token');
  }

  /** The hint is permanent; the error joins it only while it is on screen. */
  tokenDescribedBy(): string {
    return this.tokenFailed() ? 'company-token-error company-token-hint' : 'company-token-hint';
  }

  private failed(control: 'name' | 'api_token'): boolean {
    const field = this.form().controls[control];
    return field.invalid && (field.dirty || field.touched);
  }
}
