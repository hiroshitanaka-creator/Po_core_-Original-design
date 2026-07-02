# ADR Process (Original Design)

Governance-only operational guide for the Architecture Decision Record
(ADR) system introduced in PR-011. Covers `docs/original_design_adr/`,
`docs/governance/adr_rules.json`, `scripts/check_adr_index.py`, and the
optional `ADR Index` GitHub Actions workflow
(`.github/workflows/adr-index.yml`).

This ADR system governs the **Original Design** track
(`src/po_core_original/` + its governance docs). The main `po_core`
package has its own, independent ADR system at `docs/adr/` — see
`docs/original_design_adr/ADR-0001-adopt-adr-system.md` for why the two are
kept separate.

## 1. Purpose

Concept drift validation (`scripts/check_concept_drift.py`) catches wording
that shrinks Po_core's identity. Trace continuity validation
(`scripts/validate_trace_continuity.py`) catches structurally broken trace
chains. Neither one records *why* an architecture-impacting decision was
made, or what alternatives were rejected. ADRs close that gap: they are a
permanent, reviewable record of architecture decisions, required before a
PR that changes SSOT, schemas, trace contracts, layer responsibilities, or
concept-preservation rules can be considered complete.

## 2. When ADR is required

An ADR is required when a PR changes any of:

- SSOT changes (`docs/STRICT_CORE_RULES.md`, `docs/厳格固定ルール.md`)
- schema changes (files under `schemas/`)
- trace contract changes (`docs/contracts/`, trace event semantics,
  `src/po_core_original/trace_validation/`)
- architecture layer responsibility changes (Po_core / Po_self / Viewer)
- controlled mode semantics (jump / reject / reactivate)
- changes to the definition of Po_core / Po_self / Viewer
- changes to concept drift rules (`docs/governance/concept_drift_rules.json`,
  `docs/CONCEPT_DRIFT_GUARD.md`, `docs/ARCHITECTURE_NORTH_STAR.md`)
- changes to governance rules (`docs/GOVERNANCE.md`,
  `docs/governance/adr_rules.json`)

## 3. When ADR is not required

- typo fixes
- formatting-only docs changes
- adding examples that do not change semantics
- tests that only lock existing behavior
- changelog/status updates that only record already-approved work

## 4. ADR lifecycle

Each ADR has exactly one `Status` at a time:

- `Proposed` — under discussion, not yet acted on.
- `Accepted` — the decision is in effect.
- `Superseded` — replaced by a later ADR (cross-reference via
  `Supersedes:` / `Superseded by:`).
- `Deprecated` — no longer recommended but not formally replaced.
- `Rejected` — considered and explicitly not adopted; kept for the record.

An ADR is never edited to pretend a different decision was made — status
transitions are recorded by updating the `Status:` line (and, for
supersession, adding a new ADR), not by deleting or rewriting history.

## 5. ADR numbering

Sequential, four-digit, zero-padded, starting at `ADR-0001`.
`ADR-0000-template.md` is reserved for the template and is never a real
decision. File names must match `ADR-####-slug.md`; numbers must be unique
within `docs/original_design_adr/`.

## 6. How to create an ADR

1. Copy `docs/original_design_adr/ADR-0000-template.md` to
   `docs/original_design_adr/ADR-####-slug.md` using the next unused
   number.
2. Fill in every required section: `Context`, `Decision`, `Scope`,
   `Architecture Impact`, `Concept Preservation`, `Alternatives Considered`,
   `Consequences`, `Validation`, `Rollback / Reversal`.
3. Set `Status: Proposed` (or `Accepted` if adopting immediately in the same
   PR, following the ADR-0001 precedent).
4. Add a row to `docs/original_design_adr/INDEX.md`.
5. Run the validator (section 8) before opening the PR.

## 7. How to update INDEX.md

Add or update one row per non-template ADR:

```
| ADR-#### | <Title matching the ADR's H1 after "ADR-####: "> | <Status matching the ADR's Status: line> | <Date matching the ADR's Date: line> | <one-line summary> |
```

`ADR-0000-template.md` must never appear as a row. `INDEX.md` must list
every non-template ADR exactly once.

## 8. How to run validator

```bash
python scripts/check_adr_index.py
python scripts/check_adr_index.py --json
python scripts/check_adr_index.py --rules docs/governance/adr_rules.json
python -m pytest tests/test_adr_index_validator.py -v
```

Exit code `0` means the ADR set is internally consistent; non-zero means one
or more issues below need fixing.

## 9. Common failures

### missing_adr

Meaning: An architecture-impacting change has no ADR, or an existing ADR is
missing from `INDEX.md`.

Fix: Create a new ADR from `ADR-0000-template.md` and update `INDEX.md` (or,
if the ADR file already exists, add its missing row to `INDEX.md`).

### missing_section

Meaning: ADR is missing a required section (see `docs/governance/
adr_rules.json`'s `required_sections`).

Fix: Add the missing section.

### index_mismatch

Meaning: `INDEX.md` does not match the ADR file (title, status, or date
differs).

Fix: Update the `INDEX.md` row to match the ADR file's H1 title / `Status:`
line / `Date:` line exactly.

Other, less common issues the validator reports: `missing_adr_directory`,
`missing_template`, `missing_index`, `invalid_filename` (ADR file name does
not match `ADR-####-slug.md`), `duplicate_adr_number`, `missing_title`,
`title_number_mismatch`, `missing_status`, `invalid_status` (not one of
Proposed/Accepted/Superseded/Deprecated/Rejected), `missing_date`,
`template_in_index` (`ADR-0000` listed as a decision), and
`duplicate_index_row`.

## 10. Relation to concept drift validation

Concept drift validation (`scripts/check_concept_drift.py`) checks
*wording* in README/PRD/governance docs against a fixed identity contract.
ADR validation checks that architecture *decisions* are recorded and
internally consistent. A PR that changes `docs/CONCEPT_DRIFT_GUARD.md` or
`docs/governance/concept_drift_rules.json` needs **both**: an ADR recording
why the rules changed, and a passing concept drift check on the resulting
wording. Neither one substitutes for the other.

## 11. Relation to trace continuity validation

Trace continuity validation (`scripts/validate_trace_continuity.py`,
`TraceContinuityValidator`) checks that emitted `PoTraceEvent` chains are
structurally unbroken. ADR validation does not read or exercise trace
events at all. A PR that changes trace event semantics (not just adds a
new, backward-compatible field) needs an ADR explaining the change **and**
an update to `docs/contracts/TRACE_CONTINUITY_V1.md` / the validator itself
if the continuity rules change.

## 12. What ADR does not test

ADR validation does not test:

- runtime behavior
- schema correctness
- trace continuity
- concept drift wording
- LLM quality
- philosopher behavior

`scripts/check_adr_index.py` never imports `src/po_core_original/` or
`src/po_core/` — it only parses Markdown files under
`docs/original_design_adr/`.
