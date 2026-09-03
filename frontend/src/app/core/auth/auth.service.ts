import { Injectable, computed, inject, signal } from '@angular/core';
import { Observable, tap } from 'rxjs';

import { HttpService } from '../api/http.service';
import { TokenStorageService } from './token-storage.service';

interface TokenPair {
  access: string;
  refresh: string;
}

/** Internal-manager session: obtains and holds the SPA's JWT (research.md §2). */
@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly http = inject(HttpService);
  private readonly storage = inject(TokenStorageService);

  private readonly accessToken = signal<string | null>(this.storage.access);

  readonly isAuthenticated = computed(() => this.accessToken() !== null);

  get token(): string | null {
    return this.accessToken();
  }

  login(username: string, password: string): Observable<TokenPair> {
    return this.http.post<TokenPair>('/auth/token/', { username, password }).pipe(
      tap((pair) => {
        this.storage.store(pair.access, pair.refresh);
        this.accessToken.set(pair.access);
      }),
    );
  }

  logout(): void {
    this.storage.clear();
    this.accessToken.set(null);
  }
}
