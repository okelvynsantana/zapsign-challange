import { ChangeDetectionStrategy, Component, input } from '@angular/core';

/**
 * The single source of every mark in the interface.
 *
 * The status vocabulary (Constitution Principle IX) depends on each mark being
 * *identical* everywhere it appears — a hand-copied path that drifts silently
 * breaks the guarantee. Enumerating the names also turns a typo into a compile
 * error rather than an empty box (research R-005).
 *
 * Layer: atom. It knows no domain model and injects nothing. It is a component
 * rather than a global class because its substance is SVG geometry, which no
 * stylesheet can hold.
 *
 * Always decorative: the meaning is carried by the adjacent text, so the SVG is
 * hidden from assistive technology (accessibility contract).
 */
export type IconName =
  | 'check'
  | 'check-circle'
  | 'cross'
  | 'dashed-circle'
  | 'risk'
  | 'alert'
  | 'retry'
  | 'chevron'
  | 'lock'
  | 'ellipsis'
  | 'plus'
  | 'minus'
  | 'close'
  | 'clock'
  | 'document';

@Component({
  selector: 'app-icon',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <svg
      [attr.width]="size()"
      [attr.height]="size()"
      viewBox="0 0 12 12"
      fill="none"
      aria-hidden="true"
      focusable="false"
    >
      @switch (name()) {
        @case ('check') {
          <path d="M2.6 6.2 4.9 8.5 9.4 3.6" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" />
        }
        @case ('check-circle') {
          <circle cx="6" cy="6" r="4.4" stroke="currentColor" stroke-width="1.3" />
          <path d="M4.1 6.1 5.5 7.5 8 4.8" stroke="currentColor" stroke-width="1.3" stroke-linecap="round" stroke-linejoin="round" />
        }
        @case ('cross') {
          <path d="M3.3 3.3 8.7 8.7M8.7 3.3 3.3 8.7" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" />
        }
        @case ('dashed-circle') {
          <circle cx="6" cy="6" r="4.3" stroke="currentColor" stroke-width="1.4" stroke-dasharray="2.3 2" />
        }
        @case ('risk') {
          <path d="M6 1.7 11 10.4H1z" stroke="currentColor" stroke-width="1.3" stroke-linejoin="round" />
          <path d="M6 5.2v2.1" stroke="currentColor" stroke-width="1.3" stroke-linecap="round" />
          <circle cx="6" cy="8.9" r=".65" fill="currentColor" />
        }
        @case ('alert') {
          <circle cx="6" cy="6" r="4.6" stroke="currentColor" stroke-width="1.2" />
          <path d="M6 3.6v2.8" stroke="currentColor" stroke-width="1.3" stroke-linecap="round" />
          <circle cx="6" cy="8.3" r=".65" fill="currentColor" />
        }
        @case ('retry') {
          <path d="M10 6a4 4 0 1 1-1.3-3" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" />
          <path d="M10.2 1.4v2.2H8" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round" />
        }
        @case ('chevron') {
          <path d="M3.2 4.6 6 7.4l2.8-2.8" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round" />
        }
        @case ('lock') {
          <rect x="2.2" y="5.3" width="7.6" height="5.2" rx="1.2" stroke="currentColor" stroke-width="1.2" />
          <path d="M4.1 5.3V3.9a1.9 1.9 0 0 1 3.8 0v1.4" stroke="currentColor" stroke-width="1.2" />
        }
        @case ('ellipsis') {
          <circle cx="2.4" cy="6" r="1" fill="currentColor" />
          <circle cx="6" cy="6" r="1" fill="currentColor" />
          <circle cx="9.6" cy="6" r="1" fill="currentColor" />
        }
        @case ('plus') {
          <path d="M6 1.8v8.4M1.8 6h8.4" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" />
        }
        @case ('minus') {
          <path d="M2.6 6h6.8" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" />
        }
        @case ('close') {
          <path d="M3.3 3.3 8.7 8.7M8.7 3.3 3.3 8.7" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" />
        }
        @case ('clock') {
          <circle cx="6" cy="6" r="4.6" stroke="currentColor" stroke-width="1.2" />
          <path d="M6 3.5V6l1.7 1.1" stroke="currentColor" stroke-width="1.3" stroke-linecap="round" stroke-linejoin="round" />
        }
        @case ('document') {
          <path d="M3.2 1.6h4L9 3.4v7a.6.6 0 0 1-.6.6H3.2a.6.6 0 0 1-.6-.6V2.2a.6.6 0 0 1 .6-.6z" stroke="currentColor" stroke-width="1.2" stroke-linejoin="round" />
          <path d="M7 1.8v1.8h1.9" stroke="currentColor" stroke-width="1.2" stroke-linejoin="round" />
        }
      }
    </svg>
  `,
  styles: [
    `
      :host {
        display: inline-flex;
        flex-shrink: 0;
        line-height: 0;
      }
    `,
  ],
})
export class IconComponent {
  readonly name = input.required<IconName>();
  readonly size = input(12);
}
