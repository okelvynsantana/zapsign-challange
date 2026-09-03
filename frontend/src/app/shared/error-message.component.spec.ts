import { Component, signal } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';

import { ApiError } from '../core/models/api.model';
import { ErrorMessageComponent } from './error-message.component';

@Component({
  imports: [ErrorMessageComponent],
  template: `<app-error-message [error]="error()" />`,
})
class HostComponent {
  readonly error = signal<ApiError | null>(null);
}

describe('ErrorMessageComponent', () => {
  let fixture: ComponentFixture<HostComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({ imports: [HostComponent] }).compileComponents();
    fixture = TestBed.createComponent(HostComponent);
    fixture.detectChanges();
  });

  it('renders nothing when there is no error', () => {
    expect(fixture.nativeElement.querySelector('.error')).toBeNull();
  });

  it('renders the message', () => {
    fixture.componentInstance.error.set({ detail: 'Something went wrong.', code: 'x' });
    fixture.detectChanges();

    expect(fixture.nativeElement.textContent).toContain('Something went wrong.');
  });

  it('lists per-field validation detail', () => {
    fixture.componentInstance.error.set({
      detail: 'The request payload failed validation.',
      code: 'validation_error',
      fields: { pdf_url: ['Enter a valid URL.'], signers: ['At least one signer is required.'] },
    });
    fixture.detectChanges();

    const items = fixture.nativeElement.querySelectorAll('li');
    expect(items).toHaveLength(2);
    expect(fixture.nativeElement.textContent).toContain('pdf_url');
    expect(fixture.nativeElement.textContent).toContain('Enter a valid URL.');
  });
});
