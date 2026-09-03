import type { Config } from 'jest';
import { createCjsPreset } from 'jest-preset-angular/presets';

const preset = createCjsPreset({
  tsconfig: '<rootDir>/tsconfig.spec.json',
});

const config: Config = {
  ...preset,
  rootDir: '.',
  testEnvironment: 'jsdom',
  setupFilesAfterEnv: ['<rootDir>/src/test/setup.ts'],
  testMatch: ['<rootDir>/src/**/*.spec.ts'],
  moduleNameMapper: {
    '^src/(.*)$': '<rootDir>/src/$1',
  },
  collectCoverageFrom: [
    'src/app/**/*.ts',
    '!src/app/**/*.spec.ts',
    '!src/main.ts',
    // Type-only modules: interfaces and re-exports, no runtime behaviour to cover.
    '!src/app/core/models/**',
  ],
  coverageDirectory: '<rootDir>/coverage',
  coverageReporters: ['text', 'lcov'],
  // Mirrors the backend gate (Constitution Principle II: >= 80% on the primary flows).
  coverageThreshold: {
    global: { statements: 80, lines: 80 },
  },
};

export default config;
