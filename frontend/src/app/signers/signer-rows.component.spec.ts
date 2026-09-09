import { Component, viewChild } from '@angular/core';
import { FormArray, FormBuilder, Validators } from '@angular/forms';

import { SignerForm } from './signer-form';
import { ComponentFixture, TestBed } from '@angular/core/testing';

import { SignerRowsComponent } from './signer-rows.component';

@Component({
  imports: [SignerRowsComponent],
  template: `<app-signer-rows [parent]="form" [makeRow]="makeRow" />`,
})
class HostComponent {
  private readonly fb = new FormBuilder();
  readonly rows = viewChild.required(SignerRowsComponent);
  readonly makeRow = (): SignerForm => this.row();
  readonly form = this.fb.nonNullable.group({
    signers: this.fb.array<SignerForm>([this.row()]),
  });

  get signers(): FormArray<SignerForm> {
    return this.form.get('signers') as FormArray<SignerForm>;
  }

  private row(): SignerForm {
    return this.fb.nonNullable.group({
      name: ['', Validators.required],
      email: ['', [Validators.required, Validators.email]],
    });
  }
}

describe('SignerRowsComponent', () => {
  let fixture: ComponentFixture<HostComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({ imports: [HostComponent] }).compileComponents();
    fixture = TestBed.createComponent(HostComponent);
    fixture.detectChanges();
  });

  it('renders one row to start with', () => {
    expect(fixture.nativeElement.querySelectorAll('.signer-row')).toHaveLength(1);
  });

  it('appends a row when "Add signer" is clicked', () => {
    fixture.nativeElement.querySelector('[data-testid="signer-add"]').click();
    fixture.detectChanges();

    expect(fixture.componentInstance.signers.length).toBe(2);
    expect(fixture.nativeElement.querySelectorAll('.signer-row')).toHaveLength(2);
  });

  it('removes a row but never the last one', () => {
    fixture.componentInstance.rows().add();
    fixture.detectChanges();

    fixture.componentInstance.rows().remove(1);
    expect(fixture.componentInstance.signers.length).toBe(1);

    fixture.componentInstance.rows().remove(0);
    expect(fixture.componentInstance.signers.length).toBe(1);
  });

  it('disables the remove button while a single row remains', () => {
    const button = fixture.nativeElement.querySelector('[data-testid="signer-remove"]');
    expect(button.disabled).toBe(true);
  });

  it('rejects an invalid email on a row', () => {
    const row = fixture.componentInstance.signers.at(0);
    row.setValue({ name: 'Ana', email: 'not-an-email' });

    expect(row.get('email')?.invalid).toBe(true);
  });
});
