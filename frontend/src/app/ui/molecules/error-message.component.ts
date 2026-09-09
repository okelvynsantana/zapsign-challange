import { ChangeDetectionStrategy, Component, input } from '@angular/core';

import { ApiError } from '../../core/models/api.model';
import { IconComponent } from '../atoms/icon.component';

/**
 * The one presentation of a failed request (data-model §7).
 *
 * `code` is rendered rather than swallowed because it is the only part of the
 * body a person can quote in a support conversation — `detail` is prose that
 * changes, the code does not.
 *
 * Each field error carries a stable `err-<field>` id so the control that owns
 * the field can point at it with `aria-describedby` (FR-025): the association
 * is what makes the error reachable by a screen reader, and it can only be made
 * from the outside, by the form.
 *
 * Layer: molecule. It binds one domain value and injects nothing.
 */
@Component({
  selector: 'app-error-message',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [IconComponent],
  template: `
    @if (error(); as err) {
      <div class="banner" role="alert">
        <span class="banner__mark"><app-icon name="alert" [size]="14" /></span>
        <div class="banner__body">
          <p class="banner__title">{{ err.detail }}</p>
          <p class="banner__code">{{ err.code }}</p>
          @if (err.fields; as fields) {
            <ul class="banner__fields">
              @for (entry of fieldEntries(fields); track entry[0]) {
                <li class="banner__field" [id]="'err-' + entry[0]">
                  <span class="banner__field-name">{{ entry[0] }}</span>
                  {{ entry[1].join(' ') }}
                </li>
              }
            </ul>
          }
        </div>
      </div>
    }
  `,
  styles: [
    `
      /* .banner is a row; stacking its contents and resetting the list is
         layout the global class deliberately leaves to whoever fills it. */
      .banner__body {
        display: flex;
        flex-direction: column;
        gap: var(--space-1);
        min-width: 0;
      }

      .banner__mark {
        display: inline-flex;
        padding-top: 1px;
        color: var(--bad-ink);
      }

      .banner__fields {
        margin: var(--space-1) 0 0;
        padding: 0;
        list-style: none;
        display: flex;
        flex-direction: column;
        gap: var(--space-1);
      }

      .banner__field {
        font-size: 12px;
        line-height: 1.45;
        color: var(--bad-ink);
      }

      .banner__field-name {
        font-family: var(--font-mono);
        font-size: 10.5px;
        letter-spacing: 0.04em;
        margin-right: var(--space-1);
      }
    `,
  ],
})
export class ErrorMessageComponent {
  readonly error = input<ApiError | null>(null);

  /** `Object.entries` is not reachable from a template expression. */
  fieldEntries(fields: Record<string, string[]>): [string, string[]][] {
    return Object.entries(fields);
  }
}
