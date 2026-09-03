import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';

import { CompanyService } from '../core/api/company.service';
import { ApiError } from '../core/models/api.model';
import { Company } from '../core/models/company.model';
import { ErrorMessageComponent } from '../shared/error-message.component';

/**
 * Organization profile management (US1).
 *
 * List state is a signal the mutations write straight into, so a create, edit or delete
 * is reflected without a navigation or a re-fetch round trip (FR-012, SC-004).
 */
@Component({
  selector: 'app-companies',
  imports: [ReactiveFormsModule, ErrorMessageComponent],
  templateUrl: './companies.component.html',
})
export class CompaniesComponent implements OnInit {
  private readonly companies = inject(CompanyService);
  private readonly fb = inject(FormBuilder);

  readonly items = signal<Company[]>([]);
  readonly loading = signal(false);
  readonly error = signal<ApiError | null>(null);
  readonly editingId = signal<string | null>(null);

  readonly isEditing = computed(() => this.editingId() !== null);

  readonly form = this.fb.nonNullable.group({
    name: ['', [Validators.required, Validators.maxLength(255)]],
    api_token: ['', [Validators.required]],
  });

  ngOnInit(): void {
    this.reload();
  }

  reload(): void {
    this.loading.set(true);
    this.companies.list().subscribe({
      next: (page) => {
        this.items.set(page.results);
        this.loading.set(false);
      },
      error: (err: ApiError) => this.fail(err),
    });
  }

  submit(): void {
    if (this.form.invalid) {
      return;
    }
    this.error.set(null);
    const { name, api_token } = this.form.getRawValue();
    const editingId = this.editingId();

    if (editingId) {
      // A blank token means "keep the stored credential" (contracts/rest-api.md).
      const payload = api_token ? { name, api_token } : { name };
      this.companies.update(editingId, payload).subscribe({
        next: (updated) => {
          this.items.update((items) =>
            items.map((item) => (item.id === updated.id ? updated : item)),
          );
          this.resetForm();
        },
        error: (err: ApiError) => this.fail(err),
      });
      return;
    }

    this.companies.create({ name, api_token }).subscribe({
      next: (created) => {
        this.items.update((items) => [...items, created]);
        this.resetForm();
      },
      error: (err: ApiError) => this.fail(err),
    });
  }

  edit(company: Company): void {
    this.editingId.set(company.id);
    this.error.set(null);
    this.form.reset({ name: company.name, api_token: '' });
    // Editing keeps the credential unless one is typed, so it stops being required.
    this.form.controls.api_token.clearValidators();
    this.form.controls.api_token.updateValueAndValidity();
  }

  remove(company: Company): void {
    this.error.set(null);
    this.companies.remove(company.id).subscribe({
      next: () => this.items.update((items) => items.filter((i) => i.id !== company.id)),
      error: (err: ApiError) => this.error.set(err),
    });
  }

  cancelEdit(): void {
    this.resetForm();
  }

  private resetForm(): void {
    this.editingId.set(null);
    this.form.reset({ name: '', api_token: '' });
    this.form.controls.api_token.setValidators([Validators.required]);
    this.form.controls.api_token.updateValueAndValidity();
  }

  private fail(err: ApiError): void {
    this.loading.set(false);
    this.error.set(err);
  }
}
