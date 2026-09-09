import { ComponentFixture, TestBed } from '@angular/core/testing';
import { By } from '@angular/platform-browser';

import { ProviderStatus } from '../../core/models/document.model';
import { IconComponent } from '../atoms/icon.component';
import { ProviderStatusBadgeComponent } from './provider-status-badge.component';

describe('ProviderStatusBadgeComponent', () => {
  let fixture: ComponentFixture<ProviderStatusBadgeComponent>;

  const render = (status: string): HTMLElement => {
    fixture.componentRef.setInput('status', status);
    fixture.detectChanges();
    return fixture.nativeElement.querySelector('.badge');
  };

  const iconName = (): string | undefined =>
    fixture.debugElement.query(By.directive(IconComponent))?.componentInstance.name();

  beforeEach(async () => {
    await TestBed.configureTestingModule({ imports: [ProviderStatusBadgeComponent] }).compileComponents();
    fixture = TestBed.createComponent(ProviderStatusBadgeComponent);
  });

  // The hand-off scale is the only one drawn as a badge, and each value must be
  // distinguishable without reading the label (data-model section 1).
  const cases: [ProviderStatus, string, string][] = [
    ['pending_integration', 'badge--pending', 'dashed-circle'],
    ['submitted', 'badge--ok', 'check'],
    ['failed', 'badge--bad', 'cross'],
  ];

  it.each(cases)('renders %s with its own mark and its verbatim label', (status, modifier, icon) => {
    const badge = render(status);

    expect(badge).not.toBeNull();
    expect(badge.classList).toContain('badge');
    expect(badge.classList).toContain(modifier);
    expect(iconName()).toBe(icon);
    expect(badge.textContent).toContain(status);
  });

  it('gives each value a mark and a modifier no other value uses', () => {
    const seen = cases.map(([status]) => {
      const badge = render(status);
      return { modifiers: [...badge.classList].filter((c) => c.startsWith('badge--')), icon: iconName() };
    });

    expect(new Set(seen.map((s) => s.icon)).size).toBe(cases.length);
    expect(new Set(seen.map((s) => s.modifiers.join(' '))).size).toBe(cases.length);
  });

  it('falls back to the muted family for an unexpected value, still verbatim', () => {
    const badge = render('teleported');

    expect(badge.classList).toContain('badge--pending');
    expect(badge.textContent).toContain('teleported');
  });
});
