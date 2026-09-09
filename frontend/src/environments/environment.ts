/**
 * Default (production) environment.
 *
 * `apiBaseUrl` is a same-origin relative path: the nginx runtime image proxies
 * `/api/` through to the Django backend, so no CORS or absolute host is needed.
 */
export const environment: { production: boolean; apiBaseUrl: string } = {
  production: true,
  apiBaseUrl: '/api',
};
