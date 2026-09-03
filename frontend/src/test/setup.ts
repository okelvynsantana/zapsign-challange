/**
 * Global Jest setup.
 *
 * Installs zone.js + the Angular TestBed environment provided by
 * jest-preset-angular v14 (`setup-env/zone` entry point). Must run before any
 * spec touches `TestBed`.
 */
import { setupZoneTestEnv } from 'jest-preset-angular/setup-env/zone';

setupZoneTestEnv({
  errorOnUnknownElements: true,
  errorOnUnknownProperties: true,
});
