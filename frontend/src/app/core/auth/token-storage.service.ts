import { Injectable } from '@angular/core';

const ACCESS_KEY = 'dsms.access';
const REFRESH_KEY = 'dsms.refresh';

/**
 * Persists the JWT pair.
 *
 * Wrapped in try/catch because `localStorage` throws outright in some privacy modes;
 * losing the token there degrades to "you have to log in again", never to a crash.
 */
@Injectable({ providedIn: 'root' })
export class TokenStorageService {
  get access(): string | null {
    return this.read(ACCESS_KEY);
  }

  get refresh(): string | null {
    return this.read(REFRESH_KEY);
  }

  store(access: string, refresh?: string): void {
    this.write(ACCESS_KEY, access);
    if (refresh) {
      this.write(REFRESH_KEY, refresh);
    }
  }

  clear(): void {
    try {
      localStorage.removeItem(ACCESS_KEY);
      localStorage.removeItem(REFRESH_KEY);
    } catch {
      /* storage unavailable — nothing to clear */
    }
  }

  private read(key: string): string | null {
    try {
      return localStorage.getItem(key);
    } catch {
      return null;
    }
  }

  private write(key: string, value: string): void {
    try {
      localStorage.setItem(key, value);
    } catch {
      /* storage unavailable — the token simply does not survive a reload */
    }
  }
}
