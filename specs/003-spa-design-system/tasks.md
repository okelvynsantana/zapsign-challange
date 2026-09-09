---

description: "Task list for the SPA design system & interface layer"
---

# Tasks: SPA Design System & Interface Layer

**Input**: Design documents from `/specs/003-spa-design-system/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md), [data-model.md](data-model.md), [contracts/](contracts/)

**Tests**: Test tasks ARE included, but scoped. Constitution Principle II requires test-first only
for logic that carries risk; here that is the status mappings, the error presentation and the
confirmation dialog — the set named in [contracts/ui-components.md](contracts/ui-components.md).
Screen layout is verified by the [quickstart.md](quickstart.md) walkthrough, not by unit tests that
would only pin markup.

**Organization**: Tasks are grouped by user story. Note the mapping caveat under **Notes** — the
spec's stories are cross-cutting *qualities* rather than screens, so screen work is assigned to the
story whose guarantee it delivers.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to
- Paths are repository-relative; this feature touches only `frontend/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: dependencies, directories and shell configuration that everything else sits inside

- [X] T001 Add `@fontsource-variable/ibm-plex-sans` and `@fontsource/ibm-plex-mono` to dependencies in `frontend/package.json` (research R-001: no variable build exists for the mono family, so it ships static weights 400 and 500)
- [X] T002 [P] Create the empty partials `_tokens.scss`, `_reset.scss`, `_typography.scss`, `_components.scss` in `frontend/src/styles/` and import them in that order from `frontend/src/styles.scss`
- [X] T003 [P] Create the layer directories `atoms/`, `molecules/`, `organisms/` under `frontend/src/app/ui/` per the structure in `plan.md`
- [X] T004 [P] Register the `pt-BR` locale data and set `LOCALE_ID` in `frontend/src/app/app.config.ts` (research R-009)
- [X] T005 [P] Stub `HTMLDialogElement.prototype.showModal` and `.close` in `frontend/src/test/setup.ts` — verified absent in the jsdom 20.0.3 this project runs (research R-004)
- [X] T006 [P] Set `lang="pt-BR"`, the real `<title>`, and `theme-color` for both themes in `frontend/src/index.html`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: the token layer and the shared atoms. Nothing else can be styled until these exist.

**⚠️ CRITICAL**: no user story work begins until this phase is complete

- [X] T007 Declare every token from [contracts/design-tokens.md](contracts/design-tokens.md) in `frontend/src/styles/_tokens.scss` — base definitions on `:root`, then the two redefinition blocks (`@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) }` and `:root[data-theme="dark"]`). No token may have its only definition inside a theme block.
- [X] T008 [P] Write the reset and the single `:focus-visible` ring in `frontend/src/styles/_reset.scss`
- [X] T009 [P] Import the font faces and declare the type scale, `.mono` and `.eyebrow` in `frontend/src/styles/_typography.scss` — latin subset only, `font-display: swap`, full fallback stack on both families
- [X] T010 Write the global atom classes `.badge .btn .inp .sel .chip .card .kv` and the table rules in `frontend/src/styles/_components.scss` (research R-010: these are global precisely so no component stylesheet duplicates them)
- [X] T011 [P] Create the icon atom with an enumerated `name` input in `frontend/src/app/ui/atoms/icon.component.ts` — every mark authored once, rendered `aria-hidden` (research R-005)
- [X] T012 [P] Create the empty-state atom with `role="status"` in `frontend/src/app/ui/atoms/empty-state.component.ts`
- [X] T013 Write the token guard test in `frontend/src/styles/tokens.spec.ts` — assert every token named in the contract appears in the base block and in each theme block (research R-003: the cascade cannot be verified in jsdom, so verify the source)
- [X] T014 Run `npm run build` from `frontend/` and confirm no budget warning against the limits in `frontend/angular.json`

**Checkpoint**: tokens and atoms exist; the story phases can begin

---

## Phase 3: User Story 1 — Tell the two statuses apart (Priority: P1) 🎯 MVP

**Goal**: the hand-off state, the signature state and the analysis outcome become three
unmistakable visual forms, on both surfaces that show them: the document list and the report
distributions.

**Independent Test**: show the document list to someone who has never used the system and ask, per
row, whether the document reached the provider and whether it is signed — then repeat with the
display in grayscale.

### Tests for User Story 1 ⚠️ write first, watch them fail

- [X] T015 [P] [US1] Test every `ProviderStatus` value renders its own mark and its verbatim label in `frontend/src/app/ui/molecules/provider-status-badge.component.spec.ts`
- [X] T016 [P] [US1] Test signed, refused, an unrecognised value and `null` in `frontend/src/app/ui/molecules/signature-status.component.spec.ts` — the unrecognised case must render neutral and verbatim without throwing (FR-004)
- [X] T017 [P] [US1] Test risk-carrying, risk-free, failed and `null` analyses in `frontend/src/app/ui/molecules/analysis-marker.component.spec.ts` — assert the risk and failure cases share neither mark nor colour family (FR-008)

### Implementation for User Story 1

- [X] T018 [P] [US1] Implement the hand-off badge per [data-model.md](data-model.md) §1 in `frontend/src/app/ui/molecules/provider-status-badge.component.ts`
- [X] T019 [P] [US1] Implement the signature marker per §2, with the open-value fallthrough, in `frontend/src/app/ui/molecules/signature-status.component.ts`
- [X] T020 [P] [US1] Implement the analysis marker per §3 in `frontend/src/app/ui/molecules/analysis-marker.component.ts`
- [X] T021 [US1] Replace the raw status columns with the three molecules in `frontend/src/app/documents/documents.component.html`, preserving `document-list` and `analysis-risk`
- [X] T022 [US1] Style the document list — rows, columns, selected row, the name cell with its metadata line — in `frontend/src/app/documents/documents.component.scss`
- [X] T023 [US1] Rebuild the report tiles and the labelled distribution bars in `frontend/src/app/reports/report-tiles.component.*` and `frontend/src/app/reports/report-distribution.component.*`, each bar carrying its own name and count (FR-014), preserving `report-total`, `report-risk-count`, `report-provider-status`, `report-signature-status`, `report-risk-insights`
- [X] T024 [US1] Compose the two organisms into `frontend/src/app/reports/reports.component.html` and remove the list markup they replace

**Checkpoint**: the list and the reports are legible and colour-independent. This is the MVP.

---

## Phase 4: User Story 2 — Failure is recoverable (Priority: P2)

**Goal**: a failed hand-off shows its cause in place with its retry, a refused organization removal
explains itself, and the attention queue exists.

**Independent Test**: put a document into the failed state and ask an operator to explain the cause
and retry, using only the list; then try to delete an organization that owns documents.

### Tests for User Story 2 ⚠️ write first

- [X] T025 [P] [US2] Test `detail`, `code` and per-field association in `frontend/src/app/ui/molecules/error-message.component.spec.ts` — assert the field error is reachable from the field via `aria-describedby` (FR-025). Move the existing spec from `frontend/src/app/shared/`

### Implementation for User Story 2

- [X] T026 [US2] Rewrite the error message molecule at `frontend/src/app/ui/molecules/error-message.component.ts`, keeping its `input<ApiError | null>` signature, and delete `frontend/src/app/shared/error-message.component.ts`
- [X] T027 [US2] Update every import of `ErrorMessageComponent` across `frontend/src/app/{documents,companies,reports,alerts}/` and `frontend/src/app/core/auth/`
- [X] T028 [US2] Render `last_provider_error` inside the document name cell with its icon and the standing "the document is stored" statement in `frontend/src/app/documents/documents.component.html`, preserving `document-error`
- [X] T029 [US2] Present the retry as a row action gated on `canResync()` in `frontend/src/app/documents/documents.component.html`, preserving `document-resync` (FR-006)
- [X] T030 [US2] Rebuild the login screen with its two-column layout and the credential-error banner in `frontend/src/app/core/auth/login.component.ts`, extracting the inline template to `login.component.html`
- [X] T031 [US2] Build the company form organism with the credential's secret treatment — masked value only, empty on edit, the "leaving it empty keeps the stored token" statement — in `frontend/src/app/companies/company-form.component.*`, preserving `company-name`, `company-token`, `company-submit` (FR-012)
- [X] T032 [US2] Present the deletion refusal with its cause, its code and the way forward in `frontend/src/app/companies/companies.component.html`, preserving `company-list` and `company-empty` (FR-007)
- [X] T033 [US2] Build the alert group organism — count, threshold, per-item action — in `frontend/src/app/alerts/alert-group.component.*`, preserving `alerts-stalled` and `alerts-risk`
- [X] T034 [US2] Compose the two groups and the affirmative empty state into `frontend/src/app/alerts/alerts.component.html`, preserving `alerts-empty` and `alerts-refresh` (FR-013)
- [X] T035 [US2] Build the application header organism in `frontend/src/app/ui/organisms/app-header.component.*` and use it from `frontend/src/app/app.component.html`

**Checkpoint**: every failure path explains itself and offers its way out

---

## Phase 5: User Story 3 — Risk is not breakage (Priority: P3)

**Goal**: the analysis panel gets its four states, and a contract risk never looks like a
processing defect.

**Independent Test**: show one document carrying a risk finding and one whose analysis failed, and
ask which needs a lawyer and which needs a retry.

### Tests for User Story 3 ⚠️ write first

- [X] T036 [P] [US3] Test the risk and non-risk renderings in `frontend/src/app/ui/molecules/insight-item.component.spec.ts`
- [X] T037 [P] [US3] Test the four panel states resolve correctly from `latest_analysis` and the in-flight flag in `frontend/src/app/documents/analysis-panel.component.spec.ts`, extending the existing spec and preserving its assertions

### Implementation for User Story 3

- [X] T038 [P] [US3] Implement the insight molecule — ochre block, triangle, `RISCO` label for flagged insights — in `frontend/src/app/ui/molecules/insight-item.component.ts`
- [X] T039 [P] [US3] Implement the history row molecule in `frontend/src/app/ui/molecules/analysis-run-item.component.ts`
- [X] T040 [P] [US3] Implement the progress-step atom in `frontend/src/app/ui/atoms/progress-step.component.ts`
- [X] T041 [US3] Implement the produced state — summary, missing-topic chips, insight list, provenance footer — in `frontend/src/app/documents/analysis-panel.component.html`, preserving `analysis-latest`, `analysis-missing`, `analysis-insights`
- [X] T042 [US3] Implement the failed state with the verbatim reason, its Portuguese explanation for each of the five recorded reasons, the "document unaffected" statement, and retry as the primary action, in `frontend/src/app/documents/analysis-panel.component.html`, preserving `analysis-failed` (FR-009)
- [X] T043 [US3] Implement the never-run and in-progress states, including the stated time ceiling, in `frontend/src/app/documents/analysis-panel.component.{ts,html}`, preserving `analysis-empty` and `analysis-run` (FR-010)
- [X] T044 [US3] Render the history newest-first with the current run marked, in `frontend/src/app/documents/analysis-panel.component.html`, preserving `analysis-history` and `analysis-history-toggle` (FR-011)
- [X] T045 [US3] Style the panel and its four states in `frontend/src/app/documents/analysis-panel.component.scss`

**Checkpoint**: the analysis drives action instead of decorating the screen

---

## Phase 6: User Story 4 — Working a long list (Priority: P4)

**Goal**: narrowing, paging, and one screen region shared by inspection and creation, with nothing
destroyed without confirmation.

**Independent Test**: load several hundred documents; find one, inspect it, create another, delete
one — timing each and watching whether the list ever leaves the screen.

**⚠️ This is the cut line.** Deferring this phase leaves Stories 1–3 complete and shippable; the
screens keep their current stacked layout, styled.

### Tests for User Story 4 ⚠️ write first

- [X] T046 [P] [US4] Test confirm, cancel, and dismissal by `Esc` in `frontend/src/app/ui/atoms/confirm-dialog.component.spec.ts` (relies on the T005 stub)

### Implementation for User Story 4

- [X] T047 [US4] Implement the confirmation dialog over a native `<dialog>` in `frontend/src/app/ui/atoms/confirm-dialog.component.ts` — the platform supplies the focus trap, `Esc` and the backdrop (research R-004)
- [X] T048 [US4] Add the `creating` signal and derive `railMode` from it plus `selected` and `editingId` in `frontend/src/app/documents/documents.component.ts`, enforcing the mutual exclusion in [data-model.md](data-model.md) §5 (research R-007)
- [X] T049 [P] [US4] Extract the table organism to `frontend/src/app/documents/documents-table.component.*`, carrying `document-list`, `document-error`, `document-resync`
- [X] T050 [P] [US4] Extract the detail rail organism to `frontend/src/app/documents/document-detail-rail.component.*`, carrying `document-detail` and hosting the analysis panel
- [X] T051 [P] [US4] Extract the form organism to `frontend/src/app/documents/document-form.component.*`, carrying `document-company`, `document-name`, `document-pdf`, `document-submit`
- [X] T052 [US4] Compose the two-column layout with the 452 px rail and tie the selected row to the rail, in `frontend/src/app/documents/documents.component.{html,scss}` (FR-017, FR-018)
- [X] T053 [US4] Add the filter row and pass the selection to `DocumentService.list()` in `frontend/src/app/documents/documents.component.{ts,html}` — the service already accepts `DocumentFilters` (FR-015)
- [X] T054 [US4] Add paging from `count`, `next` and `previous` in `frontend/src/app/documents/documents.component.{ts,html}` (FR-016)
- [X] T055 [US4] Require confirmation before destroying, in `frontend/src/app/documents/documents.component.ts` and `frontend/src/app/companies/companies.component.ts` (FR-019)
- [X] T056 [US4] Restyle the signer rows organism in `frontend/src/app/signers/signer-rows.component.*`, preserving `signer-add` and `signer-remove`

**Checkpoint**: the list is workable at volume and nothing is destroyed by accident

---

## Phase 7: User Story 5 — Language, theme, keyboard (Priority: P5)

**Goal**: the interface reads in Portuguese, renders in both themes, and works without a mouse.

**Independent Test**: walk every screen in dark appearance, then again on the keyboard alone, then
read every string.

- [X] T057 [P] [US5] Translate the copy in `frontend/src/app/documents/*.html` and `frontend/src/app/signers/*`, leaving every API-recorded value verbatim in mono (FR-003, FR-020)
- [X] T058 [P] [US5] Translate the copy in `frontend/src/app/companies/*.html` and `frontend/src/app/core/auth/login.component.html`
- [X] T059 [P] [US5] Translate the copy in `frontend/src/app/reports/*.html` and `frontend/src/app/alerts/*.html`
- [X] T060 [US5] Update the four copy assertions the translation invalidates: `frontend/src/app/alerts/alerts.component.spec.ts:66`, `frontend/src/app/reports/reports.component.spec.ts:81`, and both in `frontend/src/app/ui/molecules/error-message.component.spec.ts` — do not touch `login.component.spec.ts:57`, which asserts a backend `detail`, not interface copy
- [X] T061 [US5] Format every displayed date through the date pipe in `frontend/src/app/documents/analysis-panel.component.html` and every other timestamp site (FR-021)
- [X] T062 [US5] Make the rail a dismissable modal layer below the narrow-window threshold, in `frontend/src/app/documents/documents.component.scss` and the rail organism (FR-028)
- [X] T063 [US5] Add accessible names to every icon-only control and `scope="col"` plus a real header for the action column, across `frontend/src/app/**/*.html` (FR-024, and the accessibility contract)
- [X] T064 [US5] Add the `prefers-reduced-motion` suppression in `frontend/src/styles/_reset.scss` (FR-029)
- [X] T065 [US5] Walk all seven screens in dark appearance and fix every element that kept a light ground — the theme pass in [quickstart.md](quickstart.md) Story 5 step 2
- [ ] T066 [US5] Walk all seven screens on the keyboard alone and fix every unreachable action or invisible focus across `frontend/src/app/**/*.{html,scss}` — the pass in [quickstart.md](quickstart.md) Story 5 step 4

**Checkpoint**: the accessibility and localization floor is met

---

## Phase 8: Polish & Cross-Cutting Concerns

- [X] T067 Delete the now-empty `frontend/src/app/shared/` directory
- [X] T068 Verify no component imports from a higher atomic layer than its own across `frontend/src/app/` (Constitution Principle XI)
- [X] T069 [P] Confirm no colour, size or spacing literal survives outside `frontend/src/styles/_tokens.scss`, excepting the theme-invariant values documented in [contracts/design-tokens.md](contracts/design-tokens.md)
- [X] T070 [P] Add the visual-system section and the font provenance to `README.md`
- [X] T071 Run `npm run lint && npm run typecheck && npm run test:cov && npm run build` from `frontend/` — coverage at or above 80%, no budget warning
- [ ] T072 Reload every screen with the network panel open and confirm no request reaches a third-party origin — the offline guarantee in [quickstart.md](quickstart.md)
- [ ] T073 Run the full [quickstart.md](quickstart.md) walkthrough and tick the definition of done in `PRD-DESIGN.md` §18

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: no dependencies
- **Foundational (Phase 2)**: needs Setup — **blocks every story**
- **US1 (Phase 3)**: needs Foundational
- **US2 (Phase 4)**: needs Foundational. Independent of US1
- **US3 (Phase 5)**: needs Foundational. Independent of US1 and US2
- **US4 (Phase 6)**: needs Foundational. T049–T051 extract markup that US1–US3 wrote, so if those
  stories are being built, US4 should follow them rather than race them
- **US5 (Phase 7)**: needs whichever screens exist — it is a pass over what has been built
- **Polish (Phase 8)**: needs every story that will ship

### Within Each Story

- Tests are written and failing before the implementation they cover
- Molecules before the screens that compose them
- Screen composition before styling

### Parallel Opportunities

- T002–T006 all touch different files
- T008, T009, T011, T012 are independent within Foundational
- T015–T017 (all three status mapping tests) run together, then T018–T020 together
- T036, T037 together, then T038–T040 together
- T049–T051 extract into three separate new files
- T057–T059 are three disjoint sets of templates

---

## Parallel Example: User Story 1

```bash
# Write the three mapping tests together — different files, no shared state:
Task: "Test every ProviderStatus value in provider-status-badge.component.spec.ts"
Task: "Test signed/refused/unknown/null in signature-status.component.spec.ts"
Task: "Test risk/no-risk/failed/null in analysis-marker.component.spec.ts"

# Then implement the three molecules together:
Task: "Implement the hand-off badge in provider-status-badge.component.ts"
Task: "Implement the signature marker in signature-status.component.ts"
Task: "Implement the analysis marker in analysis-marker.component.ts"
```

---

## Implementation Strategy

### MVP (User Story 1 only)

1. Phase 1 Setup
2. Phase 2 Foundational — blocks everything
3. Phase 3 US1
4. **Stop and validate**: run the grayscale check in quickstart Story 1. If every status survives
   the loss of colour, the MVP holds.

At this point the list and the reports are legible and trustworthy, on a styled foundation, with
every existing behaviour intact.

### Incremental delivery

1. Setup + Foundational → foundation ready
2. + US1 → statuses legible → **MVP**
3. + US2 → failures explain themselves
4. + US3 → risk separated from breakage
5. + US4 → the list works at volume *(the cut line — deferring this loses no earlier guarantee)*
6. + US5 → language, themes, keyboard
7. Polish

---

## Notes

- **Story-to-screen mapping.** The spec's stories are cross-cutting qualities, not screens, so no
  story owns "the reports screen". Screen work is assigned to the story whose guarantee it
  delivers: the report distributions land in US1 because they are the status vocabulary and carry
  FR-002 and FR-014; the alerts and organization screens land in US2 because they are where failure
  and attention surface. If you would rather see one screen finished at a time than one guarantee
  at a time, re-cut the phases — the task list, not the spec, is what changes.
- **PRD phase divergence.** `PRD-DESIGN.md` §14 puts the two-column rail in its Fase 3; the spec
  puts FR-017 and FR-018 in User Story 4, so the rail is built in Phase 6 here. The spec governs.
  The consequence is deliberate: US1–US3 improve the existing layout in place, so the cut line
  falls after a genuinely shippable increment.
- All 35 existing `data-testid` values are named in the task that moves them. None is renamed.
- The 74 existing tests are the regression net for SC-010. If a test has to be weakened to pass,
  a capability was lost — stop and find out which.
- `[P]` means different files and no dependency on unfinished work.
- Commit per task or per logical group; stop at any checkpoint to validate the story on its own.
