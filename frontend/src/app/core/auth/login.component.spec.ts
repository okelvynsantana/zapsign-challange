import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { Router, provideRouter } from '@angular/router';

import { LoginComponent } from './login.component';

describe('LoginComponent', () => {
  let fixture: ComponentFixture<LoginComponent>;
  let backend: HttpTestingController;

  beforeEach(async () => {
    localStorage.clear();
    await TestBed.configureTestingModule({
      imports: [LoginComponent],
      providers: [provideHttpClient(), provideHttpClientTesting(), provideRouter([])],
    }).compileComponents();

    fixture = TestBed.createComponent(LoginComponent);
    backend = TestBed.inject(HttpTestingController);
    fixture.detectChanges();
  });

  afterEach(() => backend.verify());

  it('requires both fields before it will submit', () => {
    expect(fixture.componentInstance.form.invalid).toBe(true);

    fixture.componentInstance.submit();
    backend.expectNone(() => true);
  });

  it('navigates to the documents view on success', () => {
    const navigate = jest.spyOn(TestBed.inject(Router), 'navigate').mockResolvedValue(true);
    fixture.componentInstance.form.setValue({ username: 'manager', password: 'secret' });

    fixture.componentInstance.submit();
    backend.expectOne((r) => r.url.endsWith('/auth/token/')).flush({ access: 'a', refresh: 'r' });

    expect(navigate).toHaveBeenCalledWith(['/documents']);
    expect(fixture.componentInstance.pending()).toBe(false);
  });

  it('shows the rejection message and stops pending on failure', () => {
    fixture.componentInstance.form.setValue({ username: 'manager', password: 'wrong' });

    fixture.componentInstance.submit();
    backend
      .expectOne((r) => r.url.endsWith('/auth/token/'))
      .flush(
        { detail: 'No active account found with the given credentials', code: 'invalid_credentials' },
        { status: 401, statusText: 'Unauthorized' },
      );
    fixture.detectChanges();

    expect(fixture.componentInstance.pending()).toBe(false);
    expect(fixture.nativeElement.textContent).toContain('No active account');
  });
});
