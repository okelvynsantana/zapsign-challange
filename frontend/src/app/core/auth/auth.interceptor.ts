import { HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';

import { AuthService } from './auth.service';

/**
 * Attach `Authorization: Bearer <access>` to every API call.
 *
 * `/auth/token/` is skipped — sending a stale token while trying to obtain a fresh one
 * only produces confusing 401s.
 */
export const authInterceptor: HttpInterceptorFn = (request, next) => {
  const token = inject(AuthService).token;

  if (!token || request.url.includes('/auth/token')) {
    return next(request);
  }

  return next(
    request.clone({ setHeaders: { Authorization: `Bearer ${token}` } }),
  );
};
