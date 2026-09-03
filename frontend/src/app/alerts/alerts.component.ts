import { Component, OnInit, computed, inject, signal } from '@angular/core';

import { AlertService } from '../core/api/alert.service';
import { Alert } from '../core/models/alert.model';
import { ApiError } from '../core/models/api.model';
import { ErrorMessageComponent } from '../shared/error-message.component';

/** Operations dashboard: stalled documents and risk findings (bonus US5). */
@Component({
  selector: 'app-alerts',
  imports: [ErrorMessageComponent],
  templateUrl: './alerts.component.html',
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
