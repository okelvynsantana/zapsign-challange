import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { ComponentFixture, TestBed } from '@angular/core/testing';

import { Alert } from '../core/models/alert.model';
import { AlertsComponent } from './alerts.component';

const stalled: Alert = {
  type: 'stalled',
  document_id: 'd1',
  document_name: 'Contrato parado',
  detail: 'pending 9 days',
  since: '2026-08-25T10:00:00Z',
};

const risk: Alert = {
  type: 'risk',
  document_id: 'd2',
  document_name: 'Contrato arriscado',
  detail: 'Multa desproporcional.',
  since: '2026-09-03T10:00:00Z',
};

describe('AlertsComponent', () => {
  let fixture: ComponentFixture<AlertsComponent>;
  let http: HttpTestingController;

  const flush = (alerts: Alert[]): void => {
    http.expectOne((r) => r.method === 'GET' && r.url.endsWith('/alerts/')).flush(alerts);
    fixture.detectChanges();
  };

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [AlertsComponent],
      providers: [provideHttpClient(), provideHttpClientTesting()],
    }).compileComponents();

    fixture = TestBed.createComponent(AlertsComponent);
    http = TestBed.inject(HttpTestingController);
    fixture.detectChanges();
  });

  afterEach(() => http.verify());

  it('groups alerts into stalled and risk', () => {
    flush([stalled, risk]);

    expect(fixture.nativeElement.querySelectorAll('[data-testid="alerts-stalled"] li')).toHaveLength(1);
    expect(fixture.nativeElement.querySelectorAll('[data-testid="alerts-risk"] li')).toHaveLength(1);
    expect(fixture.nativeElement.textContent).toContain('pending 9 days');
    expect(fixture.nativeElement.textContent).toContain('Multa desproporcional');
  });

  it('shows an empty state rather than an error when nothing matches', () => {
    flush([]);

    expect(fixture.nativeElement.querySelector('[data-testid="alerts-empty"]')).not.toBeNull();
    expect(fixture.componentInstance.error()).toBeNull();
  });

  it('says "None." for a category with no alerts', () => {
    flush([stalled]);

    expect(fixture.nativeElement.querySelector('[data-testid="alerts-risk"]')).toBeNull();
    expect(fixture.nativeElement.textContent).toContain('None.');
  });

  it('re-fetches on refresh', () => {
    flush([]);

    fixture.nativeElement.querySelector('[data-testid="alerts-refresh"]').click();
    flush([risk]);

    expect(fixture.componentInstance.items()).toHaveLength(1);
  });

  it('surfaces a failure', () => {
    http
      .expectOne((r) => r.url.endsWith('/alerts/'))
      .flush({ detail: 'nope', code: 'not_authenticated' }, { status: 401, statusText: 'x' });
    fixture.detectChanges();

    expect(fixture.componentInstance.error()?.code).toBe('not_authenticated');
  });
});
