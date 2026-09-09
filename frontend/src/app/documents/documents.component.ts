import { Component, OnInit, computed, inject, signal, viewChild } from '@angular/core';
import { FormArray, FormBuilder, Validators } from '@angular/forms';

import { CompanyService } from '../core/api/company.service';
import { DocumentService } from '../core/api/document.service';
import { ApiError } from '../core/models/api.model';
import { Company } from '../core/models/company.model';
import { Document, DocumentFilters, ProviderStatus } from '../core/models/document.model';
import { ConfirmDialogComponent } from '../ui/atoms/confirm-dialog.component';
import { EmptyStateComponent } from '../ui/atoms/empty-state.component';
import { IconComponent } from '../ui/atoms/icon.component';
import { ErrorMessageComponent } from '../ui/molecules/error-message.component';
import { SignerForm } from '../signers/signer-form';
import { DocumentDetailRailComponent } from './document-detail-rail.component';
import { DocumentFormComponent } from './document-form.component';
import { DocumentsTableComponent } from './documents-table.component';

/** The rail shows one thing at a time (data-model section 5). */
type RailMode = 'none' | 'detail' | 'form';

@Component({
  selector: 'app-documents',
  imports: [
    ConfirmDialogComponent,
    DocumentDetailRailComponent,
    DocumentFormComponent,
    DocumentsTableComponent,
    EmptyStateComponent,
    ErrorMessageComponent,
    IconComponent,
  ],
  templateUrl: './documents.component.html',
  styleUrl: './documents.component.scss',
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
  readonly creating = signal(false);

  readonly isEditing = computed(() => this.editingId() !== null);

  /**
   * Inspecting and editing share one region, so they are modes of it rather
   * than independent panels: before this, the form sat above the list and
   * pushed it off screen the moment it opened (FR-017).
   */
  readonly railMode = computed<RailMode>(() => {
    if (this.creating() || this.isEditing()) {
      return 'form';
    }
    return this.selected() ? 'detail' : 'none';
  });

  // -- narrowing and paging ----------------------------------------------------------
  readonly filters = signal<DocumentFilters>({});
  readonly page = signal(1);
  readonly total = signal(0);
  readonly hasNext = signal(false);
  readonly hasPrevious = signal(false);
  /** Learned from the first full page; the last one is short by definition. */
  private readonly pageSize = signal(0);

  readonly hasFilters = computed(() => Object.values(this.filters()).some(Boolean));

  readonly range = computed(() => {
    const shown = this.items().length;
    if (shown === 0) {
      return '';
    }
    const first = (this.page() - 1) * (this.pageSize() || shown) + 1;
    return `${first}–${first + shown - 1} de ${this.total()}`;
  });

  readonly providerStatuses: ProviderStatus[] = ['pending_integration', 'submitted', 'failed'];

  /** Signature values are the provider's, so the options come from the data we hold. */
  readonly signatureOptions = computed(() =>
    [...new Set(this.items().map((item) => item.status).filter((s): s is string => !!s))].sort(),
  );

  readonly companyNames = computed(() =>
    Object.fromEntries(this.companyOptions().map((c) => [c.id, c.name])),
  );

  // -- destructive actions -----------------------------------------------------------
  private readonly confirmDialog = viewChild(ConfirmDialogComponent);
  readonly pendingRemoval = signal<Document | null>(null);

  readonly form = this.fb.nonNullable.group({
    company: ['', Validators.required],
    name: ['', [Validators.required, Validators.maxLength(255)]],
    pdf_url: ['', [Validators.required]],
    external_id: [''],
    signers: this.fb.array<SignerForm>([this.signerRow()]),
  });

  /** Passed to `app-signer-rows` so it can append rows of the right shape. */
  readonly makeRow = (): SignerForm => this.signerRow();

  /** The retry rule belongs to the page; the table only asks whether it applies. */
  readonly canResyncFn = (document: Document): boolean => this.canResync(document);

  ngOnInit(): void {
    this.reload();
    this.companies.list().subscribe({
      next: (page) => this.companyOptions.set(page.results),
      error: (err: ApiError) => this.error.set(err),
    });
  }

  reload(): void {
    this.loading.set(true);
    this.documents.list({ ...this.filters(), page: this.page() > 1 ? this.page() : undefined })
      .subscribe({
        next: (page) => {
          this.items.set(page.results);
          this.total.set(page.count);
          this.hasNext.set(!!page.next);
          this.hasPrevious.set(!!page.previous);
          this.pageSize.update((size) => Math.max(size, page.results.length));
          this.loading.set(false);
        },
        error: (err: ApiError) => this.fail(err),
      });
  }

  applyFilter(key: keyof DocumentFilters, value: string): void {
    this.filters.update((current) => ({ ...current, [key]: value || undefined }));
    this.page.set(1);
    this.reload();
  }

  clearFilters(): void {
    this.filters.set({});
    this.page.set(1);
    this.reload();
  }

  goToPage(delta: number): void {
    this.page.update((current) => Math.max(1, current + delta));
    this.reload();
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
          this.total.update((count) => count + 1);
          this.resetForm();
        },
        error: (err: ApiError) => this.error.set(err),
      });
  }

  startCreate(): void {
    this.selected.set(null);
    this.editingId.set(null);
    this.creating.set(true);
  }

  edit(document: Document): void {
    this.editingId.set(document.id);
    this.creating.set(false);
    this.selected.set(null);
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
    this.creating.set(false);
    this.editingId.set(null);
    this.selected.set(document);
  }

  closeRail(): void {
    this.selected.set(null);
  }

  /**
   * The UI path to deletion. `remove` still deletes, so the question is asked
   * here rather than inside it — destroying a record should never be a single
   * unguarded click (FR-019).
   */
  askRemove(document: Document): void {
    this.pendingRemoval.set(document);
    this.confirmDialog()?.open();
  }

  confirmRemoval(): void {
    const document = this.pendingRemoval();
    this.pendingRemoval.set(null);
    if (document) {
      this.remove(document);
    }
  }

  remove(document: Document): void {
    this.error.set(null);
    this.documents.remove(document.id).subscribe({
      next: () => {
        this.items.update((items) => items.filter((i) => i.id !== document.id));
        this.total.update((count) => Math.max(0, count - 1));
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
    this.creating.set(false);
    this.signers.clear();
    this.signers.push(this.signerRow());
    this.form.patchValue({ company: '', name: '', pdf_url: '', external_id: '' });
  }

  private fail(err: ApiError): void {
    this.error.set(err);
    this.loading.set(false);
  }
}
