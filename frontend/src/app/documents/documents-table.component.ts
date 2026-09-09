import { DatePipe } from '@angular/common';
import { ChangeDetectionStrategy, Component, input, output, signal } from '@angular/core';

import { Document } from '../core/models/document.model';
import { IconComponent } from '../ui/atoms/icon.component';
import { AnalysisMarkerComponent } from '../ui/molecules/analysis-marker.component';
import { ProviderStatusBadgeComponent } from '../ui/molecules/provider-status-badge.component';
import { SignatureStatusComponent } from '../ui/molecules/signature-status.component';

/**
 * The document list (US2, FR-005, FR-006, FR-018).
 *
 * The densest surface in the product, so every row carries the three status scales in
 * their three distinct forms and nothing else competes with them: the retry is the only
 * action shown in full, and the rest sit behind the overflow control.
 *
 * It reports intent and holds no page state — which row is selected arrives as an input,
 * and the retry rule stays with the page that owns it.
 */
@Component({
  selector: 'app-documents-table',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    DatePipe,
    IconComponent,
    AnalysisMarkerComponent,
    ProviderStatusBadgeComponent,
    SignatureStatusComponent,
  ],
  templateUrl: './documents-table.component.html',
  styleUrl: './documents-table.component.scss',
  // A menu left open over a row the reader has moved past is noise; any click
  // outside the toggle dismisses it, and Escape closes it from wherever focus
  // sits — on the host rather than the menu, which is not itself focusable.
  host: {
    '(document:click)': 'menuFor.set(null)',
    '(document:keydown.escape)': 'menuFor.set(null)',
  },
})
export class DocumentsTableComponent {
  readonly documents = input.required<Document[]>();
  readonly selectedId = input<string | null>(null);
  /** Organisation names by id — the row records an id, a person reads a name. */
  readonly companyNames = input<Record<string, string>>({});
  /** The retry rule lives on the page; the row only asks whether it applies (FR-006). */
  readonly canResync = input.required<(document: Document) => boolean>();

  readonly selected = output<Document>();
  readonly edited = output<Document>();
  readonly removed = output<Document>();
  readonly resynced = output<Document>();

  /** Which row has its overflow menu open. View state of the table, not of the page. */
  readonly menuFor = signal<string | null>(null);

  companyName(document: Document): string {
    return this.companyNames()[document.company] || document.company;
  }

  toggleMenu(document: Document, event: Event): void {
    // Without this the document listener above would close the menu the click just opened.
    event.stopPropagation();
    this.menuFor.update((open) => (open === document.id ? null : document.id));
  }
}
