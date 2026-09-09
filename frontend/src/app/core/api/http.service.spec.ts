import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';

import { ApiError } from '../models/api.model';
import { HttpService } from './http.service';

describe('HttpService', () => {
  let http: HttpService;
  let backend: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    http = TestBed.inject(HttpService);
    backend = TestBed.inject(HttpTestingController);
  });

  afterEach(() => backend.verify());

  it('prefixes every path with the configured API base URL', () => {
    http.get('/documents/').subscribe();

    const request = backend.expectOne((r) => r.url.endsWith('/api/documents/'));
    request.flush({});
  });

  it('drops empty, null and undefined query parameters', () => {
    http.get('/documents/', { status: 'pending', company: '', page: undefined }).subscribe();

    const request = backend.expectOne((r) => r.url.endsWith('/api/documents/'));
    expect(request.request.params.get('status')).toBe('pending');
    expect(request.request.params.has('company')).toBe(false);
    expect(request.request.params.has('page')).toBe(false);
    request.flush({});
  });

  it('serialises non-string query parameters', () => {
    http.get('/documents/', { page: 2, has_risk: true }).subscribe();

    const request = backend.expectOne((r) => r.url.endsWith('/api/documents/'));
    expect(request.request.params.get('page')).toBe('2');
    expect(request.request.params.get('has_risk')).toBe('true');
    request.flush({});
  });

  it('sends the body on POST', () => {
    http.post('/documents/', { name: 'x' }).subscribe();

    const request = backend.expectOne((r) => r.method === 'POST');
    expect(request.request.body).toEqual({ name: 'x' });
    request.flush({});
  });

  it('sends the body on PATCH', () => {
    http.patch('/documents/d1/', { name: 'y' }).subscribe();

    const request = backend.expectOne((r) => r.method === 'PATCH');
    expect(request.request.body).toEqual({ name: 'y' });
    request.flush({});
  });

  it('issues a DELETE', () => {
    http.delete('/documents/d1/').subscribe();

    backend.expectOne((r) => r.method === 'DELETE').flush(null, { status: 204, statusText: '' });
  });

  it('passes the backend error body through unchanged', (done) => {
    http.get('/documents/').subscribe({
      error: (err: ApiError) => {
        expect(err).toEqual({
          detail: 'The request payload failed validation.',
          code: 'validation_error',
          fields: { pdf_url: ['Enter a valid URL.'] },
        });
        done();
      },
    });

    backend.expectOne(() => true).flush(
      {
        detail: 'The request payload failed validation.',
        code: 'validation_error',
        fields: { pdf_url: ['Enter a valid URL.'] },
      },
      { status: 400, statusText: 'Bad Request' },
    );
  });

  it('synthesises an ApiError when the failure has no body', (done) => {
    http.get('/documents/').subscribe({
      error: (err: ApiError) => {
        expect(err.code).toBe('request_failed');
        expect(err.detail).toBeTruthy();
        done();
      },
    });

    backend.expectOne(() => true).error(new ProgressEvent('network error'));
  });
});
