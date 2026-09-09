import { ChangeDetectionStrategy, Component, inject, output } from '@angular/core';
import { RouterLink, RouterLinkActive } from '@angular/router';

import { AuthService } from '../../core/auth/auth.service';

/**
 * The application's one persistent chrome: brand, navigation, sign out.
 *
 * Layer: organism (Constitution Principle XI). It reads `AuthService` directly
 * because the session is not a property of any one screen — pushing it in as an
 * input would make every page restate a fact none of them owns. Ending the
 * session, by contrast, is a routing decision, so the button only *reports* the
 * intent and the shell performs it; the header stays free of `Router`.
 *
 * The navigation exists only for a signed-in manager: on the login screen there
 * is nowhere to go, so an inert set of links would be noise.
 */
@Component({
  selector: 'app-header',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink, RouterLinkActive],
  template: `
    <header class="hdr">
      <div class="hdr__brand">
        <!-- Brand mark, not a status mark, so it is drawn here rather than
             added to the icon atom's enumerated vocabulary. -->
        <svg width="20" height="20" viewBox="0 0 20 20" fill="none" aria-hidden="true" focusable="false">
          <rect
            x="2.7"
            y="2.7"
            width="14.6"
            height="14.6"
            rx="4.2"
            stroke="var(--accent)"
            stroke-width="1.5"
          />
          <path
            d="M6.7 10.1 8.9 12.4 13.3 7.7"
            stroke="var(--accent)"
            stroke-width="1.5"
            stroke-linecap="round"
            stroke-linejoin="round"
          />
        </svg>
        <h1 class="t-panel">Documentos e Assinaturas</h1>
      </div>

      @if (auth.isAuthenticated()) {
        <nav class="hdr__nav" aria-label="Navegação principal">
          @for (link of links; track link.path) {
            <a
              class="hdr__link t-body"
              [routerLink]="link.path"
              routerLinkActive="hdr__link--active"
              ariaCurrentWhenActive="page"
              >{{ link.label }}</a
            >
          }
          <button type="button" class="btn btn--sm" (click)="signOut.emit()">Sair</button>
        </nav>
      }
    </header>
  `,
  styles: [
    `
      .hdr {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: var(--space-4);
        /* The 56px row is a control height plus one step of space, so the
         * chrome tracks the scale instead of a number of its own. */
        height: var(--h-header);
        padding: 0 var(--page-pad-x);
        background: var(--surface);
        border-bottom: 1px solid var(--line);
      }

      .hdr__brand {
        display: flex;
        align-items: center;
        gap: var(--space-2);
      }

      .hdr__nav {
        display: flex;
        align-items: center;
        gap: var(--space-1);
      }

      .hdr__link {
        display: inline-flex;
        align-items: center;
        height: var(--h-btn);
        padding: 0 var(--space-3);
        border-radius: var(--radius-control);
        color: var(--ink-2);
      }

      .hdr__link:hover {
        color: var(--ink);
        /* The global underline reads as a link inside prose; in a row of
         * destinations it only adds noise. */
        text-decoration: none;
      }

      .hdr__link--active,
      .hdr__link--active:hover {
        background: var(--accent-soft);
        color: var(--accent-ink);
      }

      /* The sign out control sits apart from the destinations. */
      .hdr__nav .btn {
        margin-left: var(--space-2);
      }
    `,
  ],
})
export class AppHeaderComponent {
  readonly auth = inject(AuthService);

  /** Ending the session is the shell's call; the header only reports it. */
  readonly signOut = output<void>();

  readonly links = [
    { path: '/documents', label: 'Documentos' },
    { path: '/companies', label: 'Organização' },
    { path: '/reports', label: 'Relatórios' },
    { path: '/alerts', label: 'Alertas' },
  ] as const;
}
