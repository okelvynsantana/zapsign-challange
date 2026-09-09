import { Component, signal } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';

import { ApiError } from '../../core/models/api.model';
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

  const setError = (error: ApiError): void => {
    fixture.componentInstance.error.set(error);
    fixture.detectChanges();
  };

  beforeEach(async () => {
    await TestBed.configureTestingModule({ imports: [HostComponent] }).compileComponents();
    fixture = TestBed.createComponent(HostComponent);
    fixture.detectChanges();
  });

  it('renders nothing when there is no error', () => {
    expect(fixture.nativeElement.querySelector('.banner')).toBeNull();
  });

  it('renders the message', () => {
    setError({ detail: 'Something went wrong.', code: 'x' });

    expect(fixture.nativeElement.textContent).toContain('Something went wrong.');
  });

  it('renders the code as the handle to quote in support', () => {
    setError({ detail: 'Something went wrong.', code: 'upstream_unavailable' });

    expect(fixture.nativeElement.querySelector('.banner__code').textContent).toContain(
      'upstream_unavailable',
    );
  });

  it('announces itself', () => {
    setError({ detail: 'Something went wrong.', code: 'x' });

    expect(fixture.nativeElement.querySelector('[role="alert"]')).not.toBeNull();
  });

  it('lists per-field validation detail', () => {
    setError({
      detail: 'The request payload failed validation.',
      code: 'validation_error',
      fields: { pdf_url: ['Enter a valid URL.'], signers: ['At least one signer is required.'] },
    });

    const items = fixture.nativeElement.querySelectorAll('li');
    expect(items).toHaveLength(2);
    expect(fixture.nativeElement.textContent).toContain('pdf_url');
    expect(fixture.nativeElement.textContent).toContain('Enter a valid URL.');
  });

  it('gives each field error the id its control can describe itself with', () => {
    setError({
      detail: 'The request payload failed validation.',
      code: 'validation_error',
      fields: { pdf_url: ['Enter a valid URL.'], signers: ['At least one signer is required.'] },
    });

    const field = fixture.nativeElement.querySelector('#err-pdf_url');
    expect(field).not.toBeNull();
    expect(field.textContent).toContain('Enter a valid URL.');
    expect(fixture.nativeElement.querySelector('#err-signers')).not.toBeNull();
  });

  it('joins every message a field carries', () => {
    setError({
      detail: 'The request payload failed validation.',
      code: 'validation_error',
      fields: { name: ['This field is required.', 'Maximum 120 characters.'] },
    });

    const field = fixture.nativeElement.querySelector('#err-name');
    expect(field.textContent).toContain('This field is required. Maximum 120 characters.');
  });
});
