import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { Company, CompanyCreate, CompanyUpdate } from '../models/company.model';
import { Paginated } from '../models/api.model';
import { HttpService } from './http.service';

/** Typed client for `/api/companies/`. */
@Injectable({ providedIn: 'root' })
export class CompanyService {
  private readonly http = inject(HttpService);

  list(): Observable<Paginated<Company>> {
    return this.http.get<Paginated<Company>>('/companies/');
  }

  create(payload: CompanyCreate): Observable<Company> {
    return this.http.post<Company>('/companies/', payload);
  }

  update(id: string, payload: CompanyUpdate): Observable<Company> {
    return this.http.patch<Company>(`/companies/${id}/`, payload);
  }

  remove(id: string): Observable<void> {
    return this.http.delete(`/companies/${id}/`);
  }
}
