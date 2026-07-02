# ADR (Architecture Decision Records) — Original Design

Po_core architecture changes must be explicit. Any change that affects
SSOT, schemas, trace contracts, Po_core / Po_self / Viewer responsibilities,
concept preservation, or controlled modes must have an ADR. ADR does not
replace tests, schemas, or trace contracts. ADR records why a decision was
made.

> This directory holds ADRs for the **Original Design governance layer**
> (`src/po_core_original/` plus its governance docs/scripts/CI) only. The
> main `po_core` package has its own, independent ADR system at
> `docs/adr/` (14 ADRs, e.g. golden-diff contracts, policy arbitration) —
> the two are deliberately separate directories with independent numbering.
> See ADR-0001 (`ADR-0001-adopt-adr-system.md`) for why they are not merged.

## What ADRs are

An Architecture Decision Record (ADR) is a short document that captures a
single architecture-impacting decision: the context that forced the
decision, the decision itself, the alternatives that were considered and
rejected, and the consequences (positive, negative, risks, mitigations).
It is a permanent, append-only record — an ADR is never edited to pretend a
different decision was made; instead, a new ADR supersedes it.

## Why this repository uses ADRs

This repository protects an original design:

> Po_core is a three-layer tensor intelligence system for processing the
> meaning and responsibility of speech.
>
> - Po_core: tensor kernel
> - Po_self: recursive trace-based self-reconstruction layer
> - Viewer: external resonance / feedback tensor layer
>
> The 42 philosophers are deliberation modules inside Po_core. They are not
> the whole system. Safety is a floor, not a concept ceiling.

Concept drift validation (`scripts/check_concept_drift.py`) and trace
continuity validation (`scripts/validate_trace_continuity.py`) both catch
*wording* and *structural* drift after the fact. Neither one records *why*
an architecture-impacting decision was made in the first place, or what
alternatives were rejected and why. ADRs close that gap: any future change
that affects this architecture must be recorded as an ADR, so a plausible
but wrong-headed "simplification" cannot slip in just because it happens to
pass every mechanical gate.

## When ADRs are required

An ADR is required when a PR changes any of:

- `docs/STRICT_CORE_RULES.md`
- `docs/ARCHITECTURE_NORTH_STAR.md`
- `docs/CONCEPT_DRIFT_GUARD.md`
- schema files under `schemas/`
- contract docs under `docs/contracts/`
- trace event definitions or trace continuity rules
- Po_core / Po_self / Viewer layer responsibilities
- concept drift rules (`docs/governance/concept_drift_rules.json`)
- future controlled modes (jump / reject / reactivate)
- any public redefinition of Po_core identity

See `docs/operations/adr_process.md` for the full "when required / when not
required" list and common validator failures.

## ADR numbering

ADRs are numbered sequentially starting at `ADR-0001` (four-digit,
zero-padded). `ADR-0000-template.md` is reserved for the template and is
never a real decision — it is intentionally excluded from `INDEX.md` and
from the "ADR-0001 exists" / uniqueness checks. File names must match
`ADR-####-slug.md` (e.g. `ADR-0002-example-decision.md`); numbers must be
unique.

## ADR status lifecycle

Each ADR has a `Status` field with exactly one of these values:

- `Proposed` — under discussion, not yet acted on.
- `Accepted` — the decision is in effect.
- `Superseded` — replaced by a later ADR (which should reference it via
  `Supersedes:` / `Superseded by:`).
- `Deprecated` — no longer recommended but not formally replaced.
- `Rejected` — considered and explicitly not adopted (kept for the record).

## How to add a new ADR

1. Copy `ADR-0000-template.md` to `ADR-####-slug.md`, where `####` is the
   next unused four-digit number and `slug` is a short kebab-case summary
   of the title.
2. Fill in every section — `Context`, `Decision`, `Scope`,
   `Architecture Impact`, `Concept Preservation`, `Alternatives Considered`,
   `Consequences`, `Validation`, `Rollback / Reversal` (see
   `docs/governance/adr_rules.json`'s `required_sections`).
3. Set `Status: Proposed` until the decision is actually adopted, then
   update it to `Accepted` (or `Rejected` if it was considered and declined
   — rejected ADRs are still kept as a record).
4. Add a row to `INDEX.md` (see below).
5. Run the validator (see below) before opening the PR.

## How to update INDEX.md

Add one row per non-template ADR to the table in `INDEX.md`:
`| ADR-#### | <Title> | <Status> | <Date> | <one-line summary> |`. The
`Title`, `Status`, and `Date` columns must match the ADR file's H1 title
(after the `ADR-####: ` prefix), `Status:` line, and `Date:` line exactly —
`scripts/check_adr_index.py` checks this. `ADR-0000-template.md` must never
appear as a row.

## How to run validator

```bash
python scripts/check_adr_index.py
python scripts/check_adr_index.py --json
python -m pytest tests/test_adr_index_validator.py -v
```

The optional `ADR Index` GitHub Actions workflow
(`.github/workflows/adr-index.yml`) runs the same two commands for PRs that
touch `docs/original_design_adr/**` or related governance files. See
`docs/operations/adr_process.md` for the full operational guide.
