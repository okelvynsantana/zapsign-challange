import { Component } from '@angular/core';
import { TestBed } from '@angular/core/testing';

/**
 * Smoke test for the Jest + jest-preset-angular harness: proves the Angular
 * TestBed environment is initialised by `src/test/setup.ts` and that component
 * templates are compiled by the transformer.
 */
@Component({
  selector: 'app-harness-probe',
  standalone: true,
  template: '<span data-testid="probe">{{ label }}</span>',
})
class HarnessProbeComponent {
  label = 'ok';
}

describe('jest harness', () => {
  it('renders a standalone component through the TestBed', async () => {
    await TestBed.configureTestingModule({
      imports: [HarnessProbeComponent],
    }).compileComponents();

    const fixture = TestBed.createComponent(HarnessProbeComponent);
    fixture.detectChanges();

    const probe: HTMLElement | null =
      fixture.nativeElement.querySelector('[data-testid="probe"]');
    expect(probe?.textContent).toBe('ok');
  });
});
