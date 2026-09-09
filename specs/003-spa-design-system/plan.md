# Implementation Plan: SPA Design System & Interface Layer

**Branch**: `003-spa-design-system` | **Date**: 2026-09-08 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/003-spa-design-system/spec.md`

## Summary

The SPA is behaviourally complete and visually absent: the global stylesheet is empty, no
component stylesheet exists, and the interface renders in browser defaults with English copy.
This feature builds the interface layer on top of the existing, unchanged application.

The approach: a global token layer carries every colour, type step, spacing step, radius and
control height for a light and a dark theme; three status vocabularies are implemented as
separate molecule components so that the hand-off state, the signature state and the analysis
outcome can never be confused for one another; the seven screens are rebuilt from those pieces
using the atomic layers the constitution mandates. Fonts are self-hosted so the application keeps
working with no external network. No backend file is touched and no service contract changes —
this layer consumes what already exists.

## Technical Context

**Language/Version**: TypeScript 5.7 · Angular 19.2 (standalone components, signals, built-in
control flow)

**Primary Dependencies**: none added for behaviour. Two font-asset packages are added
(`@fontsource-variable/ibm-plex-sans`, `@fontsource/ibm-plex-mono`); they ship woff2 files and
`@font-face` declarations only, no runtime code. No component library, CSS framework, or icon
package — forbidden by Constitution Principle VIII.

**Storage**: N/A. This feature persists nothing. The theme follows the reader's system preference
and is not stored.

**Testing**: Jest 29 with `jest-preset-angular` 14 on jsdom; existing suite of 74 tests across 16
suites, coverage gate at 80%.

**Target Platform**: evergreen desktop browsers, served same-origin behind the existing nginx
container.

**Project Type**: web application — this feature is frontend-only.

**Performance Goals**: initial bundle stays under the configured 500 kB warning; no component
stylesheet exceeds the configured 4 kB warning; a single font swap on first paint and no further
layout shift.

**Constraints**: no request to a third-party origin at runtime; no change under `backend/`; every
existing `data-testid` preserved; coverage never drops below 80%; the page never scrolls
horizontally.

**Scale/Scope**: 7 screens, ~20 components across 4 atomic layers, 2 themes, ~35 preserved test
identifiers.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

| Gate | Principle | Pre-research | Post-design |
|---|---|---|---|
| No third-party SDK or HTTP call outside the integration seam | I | PASS — frontend only, calls the existing typed services | PASS |
| Status-mapping and rendering logic pinned by tests written first | II | PASS (commitment) | PASS — the three status molecules and the confirmation dialog are the test-first set |
| Coverage stays at or above 80% | II | PASS | PASS |
| No speculative abstraction; simplest thing that works | III | PASS — no state library, no CDK, no CSS framework | PASS — research R-004 replaced the hand-rolled focus trap with the native `<dialog>` element: zero lines and zero dependencies, at the cost of one test stub |
| Third-party failure never degrades the record | IV | PASS — the failure states are the point of the feature | PASS |
| Credential never exposed | V | PASS — only the masked form is ever rendered | PASS |
| No stored-data change | VI | PASS — nothing persisted | PASS |
| Runs with no external network | VII, VIII | PASS — fonts self-hosted | PASS |
| Every visual value resolves from a token; both themes defined from `:root` | VIII | PASS | PASS |
| No component library, CSS framework, or icon package; icons are inline SVG; no emoji | VIII | PASS | PASS |
| Three status scales visually distinct; nothing communicated by colour alone | IX | PASS — the feature's core requirement | PASS |
| API-recorded values displayed verbatim | IX | PASS | PASS |
| AA contrast in both themes, keyboard operable, accessible names | X | PASS | PASS |
| Interface copy in Brazilian Portuguese | X | PASS | PASS |
| Atomic layers with one-way imports | XI | PASS | PASS |
| Behaviourless atoms are global SCSS, not components | XI, VIII | PASS | PASS |

**Icon atom clearance**: Principle XI says an atom with no behaviour *should* be a global SCSS
class. `app-icon` is a component anyway, because its substance is SVG geometry rather than style
and a stylesheet cannot hold it. The rule's purpose — not duplicating style across components — is
untouched. Recorded here so a reviewer reads it as a considered application of the rule rather than
a lapse.

**Font packages clearance**: Principle VIII bans a component library, a CSS framework and an icon
package, and separately *requires* self-hosted fonts. Two font-asset packages are therefore not a
violation of the dependency ban — they are how the self-hosting requirement is met. They ship no
runtime code and add no API surface.

## Project Structure

### Documentation (this feature)

```text
specs/003-spa-design-system/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output — the presentation model
├── quickstart.md        # Phase 1 output — validation guide
├── contracts/           # Phase 1 output
│   ├── design-tokens.md
│   └── ui-components.md
├── checklists/
│   └── requirements.md  # written by /speckit-specify
├── spec.md
└── tasks.md             # Phase 2 output (/speckit-tasks — not created here)
```

### Source Code (repository root)

This feature touches only `frontend/`. `backend/` and `deploy/` are untouched.

```text
frontend/
├── package.json                       + 2 font-asset packages
├── src/
│   ├── index.html                     lang, title, theme-color
│   ├── styles.scss                    imports the partials below
│   ├── styles/
│   │   ├── _tokens.scss               colour, type, spacing, radius, heights — both themes
│   │   ├── _reset.scss                box-sizing, margins, lists, focus ring
│   │   ├── _typography.scss           @font-face imports, scale, .mono, .eyebrow
│   │   └── _components.scss           .badge .btn .inp .sel .chip .card .kv, table
│   └── app/
│       ├── app.config.ts              + pt-BR locale registration
│       ├── app.component.*            uses the header organism
│       ├── ui/
│       │   ├── atoms/                 empty-state · confirm-dialog · progress-step · icon
│       │   ├── molecules/             provider-status-badge · signature-status ·
│       │   │                          analysis-marker · error-message · insight-item ·
│       │   │                          analysis-run-item
│       │   └── organisms/             app-header
│       ├── documents/                 page + documents-table · detail-rail · document-form ·
│       │                              analysis-panel
│       ├── companies/                 page + company-form
│       ├── reports/                   page + report-tiles · report-distribution
│       ├── alerts/                    page + alert-group
│       ├── signers/                   signer-rows (organism)
│       ├── core/                      unchanged — models, services, auth
│       └── shared/                    REMOVED; its one component becomes a molecule
```

**Structure Decision**: frontend-only, layered per Constitution Principle XI. Reusable pieces live
under `frontend/src/app/ui/{atoms,molecules,organisms}/`; an organism used by exactly one screen
stays in that screen's feature folder, so `ui/organisms/` holds only what is genuinely shared.
`core/` keeps models, services and guards and belongs to no visual layer. The existing `shared/`
folder is removed because its single occupant, the error message component, is a molecule by the
layering rule.

## Complexity Tracking

No Constitution Check gate failed, so no justification is required. The table is intentionally
empty.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| — | — | — |
