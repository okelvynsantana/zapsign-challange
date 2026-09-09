import { ComponentFixture, TestBed } from '@angular/core/testing';
import { By } from '@angular/platform-browser';

import { DocumentAnalysis, Insight } from '../../core/models/analysis.model';
import { IconComponent } from '../atoms/icon.component';
import { AnalysisMarkerComponent } from './analysis-marker.component';

const analysis = (state: 'succeeded' | 'failed', insights: Insight[] = []): DocumentAnalysis => ({
  id: 'a1',
  state,
  summary: '',
  missing_topics: [],
  insights,
  source: 'llm',
  model: null,
  error_reason: state === 'failed' ? 'timeout' : null,
  created_at: '2026-01-01T00:00:00Z',
});

const risky = (n: number): Insight[] =>
  Array.from({ length: n }, (_, i) => ({ text: `finding ${i}`, risk: true }));

describe('AnalysisMarkerComponent', () => {
  let fixture: ComponentFixture<AnalysisMarkerComponent>;

  const render = (value: DocumentAnalysis | null): HTMLElement => {
    fixture.componentRef.setInput('analysis', value);
    fixture.detectChanges();
    return fixture.nativeElement.querySelector('.mark');
  };

  const iconName = (): string | undefined =>
    fixture.debugElement.query(By.directive(IconComponent))?.componentInstance.name();

  beforeEach(async () => {
    await TestBed.configureTestingModule({ imports: [AnalysisMarkerComponent] }).compileComponents();
    fixture = TestBed.createComponent(AnalysisMarkerComponent);
  });

  it('counts only the insights flagged as a risk', () => {
    const mark = render(analysis('succeeded', [...risky(2), { text: 'fine', risk: false }]));

    expect(mark.classList).toContain('mark--risk');
    expect(iconName()).toBe('risk');
    expect(mark.textContent).toContain('2 riscos');
  });

  it('says risco in the singular for one risk', () => {
    expect(render(analysis('succeeded', risky(1))).textContent).toContain('1 risco');
    expect(fixture.nativeElement.textContent).not.toContain('riscos');
  });

  it.each([[[]], [[{ text: 'fine', risk: false }]]])(
    'reads sem risco when nothing is flagged',
    (insights: Insight[]) => {
      const mark = render(analysis('succeeded', insights));

      expect(mark.classList).not.toContain('mark--risk');
      expect(iconName()).toBe('check-circle');
      expect(mark.textContent).toContain('sem risco');
      expect(mark.getAttribute('data-testid')).toBeNull();
    },
  );

  it('reads falhou when the run itself failed', () => {
    const mark = render(analysis('failed', risky(3)));

    expect(mark.classList).toContain('mark--failed');
    expect(iconName()).toBe('alert');
    expect(mark.textContent).toContain('falhou');
    expect(mark.getAttribute('data-testid')).toBeNull();
  });

  it('renders the never-analysed form for null', () => {
    const mark = render(null);

    expect(mark.classList).toContain('mark--none');
    expect(mark.textContent?.trim()).toBe('—');
    expect(fixture.debugElement.query(By.directive(IconComponent))).toBeNull();
  });

  // The core guarantee (FR-008): a finding about the contract and a defect in
  // our processing must never be mistaken for one another.
  it('gives a risk and a failure neither the same mark nor the same colour family', () => {
    const read = (value: DocumentAnalysis) => {
      const mark = render(value);
      return {
        modifiers: [...mark.classList].filter((c) => c.startsWith('mark--')),
        icon: iconName(),
        text: mark.textContent?.trim(),
      };
    };

    const risk = read(analysis('succeeded', risky(1)));
    const failed = read(analysis('failed'));

    expect(risk.icon).not.toBe(failed.icon);
    expect(risk.modifiers).not.toHaveLength(0);
    expect(failed.modifiers).not.toHaveLength(0);
    expect(risk.modifiers.filter((c) => failed.modifiers.includes(c))).toEqual([]);
    expect(risk.text).not.toBe(failed.text);
  });
});
