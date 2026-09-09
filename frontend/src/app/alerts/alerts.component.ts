import {
  ChangeDetectionStrategy,
  Component,
  OnInit,
  computed,
  inject,
  signal,
} from '@angular/core';

import { AlertService } from '../core/api/alert.service';
import { Alert } from '../core/models/alert.model';
import { ApiError } from '../core/models/api.model';
import { EmptyStateComponent } from '../ui/atoms/empty-state.component';
import { IconComponent } from '../ui/atoms/icon.component';
import { ErrorMessageComponent } from '../ui/molecules/error-message.component';
import { AlertGroupComponent } from './alert-group.component';

/**
 * Operations dashboard: stalled documents and risk findings (bonus US5).
 *
 * The page fetches and splits; each group renders itself. The split is kept
 * here because the two lists are the page's subject — an empty one is still a
 * group with a count, not a list to drop.
 */
@Component({
  selector: 'app-alerts',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [ErrorMessageComponent, EmptyStateComponent, IconComponent, AlertGroupComponent],
  templateUrl: './alerts.component.html',
  styleUrl: './alerts.component.scss',
})
export class AlertsComponent implements OnInit {
  private readonly alerts = inject(AlertService);

  readonly items = signal<Alert[]>([]);
  readonly loading = signal(true);
  readonly error = signal<ApiError | null>(null);

  readonly stalled = computed(() => this.items().filter((a) => a.type === 'stalled'));
  readonly risks = computed(() => this.items().filter((a) => a.type === 'risk'));

  ngOnInit(): void {
    this.refresh();
  }

  refresh(): void {
    this.loading.set(true);
    this.alerts.list().subscribe({
      next: (alerts) => {
        this.items.set(alerts);
        this.loading.set(false);
      },
      error: (err: ApiError) => {
        this.loading.set(false);
        this.error.set(err);
      },
    });
  }
}
