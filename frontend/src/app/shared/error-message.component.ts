import { Component, input } from '@angular/core';

import { ApiError } from '../core/models/api.model';

/** Renders an `ApiError` — its message plus any per-field validation detail. */
@Component({
  selector: 'app-error-message',
  template: `
    @if (error(); as err) {
      <div class="error" role="alert">
        <p>{{ err.detail }}</p>
        @if (err.fields; as fields) {
          <ul>
            @for (entry of fieldEntries(fields); track entry[0]) {
              <li><strong>{{ entry[0] }}:</strong> {{ entry[1].join(' ') }}</li>
            }
          </ul>
        }
      </div>
    }
  `,
})
export class ErrorMessageComponent {
  readonly error = input<ApiError | null>(null);

  fieldEntries(fields: Record<string, string[]>): [string, string[]][] {
    return Object.entries(fields);
  }
}
