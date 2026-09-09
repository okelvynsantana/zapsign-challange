import { DatePipe } from '@angular/common';
import { ChangeDetectionStrategy, Component, input, output } from '@angular/core';

import { Document } from '../core/models/document.model';
import { IconComponent } from '../ui/atoms/icon.component';
import { AnalysisMarkerComponent } from '../ui/molecules/analysis-marker.component';
import { ProviderStatusBadgeComponent } from '../ui/molecules/provider-status-badge.component';
import { SignatureStatusComponent } from '../ui/molecules/signature-status.component';
import { AnalysisPanelComponent } from './analysis-panel.component';

/**
 * The `detail` mode of the rail: one document, its signers, its analysis (FR-017).
 *
 * It hosts the analysis panel rather than reimplementing it, and forwards the run
 * upward — the row belongs to the page, so only the page may refresh it.
 */
@Component({
  selector: 'app-document-detail-rail',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    DatePipe,
    IconComponent,
    AnalysisMarkerComponent,
    ProviderStatusBadgeComponent,
    SignatureStatusComponent,
    AnalysisPanelComponent,
  ],
  templateUrl: './document-detail-rail.component.html',
  styleUrl: './document-detail-rail.component.scss',
})
export class DocumentDetailRailComponent {
  readonly document = input.required<Document>();
  readonly companyName = input('');

  readonly closed = output<void>();
  readonly edited = output<Document>();
  readonly analyzed = output<Document>();
}
