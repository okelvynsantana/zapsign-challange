import { ComponentFixture, TestBed } from '@angular/core/testing';

import { SignatureStatusComponent } from './signature-status.component';

describe('SignatureStatusComponent', () => {
  let fixture: ComponentFixture<SignatureStatusComponent>;

  const render = (status: string | null): HTMLElement => {
    fixture.componentRef.setInput('status', status);
    fixture.detectChanges();
    return fixture.nativeElement.querySelector('.sig');
  };

  beforeEach(async () => {
    await TestBed.configureTestingModule({ imports: [SignatureStatusComponent] }).compileComponents();
    fixture = TestBed.createComponent(SignatureStatusComponent);
  });

  it('never renders a badge — this scale carries no action of ours', () => {
    render('signed');

    expect(fixture.nativeElement.querySelector('.badge')).toBeNull();
  });

  it.each(['signed', 'assinado'])('marks %s as signed', (status) => {
    const sig = render(status);

    expect(sig.querySelector('.sig__dot--signed')).not.toBeNull();
    expect(sig.textContent).toContain(status);
  });

  it.each(['refused', 'rejected', 'recusado'])('marks %s as refused', (status) => {
    const sig = render(status);

    expect(sig.querySelector('.sig__dot--refused')).not.toBeNull();
    expect(sig.textContent).toContain(status);
  });

  // The provider owns this vocabulary, so an unknown value is normal traffic,
  // not a defect: it must show as reported and never break the row (FR-004).
  it.each(['pending', 'link_opened', 'a brand new provider word'])(
    'renders the unrecognised value %s neutral and verbatim',
    (status) => {
      expect(() => render(status)).not.toThrow();

      const sig = fixture.nativeElement.querySelector('.sig');
      expect(sig.querySelector('.sig__dot')).not.toBeNull();
      expect(sig.querySelector('.sig__dot--signed')).toBeNull();
      expect(sig.querySelector('.sig__dot--refused')).toBeNull();
      expect(sig.classList).not.toContain('sig--none');
      expect(sig.textContent).toContain(status);
    },
  );

  it('matches the known values whatever case and padding the provider sends', () => {
    expect(render('  Signed ').querySelector('.sig__dot--signed')).not.toBeNull();
  });

  it.each([null, ''])('renders %p as the explicit no-state form', (status) => {
    const sig = render(status);

    expect(sig.classList).toContain('sig--none');
    expect(sig.querySelector('.sig__dot')).toBeNull();
    expect(sig.textContent?.trim()).toBe('—');
  });
});
