# ADR-0001: Adopt ADR System for Original Design Architecture Changes

- Status: Accepted
- Date: 2026-07-02
- Deciders: Original Design governance layer maintainers
- Related PRs: PR-011
- Related Issues: TBD
- Supersedes: None
- Superseded by: None

## Context

Po_core Original Design (`src/po_core_original/`) is built as an explicit,
governance-protected seed runtime: PR-003 through PR-010 established the
tensor kernel seed, the Po_self controller seed, the Viewer feedback seed,
reconstruction planning/execution, trace continuity validation, and
concept-drift validation. All of that governance is enforced either by
scripts/CI or by PR-template checklists — but none of it explains **why** a
given architecture-impacting decision was made, only whether the resulting
docs/code satisfy a rule. Without a record of *why*, future contributors (or
future AI coding agents, per `docs/AI_AGENT_INITIALIZATION_RULES.md`) have no
way to distinguish an intentional, reasoned architecture decision from an
accidental one, and no way to know what alternatives were already
considered and rejected. This creates a real risk of silent concept drift:
a plausible-looking future change (e.g. "simplify Po_self to just call an
LLM directly") could pass every existing gate (trace continuity, concept
drift wording, PR governance) while still being architecturally wrong,
simply because no prior decision record exists to contradict it.

A second, more immediate problem surfaced while starting this PR: this
repository already contains a mature, independent ADR system at `docs/adr/`
(`0001-output-format.md` … `0014-values-clarification-pack-v1.md`, plus a
lowercase `docs/adr/index.md`) that records decisions for the main,
already-published `po_core` package (golden-diff contracts, policy
arbitration, trace metrics, etc.). That system is unrelated to the Original
Design governance track and must not be disturbed. Reusing `docs/adr/` for
Original Design ADRs would require a new `docs/adr/INDEX.md` (uppercase)
next to the existing `docs/adr/index.md` (lowercase) — the exact
case-only-filename collision (broken on case-insensitive filesystems such as
macOS and Windows) that this session already found and fixed once for
`docs/STATUS.md` vs. `docs/status.md` (renamed to
`docs/original_design_status.md`).

## Decision

Adopt a formal Architecture Decision Record (ADR) system for the Original
Design governance layer, requiring an ADR for any change that affects:

- `docs/STRICT_CORE_RULES.md`
- `docs/ARCHITECTURE_NORTH_STAR.md`
- `docs/CONCEPT_DRIFT_GUARD.md`
- schema files under `schemas/`
- contract docs under `docs/contracts/`
- trace event definitions
- trace continuity rules
- Po_core / Po_self / Viewer layer responsibilities
- concept drift rules
- future controlled modes (jump / reject / reactivate)
- any public redefinition of Po_core identity

**ADR is required to prevent silent concept drift.**

To avoid colliding with the pre-existing main-track ADR system at
`docs/adr/`, the Original Design ADR system lives in its own directory,
`docs/original_design_adr/` (README, INDEX.md, ADR-0000-template.md, and
numbered `ADR-####-slug.md` files starting with this ADR), mirroring the
`docs/original_design_status.md` naming precedent. The two ADR systems are
independent: `docs/adr/` continues to govern the main `po_core` package
runtime unchanged; `docs/original_design_adr/` governs
`src/po_core_original/` and its accompanying governance docs.

**ADR governance is docs/governance only and does not add runtime
behavior.** `scripts/check_adr_index.py` and the optional `ADR Index` CI
workflow validate documentation structure (file naming, required sections,
index/file consistency) — they never import or exercise
`src/po_core_original/` or `src/po_core/` runtime code.

## Scope

- New directory `docs/original_design_adr/` (README.md, INDEX.md,
  ADR-0000-template.md, ADR-0001-adopt-adr-system.md).
- New `docs/governance/adr_rules.json` config.
- New `scripts/check_adr_index.py` validator.
- New optional `.github/workflows/adr-index.yml` CI workflow.
- New `docs/operations/adr_process.md` operations guide.
- New `tests/test_adr_index_validator.py`.
- Updates to `.github/PULL_REQUEST_TEMPLATE.md`, `docs/GOVERNANCE.md`,
  `docs/original_design_status.md`, `docs/ROADMAP.md`, `CHANGELOG.md`,
  `README.md`.
- Does **not** touch `docs/adr/` (main-track ADR system, unchanged).
- Does **not** touch any file under `src/po_core_original/` or
  `src/po_core/`.

## Architecture Impact

- Po_core tensor kernel: unaffected (no code touched; ADRs will be required
  for *future* changes to it).
- Po_self recursive layer: unaffected (no code touched; ADRs will be
  required for *future* changes to it).
- Viewer feedback layer: unaffected (no code touched; ADRs will be required
  for *future* changes to it).
- Po_trace: unaffected; trace continuity validation (PR-008/PR-009) is
  unchanged. Future changes to trace event semantics will require both an
  ADR and the existing `TraceContinuityValidator` update.
- 42 philosophers as deliberation modules: unaffected; any future change to
  their role would now require an ADR under this system.
- Safety Floor / Concept Ceiling: unaffected; this ADR does not change any
  safety-gate behavior, only adds a documentation-governance requirement for
  *future* changes that might.

## Concept Preservation

- Does this preserve the three-layer tensor intelligence model? Yes — this
  ADR exists specifically to make future changes to that model explicit and
  reviewable, not to change it.
- Does this preserve Po_self as more than a wrapper? Yes — unaffected.
- Does this preserve Viewer as more than a dashboard? Yes — unaffected.
- Does this preserve Trace as more than audit logging? Yes — unaffected;
  trace continuity is treated as a decision substrate requiring its own ADR
  for future semantic changes.
- Does this preserve the 42 philosophers as modules, not system identity?
  Yes — unaffected.

## Alternatives Considered

1. **Reuse `docs/adr/` directly** (add `ADR-####-*.md` files and a new
   `docs/adr/INDEX.md` next to the existing `docs/adr/index.md`). Rejected:
   reproduces the exact case-only-filename collision risk on
   case-insensitive filesystems that was just fixed for
   `docs/STATUS.md`/`docs/status.md`, and mixes two unrelated numbering
   conventions (`0001-*.md` for the main track vs. `ADR-0001-*.md` for
   Original Design) in one directory.
2. **Reuse `docs/adr/` but name the new index file something else** (e.g.
   `docs/adr/adr_original_design_index.md`), keeping all ADRs in one
   directory. Rejected: still mixes two independent governance tracks and
   two numbering schemes in a single directory, making it harder to tell at
   a glance which ADRs govern which system; a validator scoped only to
   `ADR-####-*.md` filenames would also need extra logic to ignore the 14
   pre-existing bare-numbered files.
3. **New directory `docs/original_design_adr/`** (chosen). Zero collision
   risk, mirrors the already-established `docs/original_design_status.md`
   precedent from this same session, and keeps the two ADR systems
   unambiguously separate while both remain easy to find via
   `docs/GOVERNANCE.md` and `README.md`.

## Consequences

### Positive

- Future architecture-impacting changes to the Original Design track must
  have a documented reason, considered alternatives, and impact analysis
  before merging.
- A machine-checkable index (`docs/original_design_adr/INDEX.md` +
  `scripts/check_adr_index.py`) keeps the ADR set internally consistent
  (no orphaned files, no stale index rows).
- Establishes a precedent (separate, clearly-named governance directories)
  that future Original Design additions can follow without re-litigating
  naming collisions.

### Negative

- Adds one more governance checklist item to the PR template.
- Contributors must learn two ADR systems exist in this repository
  (`docs/adr/` for the main track, `docs/original_design_adr/` for Original
  Design) and pick the right one.

### Risks

- A future contributor could mistakenly add an Original-Design-relevant ADR
  to `docs/adr/` (main track) instead of `docs/original_design_adr/`.
- The ADR requirement could be perceived as bureaucratic overhead for small
  changes if the "when ADR is not required" list
  (`docs/operations/adr_process.md`) is not followed.

### Mitigations

- `docs/GOVERNANCE.md`'s new "ADR Governance Gate" section and
  `docs/operations/adr_process.md` both explicitly name
  `docs/original_design_adr/` and link back to this ADR's rationale for the
  directory split.
- The "When ADR is not required" list (typo fixes, formatting-only changes,
  non-semantic examples, tests that lock existing behavior,
  changelog/status bookkeeping) keeps the bar proportionate.

## Validation

- `scripts/check_adr_index.py` validates this ADR and
  `docs/original_design_adr/INDEX.md` are consistent (title, status, date,
  required sections).
- `tests/test_adr_index_validator.py` covers the validator's pass/fail
  behavior, including that ADR-0001 exists and is `Accepted`.
- The optional `ADR Index` GitHub Actions workflow
  (`.github/workflows/adr-index.yml`) re-runs the same script plus the test
  suite for PRs touching ADR/governance paths.

## Rollback / Reversal

This ADR can be superseded by a future ADR (e.g. one that merges the two
ADR directories once the main-track numbering scheme is migrated, or one
that changes the required-ADR path list). Reversal is a documentation-only
change: delete or mark `docs/original_design_adr/` files `Superseded`,
update `INDEX.md`, and remove the corresponding CI workflow / PR template
section. No runtime code depends on this ADR's existence.

## Notes

This ADR is itself the first entry validated by the system it establishes —
`scripts/check_adr_index.py` and `tests/test_adr_index_validator.py` both
check that this file exists, is `Accepted`, and is correctly indexed.
