import { TestBed } from '@angular/core/testing';

import { TokenStorageService } from './token-storage.service';

describe('TokenStorageService', () => {
  let storage: TokenStorageService;

  beforeEach(() => {
    localStorage.clear();
    TestBed.configureTestingModule({});
    storage = TestBed.inject(TokenStorageService);
  });

  it('round-trips both tokens', () => {
    storage.store('a', 'r');

    expect(storage.access).toBe('a');
    expect(storage.refresh).toBe('r');
  });

  it('keeps the existing refresh token when only an access token is stored', () => {
    storage.store('a', 'r');
    storage.store('a2');

    expect(storage.access).toBe('a2');
    expect(storage.refresh).toBe('r');
  });

  it('clears both', () => {
    storage.store('a', 'r');
    storage.clear();

    expect(storage.access).toBeNull();
    expect(storage.refresh).toBeNull();
  });

  it('degrades to "no token" when storage throws', () => {
    // Private browsing and blocked site data make localStorage throw outright.
    const boom = (): never => {
      throw new Error('storage disabled');
    };
    jest.spyOn(Storage.prototype, 'getItem').mockImplementation(boom);
    jest.spyOn(Storage.prototype, 'setItem').mockImplementation(boom);
    jest.spyOn(Storage.prototype, 'removeItem').mockImplementation(boom);

    expect(() => storage.store('a', 'r')).not.toThrow();
    expect(storage.access).toBeNull();
    expect(() => storage.clear()).not.toThrow();

    jest.restoreAllMocks();
  });
});
