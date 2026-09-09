import { Component, signal } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';

import { DocumentAnalysis } from '../../core/models/analysis.model';
import { AnalysisRunItemComponent } from './analysis-run-item.component';

const run = (overrides: Partial<DocumentAnalysis> = {}): DocumentAnalysis => ({
  id: 'a1',
  state: 'succeeded',
  summary: 'Resumo.',
  missing_topics: [],
  insights: [],
  source: 'llm+regex',
  model: 'gpt-4o-mini',
  error_reason: null,
  created_at: '2025-03-09T14:07:00Z',
  ...overrides,
});

@Component({
  imports: [AnalysisRunItemComponent],
  template: `<app-analysis-run-item [run]="analysis()" [current]="current()" />`,
})
class HostComponent {
  readonly analysis = signal<DocumentAnalysis>(run());
  readonly current = signal(false);
}

describe('AnalysisRunItemComponent', () => {
  let fixture: ComponentFixture<HostComponent>;

  const text = (): string => fixture.nativeElement.textContent;
  const badge = (): HTMLElement => fixture.nativeElement.querySelector('.badge');

  beforeEach(async () => {
    await TestBed.configureTestingModule({ imports: [HostComponent] }).compileComponents();
    fixture = TestBed.createComponent(HostComponent);
    fixture.detectChanges();
  });

  it('shows the state and the source in the backend’s own words', () => {
    expect(badge().textContent?.trim()).toBe('succeeded');
    expect(text()).toContain('llm+regex');
  });

  it('gives a succeeded run the ok family and a failed run the bad family', () => {
    expect(badge().className).toContain('badge--ok');

    fixture.componentInstance.analysis.set(
      run({ state: 'failed', error_reason: 'timeout', source: 'regex' }),
    );
    fixture.detectChanges();

    expect(badge().textContent?.trim()).toBe('failed');
    expect(badge().className).toContain('badge--bad');
    expect(badge().className).not.toContain('badge--ok');
  });

  it('counts only the flagged insights of this run', () => {
    fixture.componentInstance.analysis.set(
      run({
        insights: [
          { text: 'Multa desproporcional.', risk: true },
          { text: 'Prazo de 30 dias.', risk: false },
          { text: 'Foro de eleição distante.', risk: true },
        ],
      }),
    );
    fixture.detectChanges();

    expect(text()).toContain('2 riscos');
  });

  it('keeps the count singular when there is one', () => {
    fixture.componentInstance.analysis.set(
      run({ insights: [{ text: 'Multa desproporcional.', risk: true }] }),
    );
    fixture.detectChanges();

    expect(text()).toContain('1 risco');
    expect(text()).not.toContain('1 riscos');
  });

  it('renders the timestamp as a day and time, never the raw ISO string', () => {
    expect(text()).toMatch(/\d{2}\/\d{2} \d{2}:\d{2}/);
    expect(text()).not.toContain('2025-03-09T14:07:00Z');
  });

  it('marks the run the panel is showing', () => {
    expect(fixture.nativeElement.querySelector('.eyebrow')).toBeNull();

    fixture.componentInstance.current.set(true);
    fixture.detectChanges();

    expect(fixture.nativeElement.querySelector('.eyebrow').textContent.trim()).toBe('atual');
  });
});
