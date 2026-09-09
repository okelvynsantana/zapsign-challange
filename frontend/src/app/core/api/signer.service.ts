import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { Paginated } from '../models/api.model';
import { Signer } from '../models/signer.model';
import { HttpService } from './http.service';

/** Typed client for the standalone `/api/signers/` surface. */
@Injectable({ providedIn: 'root' })
export class SignerService {
  private readonly http = inject(HttpService);

  listForDocument(documentId: string): Observable<Paginated<Signer>> {
    return this.http.get<Paginated<Signer>>('/signers/', { document: documentId });
  }

  create(payload: { document: string; name: string; email: string }): Observable<Signer> {
    return this.http.post<Signer>('/signers/', payload);
  }

  update(id: string, payload: { name?: string; email?: string }): Observable<Signer> {
    return this.http.patch<Signer>(`/signers/${id}/`, payload);
  }

  remove(id: string): Observable<void> {
    return this.http.delete(`/signers/${id}/`);
  }
}
