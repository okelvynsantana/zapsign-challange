import { readFileSync } from 'node:fs';
import { join } from 'node:path';

import { Component, signal } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';

import { Insight } from '../../core/models/analysis.model';
import { InsightItemComponent } from './insight-item.component';

/* Geometry from `icon.component.ts`. Both marks carry a stem and a dot, so the
 * outline is what separates them: a triangle for `risk`, a circle for `alert`.
 * Matching on the outline pins which mark rendered, not merely that one did. */
const TRIANGLE_OUTLINE = 'M6 1.7 11 10.4H1z';
const ALERT_STEM = 'M6 3.6v2.8';

@Component({
  imports: [InsightItemComponent],
  template: `<app-insight-item [insight]="insight()" />`,
})
class HostComponent {
  readonly insight = signal<Insight>({ text: 'Cláusula de rescisão unilateral.', risk: false });
}

describe('InsightItemComponent', () => {
  let fixture: ComponentFixture<HostComponent>;

  const paths = (): string[] =>
    Array.from(fixture.nativeElement.querySelectorAll('svg path')).map((path) =>
      (path as SVGPathElement).getAttribute('d') ?? '',
    );

  beforeEach(async () => {
    await TestBed.configureTestingModule({ imports: [HostComponent] }).compileComponents();
    fixture = TestBed.createComponent(HostComponent);
    fixture.detectChanges();
  });

  describe('a flagged insight', () => {
    beforeEach(() => {
      fixture.componentInstance.insight.set({ text: 'Multa desproporcional.', risk: true });
      fixture.detectChanges();
    });

    it('labels it RISCO alongside the text', () => {
      const flag = fixture.nativeElement.querySelector('.insight__flag');

      expect(flag.textContent.trim()).toBe('RISCO');
      expect(fixture.nativeElement.textContent).toContain('Multa desproporcional.');
    });

    it('marks it with the risk triangle, not the alert circle', () => {
      expect(paths()).toContain(TRIANGLE_OUTLINE);
      expect(paths()).not.toContain(ALERT_STEM);
    });

    it('renders in the ochre family', () => {
      expect(fixture.nativeElement.querySelector('app-insight-item').className).toContain(
        'insight--risk',
      );
    });
  });

  describe('a plain insight', () => {
    beforeEach(() => {
      fixture.componentInstance.insight.set({ text: 'Prazo de 30 dias.', risk: false });
      fixture.detectChanges();
    });

    it('shows neither the RISCO label nor an icon', () => {
      expect(fixture.nativeElement.querySelector('.insight__flag')).toBeNull();
      expect(fixture.nativeElement.textContent).not.toContain('RISCO');
      expect(fixture.nativeElement.querySelector('app-icon')).toBeNull();
    });

    it('carries a dot and the text', () => {
      expect(fixture.nativeElement.querySelector('.insight__dot')).not.toBeNull();
      expect(fixture.nativeElement.textContent).toContain('Prazo de 30 dias.');
    });
  });

  // The rule this component exists to hold: a risk is a finding about the
  // contract, never a failure of ours (FR-008). jsdom resolves no custom
  // properties, so the guarantee is checked where it is actually written.
  it('never reaches for the failure family', () => {
    const source = readFileSync(join(__dirname, 'insight-item.component.ts'), 'utf8');

    expect(source).not.toMatch(/--bad-/);
    expect(source).not.toMatch(/name="alert"/);
  });
});
