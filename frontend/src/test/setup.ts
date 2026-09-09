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

// jsdom 20 (the version this project runs) does not implement the dialog
// element's modal API, so a component built on native <dialog> would throw the
// moment a spec opened it. Stubbing the two methods keeps the production code
// free of a polyfill and confines the gap to the test environment
// (research R-004).
if (typeof HTMLDialogElement !== 'undefined') {
  const proto = HTMLDialogElement.prototype as HTMLDialogElement & {
    showModal?: () => void;
    close?: (returnValue?: string) => void;
  };

  if (!proto.showModal) {
    proto.showModal = function showModal(this: HTMLDialogElement): void {
      this.open = true;
    };
  }

  if (!proto.close) {
    proto.close = function close(this: HTMLDialogElement, returnValue?: string): void {
      this.open = false;
      if (returnValue !== undefined) {
        this.returnValue = returnValue;
      }
      this.dispatchEvent(new Event('close'));
    };
  }
}
