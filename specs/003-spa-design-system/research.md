# Phase 0 — Research: SPA Design System & Interface Layer

**Feature**: [spec.md](spec.md) · **Plan**: [plan.md](plan.md) · **Date**: 2026-09-08

Ten decisions had to be settled before design. Each was verified against the repository or the
package registry rather than assumed; where a check was run, its result is recorded.

---

## R-001 · Font packaging

**Decision**: `@fontsource-variable/ibm-plex-sans` for the sans family (one variable file covers
400/500/600) and `@fontsource/ibm-plex-mono` at static weights 400 and 500 for the mono family.
Import the `latin` subset only. Both are self-hosted; no request leaves the origin.

**Rationale**: Verified against the registry — `@fontsource-variable/ibm-plex-sans@5.3.0` exists,
and **`@fontsource-variable/ibm-plex-mono` does not** (the registry returns not-found). The
asymmetry is not a preference, it is what is published. One variable file replaces three static
sans files; mono has to ship two. Self-hosting is required by Constitution Principle VIII, which
exists because the README promises the whole stack runs with no external network.

**Alternatives considered**:
- *Google Fonts via `<link>`* — one line, no packages, but introduces a third-party origin at
  runtime, breaking the offline guarantee and Principle VIII. Rejected.
- *Static weights for both families* — five woff2 files instead of three, for no benefit where a
  variable build exists. Rejected.
- *Vendoring woff2 files by hand into `public/`* — no dependency at all, but the files become
  unversioned blobs nobody can update or audit. Rejected.

---

## R-002 · How the theme is selected

**Decision**: the theme is **pure CSS**. Tokens are declared on `:root`, redefined under
`@media (prefers-color-scheme: dark)` guarded as `:root:not([data-theme="light"])`, and redefined
again under `:root[data-theme="dark"]`. No JavaScript participates in theme selection, and nothing
is stored.

**Rationale**: with no script involved there is nothing to initialise, nothing to flash on first
paint, and nothing to test in an environment that cannot simulate a display preference. The third
block exists only so that a future manual switch (out of scope here) wins in both directions
without restructuring the token layer. The guarded-media pattern is what keeps a future explicit
"light" choice from being overridden by a dark system setting.

**Alternatives considered**:
- *Read the preference in TypeScript and set a class* — requires `matchMedia`, which jsdom does not
  implement, so every component test would need a mock for a behaviour no component owns. Rejected.
- *Ship only a light theme now* — violates FR-022 and Principle VIII. Rejected.

---

## R-003 · Testing what cannot be simulated

**Decision**: theme correctness is verified by **static assertion over the compiled stylesheet**,
not by component tests: every token named in the contract must appear in the base `:root` block and
in each theme block. Component tests assert structure, copy and accessible names — never computed
colour.

**Rationale**: jsdom does not apply a real cascade or resolve custom properties across media
queries, so a component test asserting a colour would assert the mock, not the product. Verified:
the project runs `testEnvironment: 'jsdom'` with no `matchMedia` mock in `src/test/setup.ts`.
Contrast and dark-mode appearance are verified by the human pass in the quickstart guide, which is
where a human eye is actually required.

**Alternatives considered**:
- *Snapshot the rendered DOM with inline styles* — pins markup, proves nothing about the cascade,
  and breaks on every cosmetic edit. Rejected.
- *Add a browser-based visual regression tool* — a new dependency and a new CI service for a
  seven-screen internal tool. Rejected under Principle III.

---

## R-004 · Modal behaviour for the confirmation dialog and the narrow-window rail

**Decision**: use the native `<dialog>` element with `showModal()`. Add a small stub for
`showModal`/`close` in `src/test/setup.ts`.

**Rationale**: the platform already provides focus trapping, `Esc` to dismiss, inertness of the
background, and the backdrop — all of which FR-019, FR-023 and FR-028 require. Writing them by hand
is roughly forty lines of focus bookkeeping that the browser does correctly for free, and
Principle III says take the simpler thing. Verified: jsdom 20.0.3 ships with this project and
`HTMLDialogElement.prototype.showModal` is `undefined` there, so the stub is required — this is a
known, contained testing cost, not a surprise waiting in CI.

**Alternatives considered**:
- *`@angular/cdk/a11y` FocusTrap* — a well-tested implementation, but it is a new dependency for
  something the platform now does natively, and it invites the rest of the CDK in later. Rejected.
- *Hand-rolled trap over a plain `div`* — more code than the stub it avoids, and easy to get wrong
  in exactly the ways screen-reader users notice. Rejected.

---

## R-005 · Icon strategy

**Decision**: one `IconComponent` atom with an enumerated `name` input, holding every path in a
single lookup. Consumers write `<app-icon name="check" />`; the SVG geometry is authored once.

**Rationale**: the same eight or so marks (check, cross, dashed circle, risk triangle, alert
circle, retry, chevron, lock, ellipsis) recur across every screen, and the status vocabulary of
Principle IX depends on each mark being *identical* everywhere — a hand-copied path that drifts
silently breaks the guarantee. An enumerated name also makes an unknown icon a compile error rather
than an empty box. The component has no domain knowledge, so by the layering rule it is an atom.

**Alternatives considered**:
- *Literal inline SVG at each use site* — no indirection, but the geometry is duplicated dozens of
  times and drift is undetectable. Rejected.
- *An icon package* — banned outright by Principle VIII. Rejected.
- *A sprite sheet referenced by `<use>`* — an extra asset and a same-document-reference footgun,
  for no gain at this count. Rejected.

---

## R-006 · Distribution bars without a charting library

**Decision**: the report distributions are plain elements — a track and a fill sized by percentage
— with the status name and count attached directly to each bar. No chart library, no SVG plot, no
axis, no separate legend.

**Rationale**: the figures show three categories each with a count. A directly attached label is
both more accurate than a legend and satisfies FR-002 and FR-014 in one move, since it means no
figure depends on colour to be read. A charting library would be a large dependency for a bar whose
entire geometry is one percentage width, and it is banned by Principle VIII anyway.

**Alternatives considered**:
- *A charting library* — banned, and disproportionate. Rejected.
- *Hand-written SVG bars* — equivalent output, more markup, worse text reflow. Rejected.

---

## R-007 · Reconciling the detail rail with the existing form state

**Decision**: introduce a single derived rail mode — `'none' | 'detail' | 'form'` — computed from
the existing `selected` and `editingId` signals plus a new `creating` signal. Selecting a document
clears the form; opening the form clears the selection. The existing signals keep their meaning and
their tests.

**Rationale**: FR-017 puts inspection and editing in the same screen region, which makes them
mutually exclusive states of one region — exactly what the current pair of independent signals
cannot express. Verified in `documents.component.ts`: `selected` and `editingId` are set
independently today, so nothing prevents both from being truthy. Deriving one mode makes the
impossible state unrepresentable without discarding the existing state or its coverage.

**Alternatives considered**:
- *Replace both signals with one state object* — a larger refactor of working, tested code for the
  same guarantee. Rejected under Principle III.
- *Let both regions show at once* — contradicts FR-017 and reintroduces the layout problem the
  feature exists to fix. Rejected.

---

## R-008 · Preserving the test identifiers through a component split

**Decision**: each of the 35 existing `data-testid` values moves with the element it names, onto
its new host inside whichever component now renders it. Where an identifier named a container that
becomes a component, it goes on that component's root element. No identifier is renamed, and none
is removed without removing the test that reads it in the same change.

**Rationale**: Constitution's workflow section makes these a stable contract. Verified: 26 of the 35
are read by specs today; the remainder are reserved for tests not yet written. Because the split
moves markup between files rather than changing behaviour, keeping the identifiers is what makes
the whole restructure verifiable — the existing suite becomes the regression net for SC-010.

**Alternatives considered**:
- *Re-derive identifiers per new component* — renames 35 hooks and rewrites 26 assertions, turning
  a verifiable refactor into an unverifiable one. Rejected.

---

## R-009 · Date and time localisation

**Decision**: register the `pt-BR` locale data at bootstrap and set the application's locale
accordingly, then format every date through the framework's date pipe. No hand-rolled formatting,
and no date library.

**Rationale**: FR-021 requires the reader's local convention. Verified: `app.config.ts` registers no
locale today, and `analysis-panel.component.html` prints the raw stored timestamp. The framework
ships the formatting; the only work is registering the data and passing a format.

**Alternatives considered**:
- *A date library* — a dependency for something the framework already does. Rejected.
- *Manual string slicing* — reliably wrong across timezones and month names. Rejected.

---

## R-010 · Keeping component stylesheets inside the budget

**Decision**: the recurring atoms (`.badge`, `.btn`, `.inp`, `.sel`, `.chip`, `.card`, `.kv`,
`.eyebrow`, table rules) are global classes in `styles/_components.scss`. A component stylesheet
carries only that component's layout, and consumes tokens through `var()`.

**Rationale**: verified in `angular.json` — the build budgets are 4 kB warning and 8 kB error per
component stylesheet, and 500 kB warning on the initial bundle. Repeating a button and a badge
definition across a dozen components both breaches the per-component budget and ships the same
bytes many times. Custom properties are inherently global, so a component needs no import to reach
a token; only the class definitions need a home, and that home is global.

**Alternatives considered**:
- *Everything in component stylesheets* — breaches the budget and duplicates CSS. Rejected.
- *Raise the budget* — treats the measurement as the problem. Explicitly rejected by the
  constitution's frontend constraints. Rejected.
- *A utility-class framework* — banned by Principle VIII. Rejected.
