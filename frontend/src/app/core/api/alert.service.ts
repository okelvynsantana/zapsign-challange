import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { Alert } from '../models/alert.model';
import { HttpService } from './http.service';

/** Typed client for `/api/alerts/`. The endpoint returns a plain list, not a page. */
@Injectable({ providedIn: 'root' })
export class AlertService {
  private readonly http = inject(HttpService);

  list(): Observable<Alert[]> {
    return this.http.get<Alert[]>('/alerts/');
  }
}
