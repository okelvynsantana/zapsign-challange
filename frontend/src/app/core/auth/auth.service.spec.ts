import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';

import { AuthService } from './auth.service';
import { TokenStorageService } from './token-storage.service';

describe('AuthService', () => {
  let auth: AuthService;
  let backend: HttpTestingController;

  const configure = (): void => {
    TestBed.resetTestingModule();
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    auth = TestBed.inject(AuthService);
    backend = TestBed.inject(HttpTestingController);
  };

  beforeEach(() => {
    localStorage.clear();
    configure();
  });

  afterEach(() => backend.verify());

  it('starts unauthenticated with no stored token', () => {
    expect(auth.isAuthenticated()).toBe(false);
    expect(auth.token).toBeNull();
  });

  it('stores both tokens on a successful sign-in', () => {
    auth.login('manager', 'secret').subscribe();

    const request = backend.expectOne((r) => r.url.endsWith('/auth/token/'));
    expect(request.request.body).toEqual({ username: 'manager', password: 'secret' });
    request.flush({ access: 'access-token', refresh: 'refresh-token' });

    expect(auth.isAuthenticated()).toBe(true);
    expect(auth.token).toBe('access-token');
    expect(TestBed.inject(TokenStorageService).refresh).toBe('refresh-token');
  });

  it('stays unauthenticated when the credentials are rejected', () => {
    auth.login('manager', 'wrong').subscribe({ error: () => undefined });

    backend
      .expectOne((r) => r.url.endsWith('/auth/token/'))
      .flush({ detail: 'no', code: 'invalid_credentials' }, { status: 401, statusText: '' });

    expect(auth.isAuthenticated()).toBe(false);
  });

  it('restores a session from storage on construction', () => {
    auth.login('manager', 'secret').subscribe();
    backend.expectOne(() => true).flush({ access: 'access-token', refresh: 'refresh-token' });

    configure(); // simulates a page reload
    expect(auth.isAuthenticated()).toBe(true);
  });

  it('clears the session on sign-out', () => {
    auth.login('manager', 'secret').subscribe();
    backend.expectOne(() => true).flush({ access: 'access-token', refresh: 'refresh-token' });

    auth.logout();

    expect(auth.isAuthenticated()).toBe(false);
    expect(auth.token).toBeNull();
    expect(TestBed.inject(TokenStorageService).access).toBeNull();
  });
});
