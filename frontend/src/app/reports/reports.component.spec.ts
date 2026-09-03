import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { ComponentFixture, TestBed } from '@angular/core/testing';

import { SummaryReport } from '../core/models/report.model';
import { ReportsComponent } from './reports.component';

const summary = (overrides: Partial<SummaryReport> = {}): SummaryReport => ({
  total_documents: 3,
  by_provider_status: { pending_integration: 0, submitted: 2, failed: 1 },
  by_signature_status: { pending: 2, signed: 1 },
  documents_with_risk_insight: 1,
  recent_risk_insights: [
    {
      document_id: 'd1',
      name: 'Contrato X',
      text: 'Multa desproporcional.',
      created_at: '2026-09-03T12:00:00Z',
    },
  ],
  generated_at: '2026-09-03T12:00:00Z',
  ...overrides,
});

describe('ReportsComponent', () => {
  let fixture: ComponentFixture<ReportsComponent>;
  let http: HttpTestingController;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ReportsComponent],
      providers: [provideHttpClient(), provideHttpClientTesting()],
    }).compileComponents();

    fixture = TestBed.createComponent(ReportsComponent);
    http = TestBed.inject(HttpTestingController);
    fixture.detectChanges();
  });

  afterEach(() => http.verify());

  const flush = (report: SummaryReport): void => {
    http
      .expectOne((r) => r.method === 'GET' && r.url.endsWith('/reports/summary/'))
      .flush(report);
    fixture.detectChanges();
  };

  it('renders the totals and both status breakdowns', () => {
    flush(summary());

    expect(
      fixture.nativeElement.querySelector('[data-testid="report-total"]').textContent,
    ).toContain('3');
    expect(
      fixture.nativeElement.querySelectorAll('[data-testid="report-provider-status"] li'),
    ).toHaveLength(3);
    expect(
      fixture.nativeElement.querySelectorAll('[data-testid="report-signature-status"] li'),
    ).toHaveLength(2);
  });

  it('lists recent risk insights with their document', () => {
    flush(summary());

    const risks = fixture.nativeElement.querySelector('[data-testid="report-risk-insights"]');
    expect(risks.textContent).toContain('Contrato X');
    expect(risks.textContent).toContain('Multa desproporcional');
  });

  it('renders an empty dataset without erroring', () => {
    flush(
      summary({
        total_documents: 0,
        by_signature_status: {},
        documents_with_risk_insight: 0,
        recent_risk_insights: [],
      }),
    );

    expect(fixture.nativeElement.textContent).toContain('No documents yet.');
    expect(fixture.nativeElement.querySelector('[data-testid="report-risk-insights"]')).toBeNull();
    expect(fixture.componentInstance.error()).toBeNull();
  });

  it('surfaces a failure instead of the report', () => {
    http
      .expectOne((r) => r.url.endsWith('/reports/summary/'))
      .flush({ detail: 'nope', code: 'not_authenticated' }, { status: 401, statusText: 'x' });
    fixture.detectChanges();

    expect(fixture.componentInstance.error()?.code).toBe('not_authenticated');
  });
});
