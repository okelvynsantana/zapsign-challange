import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { Component, signal } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';

import { DocumentAnalysis } from '../core/models/analysis.model';
import { Document } from '../core/models/document.model';
import { AnalysisPanelComponent } from './analysis-panel.component';

const analysis = (overrides: Partial<DocumentAnalysis> = {}): DocumentAnalysis => ({
  id: 'a1',
  state: 'succeeded',
  summary: 'Contrato de prestação de serviços por 12 meses.',
  missing_topics: ['foro', 'confidencialidade'],
  insights: [
    { text: 'Multa desproporcional.', risk: true },
    { text: 'Prazo de pagamento claro.', risk: false },
  ],
  source: 'llm+regex',
  model: 'gpt-4o-mini',
  error_reason: null,
  created_at: '2026-09-03T12:00:00Z',
  ...overrides,
});

const doc = (latest: DocumentAnalysis | null): Document => ({
  id: 'd1',
  company: 'c1',
  name: 'Contrato X',
  pdf_url: 'https://files.example.test/x.pdf',
  external_id: null,
  provider_status: 'submitted',
  status: 'pending',
  open_id: 1,
  token: 't',
  created_by: 'manager',
  last_provider_error: null,
  signers: [],
  latest_analysis: latest,
  created_at: '2026-09-03T10:00:00Z',
  last_updated_at: '2026-09-03T10:00:00Z',
});

@Component({
  imports: [AnalysisPanelComponent],
  template: `<app-analysis-panel [document]="document()" (analyzed)="analyzedCount = analyzedCount + 1" />`,
})
class HostComponent {
  readonly document = signal<Document>(doc(analysis()));
  analyzedCount = 0;
}

describe('AnalysisPanelComponent', () => {
  let fixture: ComponentFixture<HostComponent>;
  let http: HttpTestingController;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [HostComponent],
      providers: [provideHttpClient(), provideHttpClientTesting()],
    }).compileComponents();

    fixture = TestBed.createComponent(HostComponent);
    http = TestBed.inject(HttpTestingController);
    fixture.detectChanges();
  });

  afterEach(() => http.verify());

  it('renders the summary, missing topics and insights of the latest run', () => {
    const panel = fixture.nativeElement.querySelector('[data-testid="analysis-latest"]');

    expect(panel.textContent).toContain('prestação de serviços');
    expect(
      fixture.nativeElement.querySelectorAll('[data-testid="analysis-missing"] li'),
    ).toHaveLength(2);
    expect(
      fixture.nativeElement.querySelectorAll('[data-testid="analysis-insights"] li'),
    ).toHaveLength(2);
  });

  it('flags risk insights', () => {
    expect(fixture.nativeElement.querySelectorAll('[data-testid="analysis-risk"]')).toHaveLength(1);
  });

  it('names how the analysis was produced', () => {
    expect(fixture.nativeElement.textContent).toContain('llm+regex');
    expect(fixture.nativeElement.textContent).toContain('gpt-4o-mini');
  });

  it('shows a failed run as retryable and says the document is unaffected', () => {
    fixture.componentInstance.document.set(
      doc(analysis({ state: 'failed', summary: '', error_reason: 'no_text' })),
    );
    fixture.detectChanges();

    const failed = fixture.nativeElement.querySelector('[data-testid="analysis-failed"]');
    expect(failed.textContent).toContain('no_text');
    expect(failed.textContent).toContain('document is unaffected');
    expect(fixture.nativeElement.querySelector('[data-testid="analysis-latest"]')).toBeNull();
  });

  it('shows an empty state before the first run', () => {
    fixture.componentInstance.document.set(doc(null));
    fixture.detectChanges();

    expect(fixture.nativeElement.querySelector('[data-testid="analysis-empty"]')).not.toBeNull();
  });

  it('re-analyzing posts once and notifies the parent', () => {
    fixture.nativeElement.querySelector('[data-testid="analysis-run"]').click();

    const request = http.expectOne(
      (r) => r.method === 'POST' && r.url.endsWith('/documents/d1/analyze/'),
    );
    request.flush(analysis({ id: 'a2' }));
    fixture.detectChanges();

    expect(fixture.componentInstance.analyzedCount).toBe(1);
  });

  it('loads the history only when it is opened', () => {
    fixture.nativeElement.querySelector('[data-testid="analysis-history-toggle"]').click();
    fixture.detectChanges();

    http
      .expectOne((r) => r.method === 'GET' && r.url.endsWith('/documents/d1/analyses/'))
      .flush({
        count: 2,
        next: null,
        previous: null,
        results: [analysis({ id: 'a2' }), analysis({ id: 'a1' })],
      });
    fixture.detectChanges();

    expect(
      fixture.nativeElement.querySelectorAll('[data-testid="analysis-history"] li'),
    ).toHaveLength(2);
  });
});
