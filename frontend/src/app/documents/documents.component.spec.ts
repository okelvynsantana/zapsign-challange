import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { ComponentFixture, TestBed } from '@angular/core/testing';

import { Document } from '../core/models/document.model';
import { DocumentsComponent } from './documents.component';

const doc = (overrides: Partial<Document> = {}): Document => ({
  id: 'd1',
  company: 'c1',
  name: 'Contrato X',
  pdf_url: 'https://files.example.test/x.pdf',
  external_id: null,
  provider_status: 'submitted',
  status: 'pending',
  open_id: 123456,
  token: 'zapsign-doc-token',
  created_by: 'manager',
  last_provider_error: null,
  signers: [
    {
      id: 's1',
      document: 'd1',
      name: 'Ana Souza',
      email: 'ana@example.com',
      token: 'signer-token',
      status: 'new',
      external_id: null,
    },
  ],
  latest_analysis: null,
  created_at: '2026-09-03T10:00:00Z',
  last_updated_at: '2026-09-03T10:00:00Z',
  ...overrides,
});

describe('DocumentsComponent', () => {
  let fixture: ComponentFixture<DocumentsComponent>;
  let http: HttpTestingController;

  const flushInitial = (documents: Document[] = []): void => {
    http
      .expectOne((r) => r.method === 'GET' && r.url.endsWith('/documents/'))
      .flush({ count: documents.length, next: null, previous: null, results: documents });
    http
      .expectOne((r) => r.method === 'GET' && r.url.endsWith('/companies/'))
      .flush({ count: 0, next: null, previous: null, results: [] });
    fixture.detectChanges();
  };

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [DocumentsComponent],
      providers: [provideHttpClient(), provideHttpClientTesting()],
    }).compileComponents();

    fixture = TestBed.createComponent(DocumentsComponent);
    http = TestBed.inject(HttpTestingController);
    fixture.detectChanges();
  });

  afterEach(() => http.verify());

  it('requires a company, a name, a PDF link and one complete signer', () => {
    flushInitial();
    const component = fixture.componentInstance;

    expect(component.form.invalid).toBe(true);

    component.form.patchValue({
      company: 'c1',
      name: 'Contrato X',
      pdf_url: 'https://files.example.test/x.pdf',
    });
    expect(component.form.invalid).toBe(true); // the signer row is still empty

    component.signers.at(0).setValue({ name: 'Ana', email: 'ana@example.com' });
    expect(component.form.valid).toBe(true);
  });

  it('always keeps at least one signer row', () => {
    flushInitial();

    expect(fixture.componentInstance.signers.length).toBe(1);
    fixture.componentInstance.signers.removeAt(0);
    fixture.componentInstance.signers.push(
      fixture.componentInstance.makeRow(),
    );
    expect(fixture.componentInstance.signers.length).toBe(1);
  });

  it('adds the created document to the list without re-fetching', () => {
    flushInitial();
    const component = fixture.componentInstance;
    component.form.patchValue({
      company: 'c1',
      name: 'Contrato X',
      pdf_url: 'https://files.example.test/x.pdf',
    });
    component.signers.at(0).setValue({ name: 'Ana Souza', email: 'ana@example.com' });

    component.submit();

    const request = http.expectOne((r) => r.method === 'POST' && r.url.endsWith('/documents/'));
    expect(request.request.body.signers).toEqual([
      { name: 'Ana Souza', email: 'ana@example.com' },
    ]);
    request.flush(doc());
    fixture.detectChanges();

    expect(component.items()).toHaveLength(1);
    expect(
      fixture.nativeElement.querySelector('[data-testid="document-list"]').textContent,
    ).toContain('Contrato X');
  });

  it('shows a failed hand-off with its reason and offers a resync', () => {
    flushInitial([
      doc({ provider_status: 'failed', last_provider_error: '[timeout] ZapSign too slow' }),
    ]);

    const list = fixture.nativeElement.querySelector('[data-testid="document-list"]');
    expect(list.textContent).toContain('failed');
    expect(
      fixture.nativeElement.querySelector('[data-testid="document-error"]').textContent,
    ).toContain('timeout');
    expect(fixture.nativeElement.querySelector('[data-testid="document-resync"]')).not.toBeNull();
  });

  it('hides resync while an attempt is still in flight', () => {
    flushInitial([doc({ provider_status: 'pending_integration' })]);

    expect(fixture.nativeElement.querySelector('[data-testid="document-resync"]')).toBeNull();
  });

  it('replaces the row in place after a successful resync', () => {
    flushInitial([doc({ provider_status: 'failed' })]);

    fixture.componentInstance.resync(doc({ provider_status: 'failed' }));
    http
      .expectOne((r) => r.method === 'POST' && r.url.endsWith('/documents/d1/resync/'))
      .flush(doc({ provider_status: 'submitted', status: 'pending' }));
    fixture.detectChanges();

    expect(fixture.componentInstance.items()[0].provider_status).toBe('submitted');
  });

  it('drops a deleted document from the list', () => {
    flushInitial([doc()]);

    fixture.componentInstance.remove(doc());
    http.expectOne((r) => r.method === 'DELETE').flush(null, { status: 204, statusText: 'No Content' });
    fixture.detectChanges();

    expect(fixture.componentInstance.items()).toHaveLength(0);
    expect(fixture.nativeElement.querySelector('[data-testid="document-empty"]')).not.toBeNull();
  });

  it('shows the provider identifiers on the detail panel', () => {
    flushInitial([doc()]);

    fixture.componentInstance.select(doc());
    fixture.detectChanges();

    const detail = fixture.nativeElement.querySelector('[data-testid="document-detail"]');
    expect(detail.textContent).toContain('123456');
    expect(detail.textContent).toContain('zapsign-doc-token');
    expect(detail.textContent).toContain('ana@example.com');
  });
});
