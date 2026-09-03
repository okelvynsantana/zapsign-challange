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
  ],
  coverageDirectory: '<rootDir>/coverage',
  coverageReporters: ['text', 'lcov'],
};

export default config;
