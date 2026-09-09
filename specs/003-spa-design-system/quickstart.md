# Quickstart — Validating the Interface Layer

**Feature**: [spec.md](spec.md) · **Plan**: [plan.md](plan.md)

How to prove this feature works. Every check below maps to a success criterion in the spec, and
each states what you should see. Nothing here needs a third-party account or an internet
connection.

---

## Prerequisites

The stack runs entirely offline. From the repository root:

```bash
cp deploy/.env.example deploy/.env
```

Set the following in `deploy/.env` so no call leaves the machine:

```bash
ZAPSIGN_USE_FAKE=true      # the signature provider is faked
AI_USE_FAKE=true           # the analysis provider is faked
```

Bring it up and seed a demo organization and document:

```bash
docker compose -f deploy/docker-compose.yml up --build
docker compose -f deploy/docker-compose.yml exec backend python manage.py seed_demo
```

Sign in at <http://localhost:4200> with the seeded credentials from `deploy/.env`.

To exercise the states the seed does not produce, create documents with a deliberately unreachable
PDF link and with a link to a scanned (image-only) PDF; the first drives a hand-off failure, the
second an analysis failure with reason `no_text`.

---

## Automated gates

Run from `frontend/`. These must pass before any manual check is meaningful.

```bash
npm run lint          # no new violations
npm run typecheck     # clean
npm run test:cov      # 74+ tests, coverage >= 80%
npm run build         # must not print a budget warning
```

**Expected**

- The pre-existing suite passes unchanged in intent. Only assertions about interface copy were
  updated, and only where the copy is now in Portuguese. **This is the regression net for SC-010** —
  if a test had to be weakened or deleted to make it pass, a capability was lost.
- `npm run build` prints no budget warning. The configured limits are 500 kB on the initial bundle
  and 4 kB per component stylesheet; a warning means shared atoms leaked into component
  stylesheets (research R-010).

---

## Story 1 — The two statuses are distinguishable (SC-001, SC-002)

1. Open **Documentos** with the seeded data plus your failure cases.
2. For each row, answer two questions from the row alone: did it reach the provider, and has it
   been signed?

   **Expected** — the hand-off state is a bordered badge with a mark and its verbatim value; the
   signature state is a dot with a small-caps label and no badge. They do not read as one scale.

3. A document that was never sent shows an explicit em dash for signature state, not an empty cell.
4. Set the display to grayscale (macOS: *System Settings → Accessibility → Display → Color
   Filters → Grayscale*) and read the same rows.

   **Expected** — every status is still identifiable. Nothing became ambiguous. This is SC-002 and
   it is the check most likely to fail if a mark was skipped somewhere.

5. Force an unexpected signature value if you can reach the database, or trust the unit test for it.

   **Expected** — the row renders, the value shows verbatim with the neutral dot, nothing is hidden
   and nothing throws.

---

## Story 2 — Failure is recoverable (SC-003)

1. Find the document whose hand-off failed.

   **Expected** — the recorded reason is visible in the row itself, together with the statement
   that the document is stored. The retry action is on the row.

2. Time yourself explaining the cause and triggering the retry, using only this screen.

   **Expected** — under 30 seconds, no documentation, no other screen (SC-003).

3. Check a document in `pending_integration`.

   **Expected** — **no** retry action offered.

4. Go to **Organização** and try to delete the organization that owns documents.

   **Expected** — a refusal that explains the cause, shows the technical code, and says what to do
   instead. The organization is still listed.

---

## Story 3 — Risk is not breakage (SC-004)

1. Open a document whose latest analysis carries a risk finding.

   **Expected** — the risk sits in the ochre treatment with the triangle mark and a `RISCO` label.
   No red failure styling appears because of it.

2. Open the document whose analysis failed with `no_text`.

   **Expected** — the raw reason in mono, a plain-language explanation in Portuguese, an explicit
   statement that the document and its hand-off were unaffected, and the retry as the panel's
   primary action.

3. Show both to someone and ask which needs a lawyer and which needs a retry.

   **Expected** — correct every time (SC-004).

4. Open a document that has never been analysed, then run an analysis and watch.

   **Expected** — the never-run state says so and offers to run; while running, the panel shows work
   in progress and the maximum time rather than appearing frozen.

5. Re-analyse a document and open the history.

   **Expected** — the earlier run is intact, the current one is marked, and each row carries its
   date, outcome and how it was produced.

---

## Story 4 — Working a long list (SC-005, SC-006)

Seed enough documents to exceed one page before this section.

1. Narrow the list by hand-off state, then by signature state, then by organization.

   **Expected** — only matching documents remain, and the active narrowing is visible.

2. Find one specific document among at least 200.

   **Expected** — under 15 seconds (SC-005).

3. Move through the pages.

   **Expected** — the position within the whole set is stated; both directions work.

4. Select a document, then start creating a new one.

   **Expected** — the list stays on screen throughout; detail and form occupy the same region and
   never both at once; the selected row is visibly tied to the detail (SC-006).

5. Delete a document.

   **Expected** — an explicit confirmation first. Cancelling destroys nothing.

---

## Story 5 — Language, theme, keyboard (SC-007, SC-008, SC-009, SC-011)

1. Read every screen.

   **Expected** — all copy in Brazilian Portuguese. The only English is values the system recorded
   — `submitted`, `no_text`, `company_has_documents` and the like — shown in mono, character for
   character as stored (SC-009).

2. Switch the machine to dark appearance and walk all seven screens.

   **Expected** — every screen renders dark. No element keeps a light background. Nothing is
   illegible (SC-008).

3. Check contrast on both themes with a contrast checker on the smallest text of each screen.

   **Expected** — body text at or above 4.5:1, large text and control borders at or above 3:1, with
   no exceptions (SC-008).

4. Unplug the mouse. Complete one full task on each screen: sign in, create a document, inspect its
   analysis, delete it with confirmation, and read the reports.

   **Expected** — everything reachable, focus always visible, and focus returns to the invoking
   control when a dialog closes (SC-007).

5. Resize the window from 1440 px down to 1100 px.

   **Expected** — no horizontal page scrollbar at any width. At the narrow end the detail region
   becomes a dismissable layer rather than being cut off, and `Esc` closes it (SC-011, FR-028).

6. Turn on reduced motion and repeat a few state changes.

   **Expected** — states change without animation.

---

## Offline guarantee

With the application running, open the browser's network panel and reload every screen.

**Expected** — every request goes to the application's own origin. **No request to any font host,
CDN, or analytics endpoint.** A single request to a third-party origin fails this check and
violates Constitution Principle VIII.

---

## Done

The feature is validated when the automated gates pass, every expectation above holds, and the
definition-of-done checklist in `PRD-DESIGN.md` §18 is fully ticked.
