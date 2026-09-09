import { readFileSync } from 'node:fs';
import { join } from 'node:path';

/**
 * Guard over the token layer.
 *
 * jsdom applies no real cascade and resolves no custom property across a media
 * query, so a component test asserting a colour would assert the mock rather
 * than the product (research R-003). What *can* be verified here is the source:
 * that every token exists, and that the theme blocks only ever redefine.
 *
 * Contract: specs/003-spa-design-system/contracts/design-tokens.md
 */
const source = readFileSync(join(__dirname, '_tokens.scss'), 'utf8');

/** Tokens that must be redefined by every theme. */
const THEMED = [
  '--paper', '--surface', '--surface-2',
  '--ink', '--ink-2', '--ink-3',
  '--line', '--line-2',
  '--accent', '--accent-ink', '--accent-soft', '--on-accent',
  '--ok-ink', '--ok-bg', '--ok-line',
  '--warn-ink', '--warn-bg', '--warn-line',
  '--bad-ink', '--bad-bg', '--bad-line',
  '--mut-ink', '--mut-bg', '--mut-line',
  '--sig-signed', '--sig-refused',
  '--scrim',
  '--inverse-surface', '--inverse-line',
];

/** Tokens that are theme-invariant: they are declared once, on :root. */
const INVARIANT = [
  '--font-sans', '--font-mono',
  '--space-1', '--space-2', '--space-3', '--space-4', '--space-5', '--space-6',
  '--radius-badge', '--radius-control', '--radius-card',
  '--h-badge', '--h-btn-sm', '--h-btn', '--h-field', '--h-row', '--h-header',
  '--inverse-ink', '--inverse-ink-2', '--inverse-bad',
  '--rail-width', '--page-pad-y', '--page-pad-x',
];

/** Slice the file into its three declaration blocks. */
function block(startMarker: string): string {
  const start = source.indexOf(startMarker);
  expect(start).toBeGreaterThanOrEqual(0);
  const open = source.indexOf('{', start);
  let depth = 0;
  for (let i = open; i < source.length; i += 1) {
    if (source[i] === '{') depth += 1;
    if (source[i] === '}') {
      depth -= 1;
      if (depth === 0) return source.slice(open, i);
    }
  }
  throw new Error(`unbalanced block for ${startMarker}`);
}

describe('design tokens', () => {
  const base = block(':root {');
  const mediaDark = block("@media (prefers-color-scheme: dark)");
  const attrDark = block(":root[data-theme='dark']");

  it.each([...THEMED, ...INVARIANT])('declares %s on :root', (token) => {
    expect(base).toContain(`${token}:`);
  });

  it.each(THEMED)('redefines %s under the guarded media block', (token) => {
    expect(mediaDark).toContain(`${token}:`);
  });

  it.each(THEMED)('redefines %s under [data-theme="dark"]', (token) => {
    expect(attrDark).toContain(`${token}:`);
  });

  it('guards the media block so an explicit light choice can win', () => {
    expect(mediaDark).toContain(":root:not([data-theme='light'])");
  });

  it('introduces no token that is missing from the base block', () => {
    const declared = (text: string) => [...text.matchAll(/(--[a-z0-9-]+):/g)].map((m) => m[1]);
    const baseTokens = new Set(declared(base));
    for (const token of [...declared(mediaDark), ...declared(attrDark)]) {
      // A colour whose only definition lives in a theme block is a defect
      // (Constitution Principle VIII).
      expect(baseTokens.has(token)).toBe(true);
    }
  });
});
