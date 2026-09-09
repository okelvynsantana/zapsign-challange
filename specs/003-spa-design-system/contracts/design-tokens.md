# Contract — Design Tokens

**Feature**: [../spec.md](../spec.md) · **Consumers**: every stylesheet in `frontend/src/`

This is the authoritative list. A value that is not here does not belong in a component
stylesheet (Constitution Principle VIII).

## Declaration rules

1. Every token has its base definition in `:root`. A theme block may only **redefine** an existing
   token, never introduce one.
2. The dark theme is declared twice, deliberately:
   ```scss
   :root { /* base — light */ }
   @media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) { /* redefine */ } }
   :root[data-theme="dark"] { /* redefine */ }
   ```
   The guard on the media block is what lets a future explicit light choice win over a dark system
   setting; the third block lets a future explicit dark choice win over a light one. Neither switch
   ships in this feature — the structure does, so adding one later touches no component.
3. A colour whose only definition lives inside a media query or a `[data-theme]` block is a defect.
4. Component stylesheets reference tokens through `var()`. Custom properties are global; no import
   is needed.

## Colour

| Token | Light | Dark | Role |
|---|---|---|---|
| `--paper` | `#FAF9F7` | `#141311` | page ground |
| `--surface` | `#FFFFFF` | `#1C1B18` | card, table, rail |
| `--surface-2` | `#F3F1ED` | `#23221E` | subtle fill, table footer |
| `--ink` | `#1A1917` | `#F0EDE7` | primary text |
| `--ink-2` | `#5C5852` | `#ADA79E` | secondary text |
| `--ink-3` | `#8A857D` | `#7C766E` | label, placeholder, metadata |
| `--line` | `#E3E0D9` | `#302E29` | divider |
| `--line-2` | `#CBC7BE` | `#423F39` | control border |
| `--accent` | `#4B3FA6` | `#A79BF0` | primary action, selection, link |
| `--accent-ink` | `#372C86` | `#C7BEFA` | accent hover |
| `--accent-soft` | `#EEEBFA` | `#272238` | selected row ground |
| `--on-accent` | `#FFFFFF` | `#141311` | text laid on the accent. Not a fixed white: the dark accent is a light lilac, and white on it fails the contrast floor |
| `--ok-ink` | `#1F5F43` | `#8FD9B4` | `submitted`, `succeeded` |
| `--ok-bg` | `#E4F0EA` | `#14251D` | |
| `--ok-line` | `#B4D7C6` | `#22452F` | |
| `--warn-ink` | `#7A5312` | `#E8C078` | **content risk only** |
| `--warn-bg` | `#FBF0DC` | `#2A2013` | |
| `--warn-line` | `#E9D2A2` | `#4A3A1D` | |
| `--bad-ink` | `#8C2B22` | `#F0A79A` | **system failure only** |
| `--bad-bg` | `#FBE9E6` | `#2B1815` | |
| `--bad-line` | `#EFC1B8` | `#4C2721` | |
| `--mut-ink` | `#5C5852` | `#ADA79E` | `pending_integration`, no state |
| `--mut-bg` | `#EDEBE6` | `#23221E` | |
| `--mut-line` | `#D8D4CB` | `#37342F` | |
| `--scrim` | `rgb(26 25 23 / 55%)` | `rgb(0 0 0 / 62%)` | the veil behind a modal layer. Not an ink step: the ink family inverts between themes, so a scrim built from it would go light-on-dark |
| `--inverse-surface` | `#1A1917` | `#23221E` | a panel that is **deliberately dark in both themes** — the login product panel, the credential block |
| `--inverse-ink` | `#F0EDE7` | `#F0EDE7` | text on that panel |
| `--inverse-ink-2` | `#A8A29A` | `#A8A29A` | secondary text on that panel |
| `--inverse-line` | `#33312D` | `#3A3833` | borders and inset fields on that panel |
| `--inverse-bad` | `#F0A79A` | `#F0A79A` | an error on that panel — `--bad-ink` is tuned for a light ground and vanishes there |

**A dark panel is not an inversion.** A surface built from `--ink` / `--paper` flips with the
theme: what reads as a dark slab on a light page becomes a light slab on a dark one. The contrast
survives that swap; the intent does not. Any surface meant to stay dark uses the `--inverse-*`
family, which is themed only enough to lift the panel off the page ground.

**The warn and bad families are reserved and never interchangeable.** Ochre means a finding about
the contract; red means a defect in our processing (Constitution Principle IX).

### Theme-invariant values

Two small sets are identical in both themes, because they are marks on a known ground rather than
surface colours. They are the documented exception to rule 4 and live beside the token file.

| Purpose | Values |
|---|---|
| Distribution bar fills | ok `#2E7D5B` · neutral `#8C857B` · bad `#B4483C` · risk `#A9741F` |
| Signature dots | signed `#3E8C68` (dark `#5FBF91`) · refused `#B4483C` (dark `#D9776A`) · pending: `--line-2` outline, no fill |

Bar fills were checked to clear 3:1 against the surface. Every bar also carries its own label and
count, so no figure depends on colour (FR-002, FR-014).

## Typography

| Token | Value |
|---|---|
| `--font-sans` | `"IBM Plex Sans", system-ui, "Segoe UI", sans-serif` |
| `--font-mono` | `"IBM Plex Mono", ui-monospace, "SFMono-Regular", monospace` |

Family carries meaning: **sans for what a person wrote, mono for what the machine recorded** —
status values, identifiers, tokens, counts, dates, error codes, section eyebrows. Do not reach for
mono as decoration.

| Role | Size / weight | Notes |
|---|---|---|
| Page title | 27 / 600 | `letter-spacing: -0.02em` |
| Section title | 20 / 600 | `-0.012em` |
| Panel title | 15 / 600 | |
| Document name | 13 / 600 | |
| Body | 12.5 / 400 | `line-height: 1.5` |
| Support text | 11.5 / 400 | `--ink-2` or `--ink-3` |
| Eyebrow | 10 / 500 mono | uppercase, `letter-spacing: .13em` |
| Technical value | 11–11.5 mono | identifier, credential, status, date |
| Hero number | 34 / 500 mono | report tiles, `-0.02em` |

Document base: `400 13px/1.5 var(--font-sans)`. Apply `text-wrap: pretty` to prose blocks.

## Geometry

| Token group | Values |
|---|---|
| Spacing | 4 · 8 · 14 · 20 · 24 · 32 |
| Radius | 3 badge · 4 control · 6 card |
| Border | 1px throughout; never a sub-pixel hairline |
| Heights | 22 badge · 26 compact button · 32 button/select · 34 field · 44 minimum row · 56 header (`--h-header`, shared so the login page can size against it) |
| Detail rail | 452px fixed |
| Page padding | 22px vertical · 24px horizontal |
| Shadow | none, except the focus ring |

## Focus

One ring, everywhere, on `:focus-visible` only: a 2px `--accent` outline with a 2px offset. Never
suppressed, never replaced per component.

## Motion

Transitions are limited to colour, border and background, 120–160 ms. Everything is suppressed
under `prefers-reduced-motion: reduce` (FR-029).
