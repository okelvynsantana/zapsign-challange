import { HttpClient, HttpErrorResponse, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, throwError } from 'rxjs';
import { catchError } from 'rxjs/operators';

import { environment } from '../../../environments/environment';
import { ApiError } from '../models/api.model';

/** Query parameters accepted by the typed helpers below. */
export type QueryParams = Record<string, string | number | boolean | undefined | null>;

/**
 * Thin typed wrapper over `HttpClient`.
 *
 * Owns two things so no feature service has to: the API base URL, and normalising
 * every failure into the `ApiError` shape the backend documents. Anything that
 * escapes here (a network drop, an nginx error page) is mapped to the same shape so
 * components only ever handle one error type.
 */
@Injectable({ providedIn: 'root' })
export class HttpService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = environment.apiBaseUrl;

  get<T>(path: string, params?: QueryParams): Observable<T> {
    return this.http
      .get<T>(this.url(path), { params: this.httpParams(params) })
      .pipe(catchError(toApiError));
  }

  post<T>(path: string, body: unknown): Observable<T> {
    return this.http.post<T>(this.url(path), body).pipe(catchError(toApiError));
  }

  patch<T>(path: string, body: unknown): Observable<T> {
    return this.http.patch<T>(this.url(path), body).pipe(catchError(toApiError));
  }

  delete(path: string): Observable<void> {
    return this.http.delete<void>(this.url(path)).pipe(catchError(toApiError));
  }

  private url(path: string): string {
    return `${this.baseUrl}${path}`;
  }

  private httpParams(params?: QueryParams): HttpParams {
    let httpParams = new HttpParams();
    for (const [key, value] of Object.entries(params ?? {})) {
      if (value !== undefined && value !== null && value !== '') {
        httpParams = httpParams.set(key, String(value));
      }
    }
    return httpParams;
  }
}

/** Map any `HttpErrorResponse` onto the documented `ApiError` body. */
export function toApiError(error: HttpErrorResponse): Observable<never> {
  const body = error.error as Partial<ApiError> | null;
  return throwError(
    () =>
      ({
        detail: body?.detail ?? error.message ?? 'The request failed.',
        code: body?.code ?? 'request_failed',
        fields: body?.fields,
      }) satisfies ApiError,
  );
}
