import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { provideHttpClient } from '@angular/common/http';
import { ComponentFixture, TestBed } from '@angular/core/testing';

import { Company } from '../core/models/company.model';
import { CompaniesComponent } from './companies.component';

const company = (overrides: Partial<Company> = {}): Company => ({
  id: 'c1',
  name: 'Acme Ltda',
  api_token_masked: '••••••3f9a',
  created_at: '2026-09-03T10:00:00Z',
  last_updated_at: '2026-09-03T10:00:00Z',
  ...overrides,
});

describe('CompaniesComponent', () => {
  let fixture: ComponentFixture<CompaniesComponent>;
  let http: HttpTestingController;

  const flushInitialList = (results: Company[] = []): void => {
    http.expectOne((r) => r.url.endsWith('/companies/') && r.method === 'GET').flush({
      count: results.length,
      next: null,
      previous: null,
      results,
    });
    fixture.detectChanges();
  };

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [CompaniesComponent],
      providers: [provideHttpClient(), provideHttpClientTesting()],
    }).compileComponents();

    fixture = TestBed.createComponent(CompaniesComponent);
    http = TestBed.inject(HttpTestingController);
    fixture.detectChanges();
  });

  afterEach(() => http.verify());

  it('shows an empty state when there is no organization yet', () => {
    flushInitialList();

    const empty = fixture.nativeElement.querySelector('[data-testid="company-empty"]');
    expect(empty).not.toBeNull();
  });

  it('renders only the masked credential, never the raw token', () => {
    flushInitialList([company()]);

    const list = fixture.nativeElement.querySelector('[data-testid="company-list"]');
    expect(list.textContent).toContain('••••••3f9a');
    expect(list.textContent).not.toContain('zapsign');
  });

  it('requires a name and a token before the form can be submitted', () => {
    flushInitialList();

    expect(fixture.componentInstance.form.invalid).toBe(true);
    fixture.componentInstance.form.setValue({ name: 'Acme', api_token: 'tok' });
    expect(fixture.componentInstance.form.valid).toBe(true);
  });

  it('adds the created company to the list without re-fetching it', () => {
    flushInitialList();

    fixture.componentInstance.form.setValue({ name: 'Acme Ltda', api_token: 'tok-3f9a' });
    fixture.componentInstance.submit();

    const request = http.expectOne((r) => r.method === 'POST' && r.url.endsWith('/companies/'));
    expect(request.request.body).toEqual({ name: 'Acme Ltda', api_token: 'tok-3f9a' });
    request.flush(company());
    fixture.detectChanges();

    // No second GET: the list updated in place (FR-012, SC-004).
    expect(fixture.componentInstance.items()).toHaveLength(1);
    expect(
      fixture.nativeElement.querySelector('[data-testid="company-list"]').textContent,
    ).toContain('Acme Ltda');
  });

  it('omits the token when editing without typing a new one', () => {
    flushInitialList([company()]);

    fixture.componentInstance.edit(company());
    fixture.componentInstance.form.patchValue({ name: 'Acme S.A.' });
    fixture.componentInstance.submit();

    const request = http.expectOne((r) => r.method === 'PATCH');
    expect(request.request.body).toEqual({ name: 'Acme S.A.' });
    request.flush(company({ name: 'Acme S.A.' }));
    fixture.detectChanges();

    expect(fixture.componentInstance.items()[0].name).toBe('Acme S.A.');
  });

  it('drops a deleted company from the list', () => {
    flushInitialList([company()]);

    fixture.componentInstance.remove(company());
    http.expectOne((r) => r.method === 'DELETE').flush(null, { status: 204, statusText: 'No Content' });
    fixture.detectChanges();

    expect(fixture.componentInstance.items()).toHaveLength(0);
  });

  it('surfaces the 409 returned when the organization still has documents', () => {
    flushInitialList([company()]);

    fixture.componentInstance.remove(company());
    http.expectOne((r) => r.method === 'DELETE').flush(
      { detail: 'This organization still has documents.', code: 'company_has_documents' },
      { status: 409, statusText: 'Conflict' },
    );
    fixture.detectChanges();

    expect(fixture.componentInstance.error()?.code).toBe('company_has_documents');
    expect(fixture.nativeElement.textContent).toContain('still has documents');
  });
});
