import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { Router, provideRouter } from '@angular/router';

import { AppComponent } from './app.component';
import { AuthService } from './core/auth/auth.service';

describe('AppComponent', () => {
  let fixture: ComponentFixture<AppComponent>;

  const signIn = (): void => {
    TestBed.inject(AuthService).login('manager', 'secret').subscribe();
    TestBed.inject(HttpTestingController)
      .expectOne((r) => r.url.endsWith('/auth/token/'))
      .flush({ access: 'a', refresh: 'r' });
    fixture.detectChanges();
  };

  beforeEach(async () => {
    localStorage.clear();
    await TestBed.configureTestingModule({
      imports: [AppComponent],
      providers: [provideHttpClient(), provideHttpClientTesting(), provideRouter([])],
    }).compileComponents();

    fixture = TestBed.createComponent(AppComponent);
    fixture.detectChanges();
  });

  it('hides the navigation while signed out', () => {
    expect(fixture.nativeElement.querySelector('nav')).toBeNull();
  });

  it('shows every feature link once signed in', () => {
    signIn();

    const links = [...fixture.nativeElement.querySelectorAll('nav a')].map(
      (a: Element) => a.textContent?.trim(),
    );
    expect(links).toEqual(['Documentos', 'Organização', 'Relatórios', 'Alertas']);
  });

  it('signing out clears the session and returns to the login screen', () => {
    signIn();
    const navigate = jest.spyOn(TestBed.inject(Router), 'navigate').mockResolvedValue(true);

    fixture.componentInstance.logout();
    fixture.detectChanges();

    expect(TestBed.inject(AuthService).isAuthenticated()).toBe(false);
    expect(navigate).toHaveBeenCalledWith(['/login']);
    expect(fixture.nativeElement.querySelector('nav')).toBeNull();
  });
});
