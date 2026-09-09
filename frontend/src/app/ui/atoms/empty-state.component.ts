import { ChangeDetectionStrategy, Component, input } from '@angular/core';

import { IconComponent, IconName } from './icon.component';

/**
 * The defined presentation for "there is nothing here" (FR-013).
 *
 * `role="status"` matters: an empty result is information, and on the alerts
 * screen it is a *good* result rather than an absence of data, so it should be
 * announced rather than read as a blank region.
 *
 * Layer: atom. Knows no domain model, injects nothing.
 */
@Component({
  selector: 'app-empty-state',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [IconComponent],
  template: `
    <div class="empty" role="status">
      <span class="empty__icon" [class.empty__icon--positive]="positive()">
        <app-icon [name]="icon()" [size]="30" />
      </span>
      <div class="empty__text">
        <h2 class="t-panel">{{ title() }}</h2>
        @if (description()) {
          <p class="t-body">{{ description() }}</p>
        }
      </div>
      <ng-content />
    </div>
  `,
  styles: [
    `
      .empty {
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: var(--space-3);
        padding: 56px var(--space-6);
        text-align: center;
      }

      .empty__icon {
        display: inline-flex;
        color: var(--line-2);
      }

      .empty__icon--positive {
        color: var(--ok-ink);
      }

      .empty__text {
        display: flex;
        flex-direction: column;
        gap: 7px;
        max-width: 400px;
      }

      .empty__text p {
        color: var(--ink-2);
      }
    `,
  ],
})
export class EmptyStateComponent {
  readonly title = input.required<string>();
  readonly description = input('');
  readonly icon = input<IconName>('document');
  /** An empty attention list is a result, not an absence — colour it so. */
  readonly positive = input(false);
}
