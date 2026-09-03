/**
 * The typed API clients are thin, but they own the URLs and verbs the whole SPA depends on.
 * These assertions pin that contract against `contracts/rest-api.md`.
 */
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';

import { AlertService } from './alert.service';
import { CompanyService } from './company.service';
import { DocumentService } from './document.service';
import { ReportService } from './report.service';
import { SignerService } from './signer.service';

describe('API clients', () => {
  let backend: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    backend = TestBed.inject(HttpTestingController);
  });

  afterEach(() => backend.verify());

  const expectCall = (method: string, suffix: string): void => {
    const request = backend.expectOne((r) => r.method === method && r.url.endsWith(suffix));
    request.flush({});
  };

  it('CompanyService targets /companies/', () => {
    const companies = TestBed.inject(CompanyService);

    companies.list().subscribe();
    expectCall('GET', '/companies/');

    companies.create({ name: 'Acme', api_token: 't' }).subscribe();
    expectCall('POST', '/companies/');

    companies.update('c1', { name: 'Acme S.A.' }).subscribe();
    expectCall('PATCH', '/companies/c1/');

    companies.remove('c1').subscribe();
    expectCall('DELETE', '/companies/c1/');
  });

  it('DocumentService targets /documents/ and its actions', () => {
    const documents = TestBed.inject(DocumentService);

    documents.get('d1').subscribe();
    expectCall('GET', '/documents/d1/');

    documents.create({
      company: 'c1',
      name: 'x',
      pdf_url: 'https://e.test/x.pdf',
      signers: [{ name: 'A', email: 'a@e.test' }],
    }).subscribe();
    expectCall('POST', '/documents/');

    documents.update('d1', { name: 'y' }).subscribe();
    expectCall('PATCH', '/documents/d1/');

    documents.remove('d1').subscribe();
    expectCall('DELETE', '/documents/d1/');

    documents.resync('d1').subscribe();
    expectCall('POST', '/documents/d1/resync/');

    documents.analyze('d1').subscribe();
    expectCall('POST', '/documents/d1/analyze/');

    documents.analyses('d1').subscribe();
    expectCall('GET', '/documents/d1/analyses/');
  });

  it('DocumentService passes list filters through as query parameters', () => {
    TestBed.inject(DocumentService).list({ provider_status: 'failed', company: 'c1' }).subscribe();

    const request = backend.expectOne((r) => r.url.endsWith('/documents/'));
    expect(request.request.params.get('provider_status')).toBe('failed');
    expect(request.request.params.get('company')).toBe('c1');
    request.flush({});
  });

  it('SignerService targets /signers/ and filters by document', () => {
    const signers = TestBed.inject(SignerService);

    signers.listForDocument('d1').subscribe();
    const listed = backend.expectOne((r) => r.url.endsWith('/signers/'));
    expect(listed.request.params.get('document')).toBe('d1');
    listed.flush({});

    signers.create({ document: 'd1', name: 'A', email: 'a@e.test' }).subscribe();
    expectCall('POST', '/signers/');

    signers.update('s1', { name: 'B' }).subscribe();
    expectCall('PATCH', '/signers/s1/');

    signers.remove('s1').subscribe();
    expectCall('DELETE', '/signers/s1/');
  });

  it('ReportService targets both report endpoints', () => {
    const reports = TestBed.inject(ReportService);

    reports.summary().subscribe();
    expectCall('GET', '/reports/summary/');

    reports.forDocument('d1').subscribe();
    expectCall('GET', '/documents/d1/report/');
  });

  it('AlertService targets /alerts/', () => {
    TestBed.inject(AlertService).list().subscribe();
    expectCall('GET', '/alerts/');
  });
});
