# Phase 1 — Presentation Model

**Feature**: [spec.md](spec.md) · **Plan**: [plan.md](plan.md) · **Research**: [research.md](research.md)

This feature stores nothing and changes no persisted schema. What it does define is a
**presentation model**: how the three status scales the system already records are mapped to
distinct visual forms, and which interface states are legal. The mappings below are the testable
core of the feature — they are the units that get tests written first (Constitution Principle II).

Source of truth for the underlying shapes: `frontend/src/app/core/models/`. Nothing here adds a
field.

---

## 1. Hand-off state — `Document.provider_status`

Our own record of whether the document reached the signature provider. **The only scale rendered as
a filled, bordered badge**, because it is the only one we own and the only one carrying a recovery
action.

| Value | Mark | Token family | Retry offered |
|---|---|---|---|
| `pending_integration` | dashed circle | muted | no — an attempt is in flight; retrying risks a double submission |
| `submitted` | check | ok | yes — refreshes the state from the provider |
| `failed` | cross | bad | yes — this is the retry path the state exists for |

The set is closed *for our own writes*: it is the backend's `ProviderStatus`. An unexpected value
is a defect, not a display case — render it in the muted family and let it be visibly odd rather
than silently mapped to a wrong meaning.

The renderer nonetheless accepts a plain string. The aggregated report keys its hand-off
distribution off whatever the API returned, so a renderer that refused an unknown string would
either fail to compile there or force a cast that discards the fallback that exists precisely for
this case.

**Label**: the value verbatim, in mono (FR-003). Never translated.

**Companion**: when `last_provider_error` is present, its text renders next to the badge together
with the standing statement that the document is stored (FR-005).

---

## 2. Signature state — `Document.status` / `Signer.status`

What the provider reports about signing. **Never a badge** — a 7 px dot plus a mono small-caps
label, because it is read-only information with no action of ours attached.

| Condition | Dot | Meaning |
|---|---|---|
| value indicates signed | filled, ok colour | signed |
| value indicates refused | filled, bad colour | refused |
| any other non-empty value | outline, neutral | in progress, as reported |
| `null` or empty string | no dot, em dash | no state yet |

**The set is open.** This is text the provider chooses, not an enum of ours. The mapping recognises
the signed and refused cases to give them their marks, and **every unrecognised value falls through
to the neutral outline and is displayed verbatim** (FR-004). A new provider value must never break
the row, be hidden, or be reported as an error.

---

## 3. Analysis outcome — `Document.latest_analysis`

A judgement about the document's content. **Icon plus text, no badge.** A risk is a finding about
the contract; a failure is a defect in our processing. They never share a colour or a mark (FR-008).

| Condition | Mark | Token family | Reads as |
|---|---|---|---|
| succeeded, at least one insight flagged `risk` | triangle | warn (ochre) | "N riscos" — needs human judgement |
| succeeded, no risk flagged | check in circle | muted | "sem risco" |
| `state === 'failed'` | circle with bar | bad (red) | "falhou" — needs a retry |
| `null` | none | muted | em dash — never analysed |

Risk count comes from the insights flagged `risk` on the **latest** run only; earlier runs live in
history and never contribute to the marker.

---

## 4. Analysis panel state

A closed set of four. Derived, not stored.

```
        ┌──────────────┐   run    ┌────────────┐
        │ never-run    │─────────▶│ in-progress│
        └──────────────┘          └─────┬──────┘
                                        │
                          ┌─────────────┴─────────────┐
                          ▼                           ▼
                   ┌────────────┐             ┌────────────┐
                   │ produced   │             │ failed     │
                   └─────┬──────┘             └─────┬──────┘
                         │      re-run / retry      │
                         └──────────┬───────────────┘
                                    ▼
                             (back to in-progress)
```

| State | Condition | Primary action |
|---|---|---|
| never-run | `latest_analysis === null` and no request in flight | "Analisar agora" |
| in-progress | a request is in flight | none — the action is disabled and shows progress |
| produced | latest run `succeeded` | "Reanalisar" (secondary) |
| failed | latest run `failed` | **retry is the primary action** (FR-009) |

Runs are append-only: a retry never replaces a row. History renders newest first with the current
run marked.

**Failure reasons** are recorded by the backend and shown both verbatim and in plain language:
`unreachable`, `not_pdf`, `too_large`, `no_text`, `timeout`.

---

## 5. Detail rail mode

The right-hand region has exactly one mode at a time. Derived from the existing `selected` and
`editingId` signals plus a `creating` signal (research R-007).

| Mode | Condition | Region shows |
|---|---|---|
| `none` | nothing selected, not creating, not editing | nothing; the list uses the full width |
| `detail` | a document is selected | its detail and the analysis panel |
| `form` | creating, or editing a document | the create/edit form |

**Invariants**
- `detail` and `form` are mutually exclusive — selecting clears the form, opening the form clears
  the selection.
- Deleting the document currently shown in `detail` returns the region to `none`.
- Below the narrow-window threshold the region becomes a modal layer instead of a column; the mode
  set is unchanged (FR-028).

---

## 6. Theme

| Theme | Selected by | Notes |
|---|---|---|
| light | default, and an explicit light choice | the base token definitions |
| dark | the reader's system preference | redefines tokens only |

No JavaScript participates and nothing is stored (research R-002). Every token has its base
definition on `:root`; a theme block may only redefine (Constitution Principle VIII).

---

## 7. Error presentation

Shape is the existing `ApiError` — `{ detail, code, fields? }`.

| Part | Placement |
|---|---|
| `detail` | the message, in the bad token family |
| `code` | beneath it, mono and small — the technical handle for a support conversation |
| `fields[name]` | attached to the named field, both visually and via its accessible description (FR-025) |

Field errors no longer render as a detached list at the top of the form.
