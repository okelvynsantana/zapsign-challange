# Contract — UI Components

**Feature**: [../spec.md](../spec.md) · **Model**: [../data-model.md](../data-model.md)

The layer a component belongs to is decided by its dependencies, not by its size
(Constitution Principle XI). Imports run one way only: atom → molecule → organism → page.

| Layer | May depend on | May not |
|---|---|---|
| Atom | tokens only | domain model, service, HTTP |
| Molecule | types from `core/models/` | service, HTTP, page state |
| Organism | molecules, atoms, services from `core/api/` | another page's internal state |
| Page | organisms | markup that belongs to a lower layer |

---

## Atoms — `app/ui/atoms/`

Behaviourless atoms are **global SCSS classes, not components**, so the per-component style budget
is not spent on duplication: `.badge` `.btn` `.inp` `.sel` `.chip` `.card` `.kv` `.eyebrow` and the
table rules.

That rule governs atoms whose whole substance is *style*. `app-icon` is the one atom whose
substance is *markup* — SVG path geometry, which no stylesheet can express — so it is a component
despite carrying no behaviour. This is the SHOULD in Constitution Principle XI applied, not
bypassed: the reason for the rule (do not duplicate style across components) does not reach a case
where there is no style to duplicate.

| Component | Selector | Input | Output | Notes |
|---|---|---|---|---|
| Icon | `app-icon` | `name` (enumerated), `size` (default 12) | — | single source of every mark; an unknown name is a compile error; renders `aria-hidden` |
| Empty state | `app-empty-state` | `title`, `description`; projects an action | — | `role="status"` so an empty result is announced |
| Confirm dialog | `app-confirm-dialog` | `title`, `message`, `confirmLabel`, `destructive` | `confirmed`, `cancelled` | native `<dialog>` + `showModal()`; the platform supplies focus trap, `Esc` and backdrop (research R-004). Cancel is focused first when `destructive` |
| Progress step | `app-progress-step` | `label`, `hint` | — | the in-progress analysis state; no percentage is claimed |

**Test stub required**: jsdom 20 does not implement `showModal`/`close`. `src/test/setup.ts` stubs
both.

---

## Molecules — `app/ui/molecules/`

Each binds exactly one domain value to atoms. None injects a service. **These carry the mappings in
[data-model.md](../data-model.md) and are the test-first set** (Constitution Principle II).

| Component | Selector | Input | Renders | Preserved `data-testid` |
|---|---|---|---|---|
| Hand-off badge | `app-provider-status-badge` | `status: ProviderStatus` | badge + mark + verbatim label | — |
| Signature state | `app-signature-status` | `status: string \| null` | dot + small-caps verbatim label; unknown values fall through to neutral | — |
| Analysis marker | `app-analysis-marker` | `analysis: DocumentAnalysis \| null` | icon + text; risk ochre, failure red | — |
| Error message | `app-error-message` | `error: ApiError \| null` | `detail`, `code`, per-field errors | — |
| Insight item | `app-insight-item` | `insight: Insight` | risk-flagged insights get the ochre block and a `RISCO` label | — |
| Analysis run item | `app-analysis-run-item` | `run: DocumentAnalysis` | date, outcome, source, risk count | — |

`app-error-message` keeps its current public input (`input<ApiError \| null>`) so no caller
changes; it moves from `shared/` to `ui/molecules/` and `shared/` is removed.

**Required tests, written first**

- every `ProviderStatus` value renders its own mark and its verbatim label;
- a signature value the mapping does not recognise renders neutral, verbatim, without throwing;
- `null` signature and `null` analysis each render their explicit "no state" form;
- a risk-carrying analysis and a failed analysis never produce the same mark or colour family;
- the confirmation dialog emits on confirm and on cancel, and emits nothing on dismissal by `Esc`
  other than `cancelled`.

---

## Organisms

Shared ones live in `app/ui/organisms/`; an organism used by exactly one screen stays in that
screen's folder.

| Component | Location | Responsibility | Preserved `data-testid` |
|---|---|---|---|
| App header | `ui/organisms/` | brand, navigation with active item, sign out | — |
| Documents table | `documents/` | rows, statuses, in-place failure reason, row actions | `document-list`, `document-error`, `document-resync` |
| Detail rail | `documents/` | selected document, signers, hosts the analysis panel | `document-detail` |
| Document form | `documents/` | create and edit, hosts signer rows | `document-company`, `document-name`, `document-pdf`, `document-submit` |
| Analysis panel | `documents/` | the four states of the model, plus history | `analysis-panel`, `analysis-risk`, `analysis-latest`, `analysis-failed`, `analysis-empty`, `analysis-run`, `analysis-history`, `analysis-history-toggle`, `analysis-missing`, `analysis-insights` |
| Signer rows | `signers/` | the signer form array | `signer-add`, `signer-remove` |
| Company form | `companies/` | name plus the credential's secret treatment | `company-name`, `company-token`, `company-submit` |
| Report tiles | `reports/` | the four hero numbers | `report-total`, `report-risk-count` |
| Report distribution | `reports/` | one labelled bar set | `report-provider-status`, `report-signature-status`, `report-risk-insights` |
| Alert group | `alerts/` | one attention group with its count and threshold | `alerts-stalled`, `alerts-risk` |

**Credential rule**: the company form renders only the masked credential. The input starts empty on
edit, and states that leaving it empty keeps the stored value. The raw value is never placed in the
DOM (FR-012, Constitution Principle V).

---

## Pages

`login` · `documents` · `companies` · `reports` · `alerts`. After the split they own routing, data
fetching and orchestration only.

| Page | Preserved `data-testid` |
|---|---|
| documents | `document-empty` |
| companies | `company-empty`, `company-list` |
| alerts | `alerts-empty`, `alerts-refresh` |

---

## Identifier contract

All 35 existing `data-testid` values move with the elements they name; where an identifier named a
container that is now a component, it lands on that component's root. **None is renamed.** An
identifier may be removed only together with the test that reads it, in the same change
(Constitution, Development Workflow).

## Accessibility contract

Applies to every component above.

| Requirement | Rule |
|---|---|
| Focus | `:focus-visible` ring from the token contract; never suppressed |
| Icon-only controls | an accessible name is mandatory |
| Decorative SVG | `aria-hidden="true"` |
| Tables | `<th scope="col">`; the action column has a real accessible header, not an empty cell |
| Field errors | associated by `aria-describedby`, with `aria-invalid` on the field |
| Banners | `role="alert"` |
| Modal layers | native `<dialog>`; focus returns to the invoking control on close |
| Colour | never the sole carrier of meaning |
