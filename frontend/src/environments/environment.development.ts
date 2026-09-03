/**
 * Development environment (swapped in by the `development` build configuration
 * via `fileReplacements` in angular.json).
 *
 * Points straight at the Django dev server running on port 8000.
 */
export const environment: { production: boolean; apiBaseUrl: string } = {
  production: false,
  apiBaseUrl: 'http://localhost:8000/api',
};
