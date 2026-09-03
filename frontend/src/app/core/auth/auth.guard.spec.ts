import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { Router, UrlTree } from '@angular/router';
import { provideRouter } from '@angular/router';

import { authGuard } from './auth.guard';
import { AuthService } from './auth.service';

describe('authGuard', () => {
  const run = (): boolean | UrlTree =>
    TestBed.runInInjectionContext(
      () =>
        authGuard(
          // The guard reads neither argument.
          null as never,
          null as never,
        ) as boolean | UrlTree,
    );

  beforeEach(() => {
    localStorage.clear();
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting(), provideRouter([])],
    });
  });

  it('redirects an anonymous visitor to the login screen', () => {
    const result = run();

    expect(result).toBeInstanceOf(UrlTree);
    expect(TestBed.inject(Router).serializeUrl(result as UrlTree)).toBe('/login');
  });

  it('lets an authenticated manager through', () => {
    TestBed.inject(AuthService).login('manager', 'secret').subscribe();
    TestBed.inject(HttpTestingController)
      .expectOne((r) => r.url.endsWith('/auth/token/'))
      .flush({ access: 'access-token', refresh: 'refresh-token' });

    expect(run()).toBe(true);
  });
});
