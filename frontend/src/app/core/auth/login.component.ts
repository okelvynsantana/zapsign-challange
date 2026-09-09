import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router } from '@angular/router';

import { ApiError } from '../models/api.model';
import { IconComponent } from '../../ui/atoms/icon.component';
import { ErrorMessageComponent } from '../../ui/molecules/error-message.component';
import { AuthService } from './auth.service';

/**
 * The way in (US0).
 *
 * The rejection is kept as the whole `ApiError` rather than its `detail` string: the
 * code is the only part a person can quote in a support conversation, and the banner
 * already knows how to render both (data-model §7).
 */
@Component({
  selector: 'app-login',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [ReactiveFormsModule, ErrorMessageComponent, IconComponent],
  templateUrl: './login.component.html',
  styleUrl: './login.component.scss',
})
export class LoginComponent {
  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);

  readonly form = inject(FormBuilder).nonNullable.group({
    username: ['', Validators.required],
    password: ['', Validators.required],
  });

  readonly pending = signal(false);
  readonly error = signal<ApiError | null>(null);

  submit(): void {
    if (this.form.invalid) {
      return;
    }
    const { username, password } = this.form.getRawValue();
    this.pending.set(true);
    this.error.set(null);

    this.auth.login(username, password).subscribe({
      next: () => {
        this.pending.set(false);
        void this.router.navigate(['/documents']);
      },
      error: (err: ApiError) => {
        this.pending.set(false);
        this.error.set(err);
      },
    });
  }
}
