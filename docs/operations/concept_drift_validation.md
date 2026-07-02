# Concept Drift Validation — Operations Guide

> PR-010 governance documentation. This document explains how to run
> `scripts/check_concept_drift.py` as an operational check. **It adds no new
> runtime behavior** — it is a text scanner over documentation files and the
> PR template. See `docs/CONCEPT_DRIFT_GUARD.md` for the underlying checklist
> this formalizes, and `docs/GOVERNANCE.md` ("Concept Drift Governance Gate")
> for the governance policy.

## 1. Purpose

Concept drift validation checks that public documentation (`README.md`, the
PRD, and related governance docs) and the PR template continue to describe
Po_core as its canonical identity:

> Po_core is a three-layer tensor intelligence system for processing the
> meaning and responsibility of speech. Layer 1 (Po_core) computes semantic,
> ethical, responsibility, and freedom-pressure tensors. Layer 2 (Po_self)
> reads Po_trace and performs recursive self-reconstruction decisions.
> Layer 3 (Viewer) returns external resonance, disagreement, discomfort, and
> feedback tensors into Po_self. The 42 philosophers are deliberation
> modules inside Po_core — they are not the whole system. Safety is a
> floor, not a concept ceiling.

## 2. Why concept drift validation exists

Documentation and PR descriptions are edited far more often than the
underlying architecture — by contributors and AI coding agents alike. Each
individual edit can look reasonable in isolation ("simplify this sentence for
readability") while the cumulative effect quietly rewrites Po_core into a
generic chatbot, a generic decision-support tool, a safety-wrapper product,
or a philosopher-roleplay demo. `docs/CONCEPT_DRIFT_GUARD.md` already names
this failure mode; this validator makes the checklist mechanically
enforceable instead of relying on every future reviewer remembering to apply
it by hand.

## 3. When to run

Run concept drift validation when changing:

- README
- PRD
- architecture docs
- governance docs
- AI agent instruction docs
- docs describing Po_core / Po_self / Viewer
- docs describing the 42 philosophers
- docs describing safety identity

If your PR does not touch any of the above, you do not need to run this —
the "Concept Drift Check" section in `.github/PULL_REQUEST_TEMPLATE.md` lets
you mark it "Not applicable."

## 4. Local commands

```bash
# Full default check: README + PRD (docs/PRD.md or docs/spec/prd.md,
# whichever exists) + other configured checked_files + governance docs
# existence + PR template checklist:
python scripts/check_concept_drift.py

# Explicitly run the PR template Concept Preservation checklist check
# (already included in the default run above; this is the exact command
# used by the Concept Drift CI workflow):
python scripts/check_concept_drift.py --check-pr-template

# Check specific files only:
python scripts/check_concept_drift.py --files README.md docs/spec/prd.md

# Use a different rules config:
python scripts/check_concept_drift.py --rules docs/governance/concept_drift_rules.json

# Machine-readable output:
python scripts/check_concept_drift.py --json

# Run the validator's own unit tests:
python -m pytest tests/test_concept_drift_guard.py -v
```

Exit code `0` means every check passed; non-zero means at least one issue was
found (missing identity term, forbidden shrinkage phrase/pattern, unclosed
ignore block, missing PR-template checklist item, or missing governance
doc/PRD). No network access is required; the script uses only the Python
standard library.

## 5. CI workflow explanation

`.github/workflows/concept-drift.yml` ("Concept Drift") runs
`python scripts/check_concept_drift.py --check-pr-template` on
`ubuntu-latest` with only the Python standard library (no dependencies to
install). It is **scoped and optional**: it does not run the runtime test
suite, does not publish artifacts, does not require secrets, and does not
mutate repository state. It triggers on changes to `README.md`, anything
under `docs/**`, the PR template, the workflow file itself, and the checker
script — or manually via `workflow_dispatch`.

## 6. Required identity terms

Minimum required in `README.md`:

- `three-layer tensor intelligence system`
- `Po_core`
- `Po_self`
- `Viewer`
- `42 philosophers`
- `deliberation modules`
- `Safety is a floor`

Minimum required in the PRD (`docs/PRD.md` or `docs/spec/prd.md`, whichever
exists):

- `three-layer tensor intelligence system`
- `Po_core`
- `Po_self`
- `Viewer`
- `Po_trace`
- `feedback tensor`

See `docs/governance/concept_drift_rules.json` (`required_identity_terms`)
for the authoritative, machine-read list.

## 7. Forbidden shrinkage patterns

The checker rejects sentences that positively *define* Po_core (or Po_self /
Viewer / Trace / the 42 philosophers) as something smaller than the
three-layer system — while still allowing legitimate negations. Examples:

| Must PASS (allowed negation) | Must FAIL (forbidden shrinkage) |
|---|---|
| "Po_core is not a generic chatbot." | "Po_core is just a chatbot." |
| "The 42 philosophers are not the whole system." | "Po_core is merely a decision-support tool." |
| "Viewer is not merely a dashboard." | "Viewer is only a dashboard." |
| "Safety is a floor, not a concept ceiling." | "Po_self is just a wrapper." |
| | "Trace is merely an audit log." |
| | "Po_core is primarily a safe answer generator." |

The full literal-phrase and regex-pattern lists are in
`docs/governance/concept_drift_rules.json`
(`forbidden_positive_identity_patterns`, `forbidden_regex_patterns`).
Negation is detected by checking whether the *same line* also contains an
`allowed_negation_contexts` phrase (e.g. `"not just"`, `"not merely"`, `"not
the whole system"`) — a forbidden phrase on a line that also carries a
negation context is not flagged.

## 8. Ignore marker usage

Use ignore markers **only** for illustrating bad wording as an example
inside governance docs (e.g. `docs/CONCEPT_DRIFT_GUARD.md`'s "Forbidden
Rewrites" section) — never to silence a real drift violation.

Ignore a single line:

```markdown
Po_core is just a chatbot. <!-- concept-drift-ignore-line -->
```

Ignore a block:

```markdown
<!-- concept-drift-ignore-start -->
Bad example text here, spanning multiple lines.
<!-- concept-drift-ignore-end -->
```

An unclosed `<!-- concept-drift-ignore-start -->` (no matching end marker
before end of file) is itself a failure (`unclosed_ignore_block`) — it is
usually a sign that an entire section was accidentally excluded from
checking.

## 9. Common failures

### missing_required_term

**Meaning:** README or PRD no longer contains a required canonical term.

**Fix:** Restore the canonical architecture wording (see §6 above).

### forbidden_shrinkage_phrase / forbidden_shrinkage_pattern

**Meaning:** A public doc appears to define Po_core (or a layer) as a
smaller generic system.

**Fix:** Rewrite the sentence so Po_core remains a three-layer tensor
intelligence system. If the sentence is a legitimate example of *bad*
wording (e.g. in `docs/CONCEPT_DRIFT_GUARD.md`), wrap it in ignore markers
instead of rewording it (§8).

### missing_pr_template_concept_preservation_item

**Meaning:** The PR template no longer enforces concept preservation.

**Fix:** Restore the required checklist item in
`.github/PULL_REQUEST_TEMPLATE.md`.

### unclosed_ignore_block

**Meaning:** A concept-drift ignore block was opened but not closed.

**Fix:** Close the block with `<!-- concept-drift-ignore-end -->`, or remove
the stray start marker.

### missing_prd

**Meaning:** Neither `docs/PRD.md` nor `docs/spec/prd.md` exists.

**Fix:** Create `docs/PRD.md` aligned with the Original Design governance
(three-layer architecture, no unimplemented-runtime claims), or explicitly
document why PRD creation is deferred.

### missing_governance_doc

**Meaning:** One of the governance documents this gate itself depends on is
missing (`docs/CONCEPT_DRIFT_GUARD.md`,
`docs/operations/concept_drift_validation.md`,
`docs/governance/concept_drift_rules.json`).

**Fix:** Restore the missing file; these are not meant to be deleted.

## 10. What this does not test

This validation does not test:

- runtime behavior
- factual correctness
- trace continuity
- schema validation
- LLM output quality
- philosopher deliberation
- reconstruction execution
- safety gate correctness

It tests **public documentation wording only**: does the repository still
describe Po_core as the three-layer tensor intelligence system it is
architected to be, and does the PR process still ask contributors to affirm
that.

## 11. Future extensions

- Extend concept drift validation to ADRs and release docs once wording in
  those documents has stabilized.
- Add a release-doc public-claim validator (e.g. package metadata,
  PyPI description) so external-facing text is covered too.
- Add an AI-agent prompt preflight check that runs this validator before an
  agent starts a documentation-editing session, not just at PR time.
