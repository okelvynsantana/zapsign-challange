import { HttpClient, provideHttpClient, withInterceptors } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';

import { authInterceptor } from './auth.interceptor';
import { AuthService } from './auth.service';

describe('authInterceptor', () => {
  let http: HttpClient;
  let backend: HttpTestingController;

  beforeEach(() => {
    localStorage.clear();
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(withInterceptors([authInterceptor])),
        provideHttpClientTesting(),
      ],
    });
    http = TestBed.inject(HttpClient);
    backend = TestBed.inject(HttpTestingController);
  });

  afterEach(() => backend.verify());

  const signIn = (): void => {
    TestBed.inject(AuthService).login('manager', 'secret').subscribe();
    backend
      .expectOne((r) => r.url.endsWith('/auth/token/'))
      .flush({ access: 'access-token', refresh: 'refresh-token' });
  };

  it('sends no Authorization header while signed out', () => {
    http.get('/api/documents/').subscribe();

    const request = backend.expectOne('/api/documents/');
    expect(request.request.headers.has('Authorization')).toBe(false);
    request.flush({});
  });

  it('attaches the bearer token once signed in', () => {
    signIn();

    http.get('/api/documents/').subscribe();

    const request = backend.expectOne('/api/documents/');
    expect(request.request.headers.get('Authorization')).toBe('Bearer access-token');
    request.flush({});
  });

  it('never attaches a stale token to the token endpoint itself', () => {
    signIn();

    TestBed.inject(AuthService).login('manager', 'again').subscribe();

    const request = backend.expectOne((r) => r.url.endsWith('/auth/token/'));
    expect(request.request.headers.has('Authorization')).toBe(false);
    request.flush({ access: 'a', refresh: 'r' });
  });
});
