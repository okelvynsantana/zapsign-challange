import { Component, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router } from '@angular/router';

import { ApiError } from '../models/api.model';
import { AuthService } from './auth.service';

@Component({
  selector: 'app-login',
  imports: [ReactiveFormsModule],
  template: `
    <section class="panel">
      <h1>Sign in</h1>
      <form [formGroup]="form" (ngSubmit)="submit()">
        <label>
          Username
          <input type="text" formControlName="username" autocomplete="username" />
        </label>
        <label>
          Password
          <input type="password" formControlName="password" autocomplete="current-password" />
        </label>
        @if (error(); as message) {
          <p class="error" role="alert">{{ message }}</p>
        }
        <button type="submit" [disabled]="form.invalid || pending()">
          {{ pending() ? 'Signing in…' : 'Sign in' }}
        </button>
      </form>
    </section>
  `,
})
export class LoginComponent {
  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);

  readonly form = inject(FormBuilder).nonNullable.group({
    username: ['', Validators.required],
    password: ['', Validators.required],
  });

  readonly pending = signal(false);
  readonly error = signal<string | null>(null);

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
        this.error.set(err.detail);
      },
    });
  }
}
