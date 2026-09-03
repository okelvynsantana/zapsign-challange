import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormArray, FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';

import { CompanyService } from '../core/api/company.service';
import { DocumentService } from '../core/api/document.service';
import { ApiError } from '../core/models/api.model';
import { Company } from '../core/models/company.model';
import { Document } from '../core/models/document.model';
import { ErrorMessageComponent } from '../shared/error-message.component';
import { AnalysisPanelComponent } from './analysis-panel.component';
import { SignerForm } from '../signers/signer-form';
import { SignerRowsComponent } from '../signers/signer-rows.component';

/**
 * Document and signer management (US2).
 *
 * Every mutation writes the returned resource straight into the list signal, so the view
 * reflects a create, edit, delete or resync with no reload (FR-012, SC-004).
 */
@Component({
  selector: 'app-documents',
  imports: [
    ReactiveFormsModule,
    ErrorMessageComponent,
    SignerRowsComponent,
    AnalysisPanelComponent,
  ],
  templateUrl: './documents.component.html',
})
export class DocumentsComponent implements OnInit {
  private readonly documents = inject(DocumentService);
  private readonly companies = inject(CompanyService);
  private readonly fb = inject(FormBuilder);

  readonly items = signal<Document[]>([]);
  readonly companyOptions = signal<Company[]>([]);
  readonly selected = signal<Document | null>(null);
  readonly loading = signal(false);
  readonly error = signal<ApiError | null>(null);
  readonly editingId = signal<string | null>(null);

  readonly isEditing = computed(() => this.editingId() !== null);

  readonly form = this.fb.nonNullable.group({
    company: ['', Validators.required],
    name: ['', [Validators.required, Validators.maxLength(255)]],
    pdf_url: ['', [Validators.required]],
    external_id: [''],
    signers: this.fb.array<SignerForm>([this.signerRow()]),
  });

  /** Passed to `app-signer-rows` so it can append rows of the right shape. */
  readonly makeRow = (): SignerForm => this.signerRow();

  ngOnInit(): void {
    this.reload();
    this.companies.list().subscribe({
      next: (page) => this.companyOptions.set(page.results),
      error: (err: ApiError) => this.error.set(err),
    });
  }

  reload(): void {
    this.loading.set(true);
    this.documents.list().subscribe({
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
    const value = this.form.getRawValue();
    const editingId = this.editingId();

    if (editingId) {
      this.documents
        .update(editingId, {
          name: value.name,
          pdf_url: value.pdf_url,
          external_id: value.external_id,
          signers: value.signers,
        })
        .subscribe({
          next: (updated) => {
            this.replace(updated);
            this.resetForm();
          },
          error: (err: ApiError) => this.error.set(err),
        });
      return;
    }

    this.documents
      .create({
        company: value.company,
        name: value.name,
        pdf_url: value.pdf_url,
        external_id: value.external_id || undefined,
        signers: value.signers,
      })
      .subscribe({
        next: (created) => {
          this.items.update((items) => [created, ...items]);
          this.resetForm();
        },
        error: (err: ApiError) => this.error.set(err),
      });
  }

  edit(document: Document): void {
    this.editingId.set(document.id);
    this.error.set(null);
    this.signers.clear();
    for (const signer of document.signers) {
      this.signers.push(this.signerRow(signer.name, signer.email));
    }
    if (this.signers.length === 0) {
      this.signers.push(this.signerRow());
    }
    this.form.patchValue({
      company: document.company,
      name: document.name,
      pdf_url: document.pdf_url,
      external_id: document.external_id ?? '',
    });
  }

  select(document: Document): void {
    this.selected.set(document);
  }

  remove(document: Document): void {
    this.error.set(null);
    this.documents.remove(document.id).subscribe({
      next: () => {
        this.items.update((items) => items.filter((i) => i.id !== document.id));
        if (this.selected()?.id === document.id) {
          this.selected.set(null);
        }
      },
      error: (err: ApiError) => this.error.set(err),
    });
  }

  /** Retry the ZapSign hand-off, or refresh the signature status (FR-010). */
  resync(document: Document): void {
    this.error.set(null);
    this.documents.resync(document.id).subscribe({
      next: (updated) => this.replace(updated),
      error: (err: ApiError) => this.error.set(err),
    });
  }

  /** A fresh analysis changes the document's `latest_analysis`; re-read the row. */
  onAnalyzed(document: Document): void {
    this.documents.get(document.id).subscribe({
      next: (updated) => this.replace(updated),
      error: (err: ApiError) => this.error.set(err),
    });
  }

  canResync(document: Document): boolean {
    return document.provider_status === 'failed' || document.provider_status === 'submitted';
  }

  cancelEdit(): void {
    this.resetForm();
  }

  get signers(): FormArray<SignerForm> {
    return this.form.get('signers') as FormArray<SignerForm>;
  }

  private signerRow(name = '', email = ''): SignerForm {
    return this.fb.nonNullable.group({
      name: [name, Validators.required],
      email: [email, [Validators.required, Validators.email]],
    });
  }

  private replace(document: Document): void {
    this.items.update((items) => items.map((i) => (i.id === document.id ? document : i)));
    if (this.selected()?.id === document.id) {
      this.selected.set(document);
    }
  }

  private resetForm(): void {
    this.editingId.set(null);
    this.signers.clear();
    this.signers.push(this.signerRow());
    this.form.patchValue({ company: '', name: '', pdf_url: '', external_id: '' });
  }

  private fail(err: ApiError): void {
    this.loading.set(false);
    this.error.set(err);
  }
}
