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

const failedRun = (reason: string): DocumentAnalysis =>
  analysis({ state: 'failed', summary: '', insights: [], missing_topics: [], error_reason: reason });

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

  const el = (testid: string): HTMLElement | null =>
    fixture.nativeElement.querySelector(`[data-testid="${testid}"]`);
  const all = (selector: string): HTMLElement[] =>
    Array.from(fixture.nativeElement.querySelectorAll(selector));
  const action = (): HTMLButtonElement => el('analysis-run') as HTMLButtonElement;

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
    expect(el('analysis-latest')!.textContent).toContain('prestação de serviços');
    expect(all('[data-testid="analysis-missing"] li')).toHaveLength(2);
    expect(all('[data-testid="analysis-insights"] app-insight-item')).toHaveLength(2);
  });

  it('flags risk insights', () => {
    expect(all('[data-testid="analysis-risk"]')).toHaveLength(1);
  });

  it('names how the analysis was produced', () => {
    expect(fixture.nativeElement.textContent).toContain('llm+regex');
    expect(fixture.nativeElement.textContent).toContain('gpt-4o-mini');
  });

  it('shows a failed run as retryable and says the document is unaffected', () => {
    fixture.componentInstance.document.set(doc(failedRun('no_text')));
    fixture.detectChanges();

    const failed = el('analysis-failed')!;
    expect(failed.textContent).toContain('no_text');
    expect(failed.textContent).toContain('não foram afetados');
    expect(el('analysis-latest')).toBeNull();
  });

  it('shows an empty state before the first run', () => {
    fixture.componentInstance.document.set(doc(null));
    fixture.detectChanges();

    expect(el('analysis-empty')).not.toBeNull();
  });

  it('re-analyzing posts once and notifies the parent', () => {
    action().click();

    const request = http.expectOne(
      (r) => r.method === 'POST' && r.url.endsWith('/documents/d1/analyze/'),
    );
    request.flush(analysis({ id: 'a2' }));
    fixture.detectChanges();

    expect(fixture.componentInstance.analyzedCount).toBe(1);
  });

  it('loads the history only when it is opened', () => {
    el('analysis-history-toggle')!.click();
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

    expect(all('[data-testid="analysis-history"] app-analysis-run-item')).toHaveLength(2);
  });

  // --- the four states (data-model §4, FR-010) -----------------------------

  describe('state resolution', () => {
    it('resolves never-run from a null latest_analysis', () => {
      fixture.componentInstance.document.set(doc(null));
      fixture.detectChanges();

      expect(el('analysis-empty')).not.toBeNull();
      expect(el('analysis-latest')).toBeNull();
      expect(el('analysis-failed')).toBeNull();
      expect(el('analysis-progress')).toBeNull();
      expect(action().textContent).toContain('Analisar agora');
    });

    it('resolves in-progress from the in-flight flag, whatever the stored run says', () => {
      action().click();
      fixture.detectChanges();

      // The succeeded run is still on the document, but the request in flight
      // is the news — the panel must not read as idle.
      expect(el('analysis-progress')).not.toBeNull();
      expect(el('analysis-latest')).toBeNull();
      expect(action().disabled).toBe(true);

      http.expectOne((r) => r.method === 'POST').flush(analysis({ id: 'a2' }));
    });

    it('states the 15 s ceiling while the analysis runs, so it never looks frozen', () => {
      action().click();
      fixture.detectChanges();

      const progress = el('analysis-progress')!;
      expect(progress.textContent).toContain('15 s');
      expect(progress.textContent).toContain('AI_TIMEOUT_SECONDS');

      http.expectOne((r) => r.method === 'POST').flush(analysis({ id: 'a2' }));
    });

    it('resolves produced from a succeeded latest run, with re-running as a secondary action', () => {
      expect(el('analysis-latest')).not.toBeNull();
      expect(el('analysis-failed')).toBeNull();
      expect(action().textContent).toContain('Reanalisar');
      expect(action().classList).not.toContain('btn--primary');
    });

    it('resolves failed from a failed latest run and makes the retry the primary action', () => {
      fixture.componentInstance.document.set(doc(failedRun('timeout')));
      fixture.detectChanges();

      expect(el('analysis-failed')).not.toBeNull();
      expect(el('analysis-latest')).toBeNull();
      expect(action().classList).toContain('btn--primary');
    });
  });

  // --- failure reporting (FR-009) ------------------------------------------

  describe('failure reporting', () => {
    it('keeps the recorded reason verbatim in mono', () => {
      fixture.componentInstance.document.set(doc(failedRun('no_text')));
      fixture.detectChanges();

      const verbatim = all('[data-testid="analysis-failed"] .mono').map((n) => n.textContent);
      expect(verbatim.some((text) => text === 'no_text')).toBe(true);
      // The state value is the backend's own word and is never translated.
      expect(el('analysis-failed')!.querySelector('.badge--bad')!.textContent).toBe('failed');
    });

    it.each([
      ['unreachable', 'não pôde ser baixado'],
      ['not_pdf', 'não é um PDF'],
      ['too_large', 'limite de tamanho'],
      ['no_text', 'camada de texto'],
      ['timeout', 'tempo limite'],
    ])('explains %s in plain Portuguese', (reason, explanation) => {
      fixture.componentInstance.document.set(doc(failedRun(reason)));
      fixture.detectChanges();

      const failed = el('analysis-failed')!;
      expect(failed.textContent).toContain(reason);
      expect(failed.textContent).toContain(explanation);
    });

    it('stays readable when the backend records a reason we do not know yet', () => {
      fixture.componentInstance.document.set(doc(failedRun('quota_exhausted')));
      fixture.detectChanges();

      const failed = el('analysis-failed')!;
      expect(failed.textContent).toContain('quota_exhausted');
      expect(failed.textContent).toContain('não foram afetados');
    });
  });

  // --- history (FR-011) -----------------------------------------------------

  describe('history', () => {
    it('appends a retry rather than replacing the previous run', () => {
      el('analysis-history-toggle')!.click();
      fixture.detectChanges();
      http.expectOne((r) => r.method === 'GET').flush({
        count: 1,
        next: null,
        previous: null,
        results: [analysis({ id: 'a1' })],
      });
      fixture.detectChanges();

      action().click();
      http.expectOne((r) => r.method === 'POST').flush(analysis({ id: 'a2' }));
      fixture.detectChanges();

      const rows = all('[data-testid="analysis-history"] app-analysis-run-item');
      expect(rows).toHaveLength(2);
      expect(rows[0].textContent).toContain('succeeded');
    });

    it('marks the run the panel is currently showing', () => {
      el('analysis-history-toggle')!.click();
      fixture.detectChanges();
      http.expectOne((r) => r.method === 'GET').flush({
        count: 2,
        next: null,
        previous: null,
        results: [analysis({ id: 'a1' }), analysis({ id: 'a0' })],
      });
      fixture.detectChanges();

      const rows = all('[data-testid="analysis-history"] app-analysis-run-item');
      expect(rows[0].textContent).toContain('atual');
      expect(rows[1].textContent).not.toContain('atual');
    });

    it('hides again on a second toggle without re-fetching', () => {
      el('analysis-history-toggle')!.click();
      fixture.detectChanges();
      http.expectOne((r) => r.method === 'GET').flush({
        count: 0,
        next: null,
        previous: null,
        results: [],
      });
      fixture.detectChanges();

      el('analysis-history-toggle')!.click();
      fixture.detectChanges();

      expect(el('analysis-history')).toBeNull();
    });
  });

  it('presents the run date in the reader’s convention, not as stored (FR-021)', () => {
    const text = el('analysis-latest')!.textContent ?? '';

    expect(text).not.toContain('2026-09-03T12:00:00Z');
    expect(text).toMatch(/\d{2}\/\d{2}\/\d{4} \d{2}:\d{2}/);
  });
});
