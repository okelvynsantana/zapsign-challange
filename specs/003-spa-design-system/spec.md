# Feature Specification: SPA Design System & Interface Layer

**Feature Branch**: `003-spa-design-system`

**Created**: 2026-09-08

**Status**: Draft

**Input**: User description: (empty — derived from `PRD-DESIGN.md`, "Implementação do Design do SPA", and the published design canvas)

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Tell the two statuses apart at a glance (Priority: P1)

An internal manager opens the document list and, without reading documentation or asking a
colleague, correctly answers two different questions for every row: *did this document reach the
signature provider?* and *has anyone signed it?* These are independent facts about a document, and
today they are presented as two adjacent columns of identical-looking raw text, which invites the
reader to treat them as one scale.

**Why this priority**: Mistaking "we sent it" for "they signed it" is the most consequential error
this interface can invite — it leads to a contract being treated as executed when nobody has signed
it. Every other improvement is cosmetic next to this one, and this story alone makes the existing
list trustworthy.

**Independent Test**: Show the document list, populated with documents covering every combination of
hand-off state and signature state, to someone who has never used the system. Ask them, per row,
whether the document reached the provider and whether it is signed. Delivers value on its own: the
list becomes readable without training, with no other screen changed.

**Acceptance Scenarios**:

1. **Given** a document that reached the provider but has not been signed, **When** the manager
   looks at its row, **Then** the hand-off state and the signature state are shown in two visibly
   different forms, and neither can be read as the other.
2. **Given** the same list viewed with all colour removed, **When** the manager reads any row,
   **Then** every status is still identifiable, because each carries a distinct shape or mark and a
   text label in addition to its colour.
3. **Given** a document whose signature state is a value the provider has never returned before,
   **When** the row renders, **Then** the value is displayed as received, in the neutral form, and
   nothing breaks or is silently dropped.
4. **Given** a document that has never been sent, **When** the manager looks at its signature
   column, **Then** the absence of a signature state is shown explicitly as "no state yet" rather
   than as an empty cell that reads like a bug.

---

### User Story 2 - Recover from a failed hand-off without help (Priority: P2)

A document was written down locally but the signature provider refused or was unreachable. The
manager sees which document is affected, why, and that the document itself is safe, and retries the
hand-off from where they already are.

**Why this priority**: The system deliberately records the document before contacting the provider,
so a failure is a normal, recoverable state rather than a lost document. The interface currently
presents that failure as an unstyled fragment of text, which makes a designed-for state look like a
crash and pushes people to re-create documents that already exist.

**Independent Test**: Put a document into the failed hand-off state with a recorded reason, then ask
an operator to explain what happened and to retry, using only the list. Delivers value on its own:
failure stops generating support requests and duplicate documents.

**Acceptance Scenarios**:

1. **Given** a document whose hand-off failed, **When** the manager looks at the list, **Then** the
   recorded reason is visible in place, together with a statement that the document is stored and
   nothing was lost.
2. **Given** that same document, **When** the manager decides to retry, **Then** the retry action is
   available on the row itself, without opening another screen.
3. **Given** a document in a state where retrying would risk a double submission, **When** the row
   renders, **Then** no retry action is offered.
4. **Given** an attempt to remove an organization that still owns documents, **When** the removal is
   refused, **Then** the manager is told why it was refused and what to do instead, not only that it
   failed.

---

### User Story 3 - Read an analysis and separate risk from breakage (Priority: P3)

The manager opens a document's content analysis and distinguishes two very different things: a
finding *about the contract* that a person must judge, and a failure *of our processing* that a
person must retry.

**Why this priority**: These two have different owners and different fixes. Presenting them alike —
as the interface does today — either causes real contract risks to be dismissed as glitches, or
causes processing glitches to be escalated as legal problems.

**Independent Test**: Show one document whose latest analysis carries a risk finding and one whose
latest analysis failed, and ask which one needs a lawyer and which one needs a retry. Delivers value
on its own: the analysis stops being decorative and starts driving action.

**Acceptance Scenarios**:

1. **Given** an analysis carrying a risk finding, **When** the manager opens the panel, **Then** the
   risk is marked distinctly and is never presented in the same visual language as a processing
   failure.
2. **Given** an analysis that failed, **When** the manager opens the panel, **Then** the recorded
   reason is shown both as the system recorded it and in plain language, together with an explicit
   statement that the document and its hand-off were unaffected, and the retry is the panel's
   primary action.
3. **Given** a document that has never been analysed, **When** the manager opens the panel, **Then**
   the panel says so plainly and offers to run the first analysis.
4. **Given** an analysis in progress, **When** the manager waits, **Then** the panel shows that work
   is under way and the maximum time it may take, rather than appearing frozen.
5. **Given** a document analysed more than once, **When** the manager opens the history, **Then**
   every past run remains readable with its date, outcome and how it was produced, and the current
   one is marked.

---

### User Story 4 - Work a long list without losing the list (Priority: P4)

With hundreds of documents, the manager narrows the list to what matters, moves through it, and
inspects or creates a document without the list being pushed out of view.

**Why this priority**: Valuable, but the three stories above make the existing list *correct* while
this one makes a large list *workable*. It is the natural cut line if effort runs short: without it
the interface is complete and honest, just less efficient at volume.

**Independent Test**: Load several hundred documents and ask an operator to find one specific
document, inspect it, and then create a new one — timing each step and observing whether the list
stays on screen throughout.

**Acceptance Scenarios**:

1. **Given** a list of several hundred documents, **When** the manager narrows it by hand-off state,
   by signature state, or by organization, **Then** only matching documents remain and the active
   narrowing is visible.
2. **Given** more documents than fit on one screenful, **When** the manager moves through them,
   **Then** the position within the whole set is stated and movement in both directions is possible.
3. **Given** the manager selects a document, **When** its detail opens, **Then** the list remains
   visible and the selected row is visibly tied to the detail being shown.
4. **Given** the manager starts creating a document, **When** the form opens, **Then** it occupies
   the same region as the detail, and the list is not pushed off screen.
5. **Given** the manager asks to delete a document or an organization, **When** the request is made,
   **Then** an explicit confirmation is required before anything is destroyed.

---

### User Story 5 - Use the system in the reader's own language and conditions (Priority: P5)

Whoever operates the system — including whoever is hired next — reads it in Brazilian Portuguese,
in whichever display mode their machine is set to, using a keyboard if that is how they work.

**Why this priority**: This is a floor rather than a feature, and it is applied across every screen
the other stories touch, so it lands last in sequence while remaining non-optional at delivery.

**Independent Test**: Walk every screen with the system set to dark appearance, then again using
only a keyboard, then read every string for language.

**Acceptance Scenarios**:

1. **Given** any screen, **When** it is read, **Then** all interface copy is in Brazilian
   Portuguese, and the only exceptions are values the system itself recorded, which appear exactly
   as recorded.
2. **Given** a machine set to a dark appearance, **When** any screen opens, **Then** it renders in a
   dark presentation, and no text falls below the accessible contrast floor.
3. **Given** a manager using only a keyboard, **When** they move through any screen, **Then** every
   action is reachable and the focused element is always visibly identifiable.
4. **Given** a control that shows only an icon, **When** it is reached by assistive technology,
   **Then** it announces what it does.
5. **Given** any recorded date or time, **When** it is displayed, **Then** it reads in the local
   convention rather than in the form it was stored.
6. **Given** a reader who has asked their system to reduce motion, **When** any screen changes
   state, **Then** the change happens without animation.

---

### Edge Cases

- A signature state the provider has never returned before, including an empty one.
- A document that has never been analysed, and one whose only successful analysis produced findings
  but no written summary.
- A document that is simultaneously overdue and carrying a risk finding — it must appear in both
  attention groups, because they are two different problems with two different fixes.
- A recorded failure reason at its maximum recorded length, and a document name or finding long
  enough to wrap several lines.
- Empty results everywhere: no documents, no organizations, and no items needing attention. The last
  of these is a good outcome and must not be presented as an error or as missing data.
- A document removed while its detail is open on screen.
- A window narrower than the intended working width, where the detail region can no longer sit
  beside the list.
- A reader who has asked their system to reduce motion.
- A screen read without colour — printed, projected, or by a colour-blind reader.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The interface MUST present the hand-off state, the signature state, and the analysis
  outcome in three visually distinct forms that cannot be mistaken for one another.
- **FR-002**: No status MAY be communicated by colour alone; every status indicator MUST combine
  colour with a distinct shape or mark and a text label.
- **FR-003**: Values the system recorded from the signature provider or from its own processing MUST
  be displayed exactly as recorded, never reworded or translated.
- **FR-004**: An unrecognised signature state MUST render sensibly rather than break, be hidden, or
  be reported as an error.
- **FR-005**: A failed hand-off MUST show its recorded reason in place, together with an explicit
  statement that the document itself is stored.
- **FR-006**: The retry action for a failed or already-submitted hand-off MUST be available from the
  list, and MUST NOT be offered in states where retrying would risk a double submission.
- **FR-007**: A refused organization removal MUST explain the cause and the way forward, not only
  report the refusal.
- **FR-008**: A risk finding MUST be visually distinct from a processing failure, and the two MUST
  NOT share a colour or a mark.
- **FR-009**: A failed analysis MUST show the recorded reason and a plain-language explanation,
  state that the document and its hand-off were unaffected, and present the retry as the primary
  action.
- **FR-010**: The analysis area MUST have a defined presentation for each of its four states:
  produced, failed, never run, and in progress.
- **FR-011**: The analysis history MUST remain readable, with each past run showing its date,
  outcome and how it was produced, and the current run marked.
- **FR-012**: The credential held for the signature provider MUST be presented as a secret: shown
  only in masked form, left empty when editing with an explicit statement that leaving it empty
  keeps the stored value.
- **FR-013**: Every screen MUST have a defined presentation for having no data, and an empty
  attention list MUST read as a positive result rather than as an absence.
- **FR-014**: The aggregated report MUST present each distribution with a directly attached label
  and count, so no figure depends on a separate key.
- **FR-015**: The document list MUST be narrowable by hand-off state, by signature state, and by
  organization, and the active narrowing MUST be visible.
- **FR-016**: When more documents exist than are shown, the interface MUST state the position within
  the whole set and allow movement in both directions.
- **FR-017**: Inspecting a document and creating or editing one MUST occupy the same screen region,
  and neither MAY displace the list.
- **FR-018**: The selected document MUST be visibly tied to the detail shown beside it.
- **FR-019**: Destroying a document or an organization MUST require an explicit confirmation.
- **FR-020**: All interface copy MUST be in Brazilian Portuguese, excepting the recorded values of
  FR-003.
- **FR-021**: Dates and times MUST be presented in the reader's local convention rather than as
  stored.
- **FR-022**: The interface MUST offer a light and a dark presentation and MUST follow the reader's
  system preference without requiring a choice.
- **FR-023**: Every screen MUST be fully operable by keyboard, with the focused element always
  visibly identifiable.
- **FR-024**: Every control that shows only an icon MUST announce its purpose to assistive
  technology.
- **FR-025**: A validation error MUST be attached to the field it concerns, both visually and for
  assistive technology.
- **FR-026**: Text MUST meet the accessible contrast floor in both presentations.
- **FR-027**: No screen MAY require horizontal scrolling of the page; content too wide for its
  region MUST scroll within that region.
- **FR-028**: Below the intended working width, the detail region MUST remain reachable and
  dismissable rather than being cut off.
- **FR-029**: Motion MUST be limited to state transitions and MUST be suppressed for readers who
  have asked to reduce it.
- **FR-030**: Every capability available before this work MUST remain available after it; no
  existing workflow may be lost in the course of the redesign.

### Key Entities

This feature adds no stored data. It gives distinct presentation to three concepts the system
already records, and the separation between them is the substance of the work:

- **Hand-off state**: our own record of whether a document reached the signature provider. We own
  it, it is the only one of the three with a recovery action, and it is the only one presented in
  the strongest visual form.
- **Signature state**: what the signature provider reports about signing. It is read, never
  computed here, its set of values is open-ended, and it carries no action of ours.
- **Analysis outcome**: the result of examining a document's content — a summary, absent topics, and
  findings, some of which are flagged as risk. A risk is a judgement about the contract; a failed
  analysis is a defect in our processing. They are different concepts and must look different.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Someone who has never used the system, shown the document list once, correctly states
  both whether a document was sent and whether it was signed for 10 out of 10 sampled documents,
  without asking a question.
- **SC-002**: Every status remains correctly identifiable when the same screens are read with all
  colour removed.
- **SC-003**: Given a document with a failed hand-off, an operator explains the cause and triggers
  the retry in under 30 seconds, without leaving the list or consulting documentation.
- **SC-004**: Shown one document carrying a contract risk and one whose analysis failed, operators
  classify which needs human judgement and which needs a retry correctly 100% of the time.
- **SC-005**: Finding one specific document among at least 200 takes under 15 seconds.
- **SC-006**: No task requires the document list to leave the screen; inspecting and creating both
  keep it in view.
- **SC-007**: All primary tasks on every screen are completable using only a keyboard, with the
  focused element identifiable at every step.
- **SC-008**: Text contrast meets the accessible floor on every screen in both the light and the
  dark presentation, with zero exceptions.
- **SC-009**: 100% of interface copy is in Brazilian Portuguese, excepting recorded values, which
  match what the system stored character for character.
- **SC-010**: Every workflow the system supported before this feature still completes after it,
  verified by walking each supported workflow end to end; zero capabilities are lost.
- **SC-011**: No screen scrolls horizontally at or above the intended working width, and none
  becomes unusable below it.

## Assumptions

- The visual direction is settled and is the one published on the design canvas and detailed in
  `PRD-DESIGN.md`; this feature implements it rather than reopening it. The two alternative
  directions explored were considered and set aside.
- The work is confined to the interface. No stored data, no service contract, and no business rule
  changes; the interface consumes what already exists.
- Desktop is the target. The interface must degrade gracefully on a narrow window, but designing for
  small screens is out of scope for this feature.
- Following the reader's system appearance preference is sufficient; an explicit in-app switch
  between light and dark is out of scope and may be added later.
- Brazilian Portuguese is applied as the interface's single language. A translation mechanism for
  further languages is out of scope.
- User Stories 4 and 5 introduce capabilities and guarantees the current interface does not have.
  They are ordered last precisely so that they can be deferred without leaving the earlier stories
  incomplete; Stories 1 through 3 stand on their own as a shippable improvement.
- The existing automated behavioural checks are treated as a contract on what the system does, and
  are expected to survive the redesign; where copy changes, only the assertions about that copy
  change with it.
