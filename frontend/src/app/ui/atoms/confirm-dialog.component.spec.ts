import { ComponentFixture, TestBed } from '@angular/core/testing';

import { ConfirmDialogComponent } from './confirm-dialog.component';

describe('ConfirmDialogComponent', () => {
  let fixture: ComponentFixture<ConfirmDialogComponent>;
  let confirmed: number;
  let cancelled: number;

  const dialog = (): HTMLDialogElement => fixture.nativeElement.querySelector('dialog');
  const actions = (): HTMLButtonElement[] =>
    Array.from(fixture.nativeElement.querySelectorAll('.dlg__actions button'));
  const cancelButton = (): HTMLButtonElement => actions()[0];
  const confirmButton = (): HTMLButtonElement => actions()[1];

  beforeEach(async () => {
    await TestBed.configureTestingModule({ imports: [ConfirmDialogComponent] }).compileComponents();

    fixture = TestBed.createComponent(ConfirmDialogComponent);
    fixture.componentRef.setInput('title', 'Excluir documento?');

    confirmed = 0;
    cancelled = 0;
    fixture.componentInstance.confirmed.subscribe(() => (confirmed += 1));
    fixture.componentInstance.cancelled.subscribe(() => (cancelled += 1));

    fixture.detectChanges();
  });

  it('stays closed until open() is called', () => {
    expect(dialog().open).toBe(false);

    fixture.componentInstance.open();

    expect(dialog().open).toBe(true);
  });

  it('renders the title, the message and the default labels', () => {
    fixture.componentRef.setInput('message', 'Esta ação não pode ser desfeita.');
    fixture.detectChanges();

    expect(fixture.nativeElement.textContent).toContain('Excluir documento?');
    expect(fixture.nativeElement.textContent).toContain('Esta ação não pode ser desfeita.');
    expect(cancelButton().textContent?.trim()).toBe('Cancelar');
    expect(confirmButton().textContent?.trim()).toBe('Confirmar');
  });

  it('emits confirmed — and never cancelled — when the confirm button is pressed', () => {
    fixture.componentInstance.open();

    confirmButton().click();

    expect(confirmed).toBe(1);
    expect(cancelled).toBe(0);
    expect(dialog().open).toBe(false);
  });

  it('emits cancelled — and never confirmed — when the cancel button is pressed', () => {
    fixture.componentInstance.open();

    cancelButton().click();

    expect(cancelled).toBe(1);
    expect(confirmed).toBe(0);
    expect(dialog().open).toBe(false);
  });

  // Esc dismissal reaches the component only as the platform's `close` event:
  // there is no click to observe, so this is the whole of that path.
  it('emits cancelled exactly once when the platform closes the dialog', () => {
    fixture.componentInstance.open();

    dialog().dispatchEvent(new Event('close'));
    dialog().dispatchEvent(new Event('close'));

    expect(cancelled).toBe(1);
    expect(confirmed).toBe(0);
  });

  it('does not re-emit when the platform reports the close that a button caused', () => {
    fixture.componentInstance.open();

    confirmButton().click();
    dialog().dispatchEvent(new Event('close'));

    expect(confirmed).toBe(1);
    expect(cancelled).toBe(0);
  });

  it('focuses confirm by default', () => {
    fixture.componentInstance.open();

    expect(document.activeElement).toBe(confirmButton());
  });

  it('focuses cancel and marks confirm as dangerous when destructive', () => {
    fixture.componentRef.setInput('destructive', true);
    fixture.detectChanges();

    fixture.componentInstance.open();

    expect(document.activeElement).toBe(cancelButton());
    expect(confirmButton().classList).toContain('btn--danger');
    expect(confirmButton().classList).not.toContain('btn--primary');
  });
});
