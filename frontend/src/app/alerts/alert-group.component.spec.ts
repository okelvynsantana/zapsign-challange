import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';

import { Alert } from '../core/models/alert.model';
import { AlertGroupComponent } from './alert-group.component';

const alert: Alert = {
  type: 'risk',
  document_id: 'd2',
  document_name: 'Contrato arriscado',
  detail: 'Multa desproporcional.',
  since: '2026-09-03T10:00:00Z',
};

describe('AlertGroupComponent', () => {
  let fixture: ComponentFixture<AlertGroupComponent>;

  const render = (alerts: Alert[], tone: 'neutral' | 'risk' = 'neutral'): void => {
    fixture.componentRef.setInput('title', 'Achados de risco');
    fixture.componentRef.setInput('icon', 'risk');
    fixture.componentRef.setInput('listTestId', 'alerts-risk');
    fixture.componentRef.setInput('hint', 'Apontados na análise mais recente.');
    fixture.componentRef.setInput('alerts', alerts);
    fixture.componentRef.setInput('count', alerts.length);
    fixture.componentRef.setInput('tone', tone);
    fixture.detectChanges();
  };

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [AlertGroupComponent],
      providers: [provideRouter([])],
    }).compileComponents();

    fixture = TestBed.createComponent(AlertGroupComponent);
  });

  it('renders each alert as a named link, its detail and an action', () => {
    render([alert]);

    const item = fixture.nativeElement.querySelector('[data-testid="alerts-risk"] li');
    expect(item.querySelector('a').textContent).toContain('Contrato arriscado');
    expect(item.textContent).toContain('Multa desproporcional.');
    expect(item.querySelector('.grp__go').getAttribute('aria-label')).toBe(
      'Abrir Contrato arriscado',
    );
  });

  it('names the group for assistive technology and states its count', () => {
    render([alert]);

    const section = fixture.nativeElement.querySelector('section');
    expect(section.getAttribute('aria-label')).toBe('Achados de risco');
    expect(section.querySelector('.grp__count').textContent.trim()).toBe('1');
  });

  it('drops the list, not the group, when it holds nothing', () => {
    render([]);

    expect(fixture.nativeElement.querySelector('[data-testid="alerts-risk"]')).toBeNull();
    expect(fixture.nativeElement.textContent).toContain('Nenhum.');
    expect(fixture.nativeElement.querySelector('section')).not.toBeNull();
  });

  it('marks a risk group apart from a neutral one', () => {
    render([alert], 'risk');
    expect(fixture.nativeElement.querySelector('section').classList).toContain('grp--risk');

    render([alert], 'neutral');
    expect(fixture.nativeElement.querySelector('section').classList).not.toContain('grp--risk');
  });
});
