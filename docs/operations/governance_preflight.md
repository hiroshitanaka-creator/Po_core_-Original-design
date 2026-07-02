# Governance Preflight — Operations Guide

> PR-012 governance documentation. This document explains how to run
> `scripts/governance_preflight.py`, the single aggregate command that runs
> the existing concept drift, trace continuity, ADR index, and schema/example
> validators. **It adds no new runtime behavior.** It only orchestrates
> validators introduced by earlier PRs via `subprocess`. See
> `docs/operations/concept_drift_validation.md`,
> `docs/operations/trace_continuity_validation.md`, and
> `docs/operations/adr_process.md` for the individual validators it
> aggregates.

## 1. Purpose

Before PR-012, a contributor or AI agent who wanted full governance
confidence had to remember and run four separate commands. Missing one
(usually ADR index or schema validation) was easy, especially for AI coding
agents operating from partial context. `scripts/governance_preflight.py`
gives a single, deterministic entry point that runs all four and reports one
clear pass/fail result.

## 2. What checks are aggregated

| Check name      | Underlying command                                                                 | Introduced by |
|------------------|--------------------------------------------------------------------------------------|---------------|
| `concept-drift`  | `python scripts/check_concept_drift.py --check-pr-template`                          | PR-010        |
| `trace`          | `python scripts/validate_trace_continuity.py --include-negative`                     | PR-009        |
| `adr`            | `python scripts/check_adr_index.py`                                                  | PR-011        |
| `schemas`        | `python -m pytest tests/test_contract_schemas.py -v --noconftest -p no:cacheprovider` | PR-002        |

The aggregator does not reimplement any validator's logic — it only invokes
the existing scripts/tests as subprocesses and summarizes their results. The
schema check adds `--noconftest -p no:cacheprovider` (matching the existing
`trace-continuity.yml` and `adr-index.yml` workflows) so that this
governance-only check does not require installing the full Po_core runtime
dependency set (numpy, torch, etc.) pulled in by `tests/conftest.py`.

## 3. When to run

Run governance preflight before opening or updating a PR that modifies:

- README
- PRD
- strict core rules
- architecture docs
- governance docs
- schemas
- contract docs
- trace examples
- ADRs
- PR templates
- governance scripts
- trace continuity
- concept drift rules

## 4. Local commands

```bash
python scripts/governance_preflight.py
python scripts/governance_preflight.py --json
python scripts/governance_preflight.py --only concept-drift
python scripts/governance_preflight.py --only trace
python scripts/governance_preflight.py --only adr
python scripts/governance_preflight.py --only schemas
python scripts/governance_preflight.py --fail-fast
python scripts/governance_preflight.py --list-checks
```

`--only` accepts repeated flags or a comma-separated list
(e.g. `--only trace,adr`).

## 5. CI workflow explanation

`.github/workflows/governance-preflight.yml` runs
`python scripts/governance_preflight.py` on `pull_request` when governance,
docs, schema, example, or governance-script paths change, and can also be
triggered manually via `workflow_dispatch`. It is governance-only: it
installs only `pytest` and `jsonschema`, performs no runtime integration
tests, requires no secrets or network access, and does not publish
artifacts or mutate the repository. It does not replace the existing
`Concept Drift`, `Trace Continuity`, or `ADR Index` workflows — it
aggregates the same underlying checks into one additional, optional gate.

## 6. Exit codes

| Code | Meaning                                                              |
|------|-----------------------------------------------------------------------|
| `0`  | All selected checks passed.                                          |
| `1`  | One or more selected checks failed.                                  |
| `2`  | CLI usage/configuration error (e.g. unknown `--only` value).          |
| `3`  | A required check file (validator script or test module) is missing.  |

## 7. Options

| Option           | Behavior                                                                                   |
|-------------------|---------------------------------------------------------------------------------------------|
| `--json`          | Print a machine-readable JSON summary (`{"valid": bool, "checks": [...]}`) instead of text. |
| `--skip-tests`    | Skip pytest-based checks (currently `schemas`). **Do not use for final PR validation unless justified** — it silently narrows coverage. |
| `--only NAME[,NAME...]` | Run only the named check(s). Repeatable and/or comma-separated. Allowed values: `concept-drift`, `trace`, `adr`, `schemas`. Unknown values exit `2` and print the allowed list. |
| `--fail-fast`     | Stop after the first failed (or missing) check instead of running all selected checks.      |
| `--list-checks`   | Print the available checks and exit `0` without running anything.                           |

## 8. Common failures

### concept-drift failed
Meaning:
Public docs may have shrunk Po_core into a generic chatbot, generic
decision-support tool, safety wrapper, or philosopher demo.
Fix:
Run `python scripts/check_concept_drift.py --check-pr-template` and fix
reported wording.

### trace failed
Meaning:
Trace continuity examples or trace graph validation failed.
Fix:
Run `python scripts/validate_trace_continuity.py --include-negative`.

### adr failed
Meaning:
ADR index or ADR files are inconsistent.
Fix:
Run `python scripts/check_adr_index.py`.

### schemas failed
Meaning:
Contract schema examples or schema tests failed.
Fix:
Run `python -m pytest tests/test_contract_schemas.py -v`.

## 9. What this does not test

This preflight does not test:

- runtime behavior correctness
- performance
- LLM output quality
- philosopher deliberation
- actual content rewriting
- REST API behavior
- Viewer UI behavior
- production release readiness

## 10. Future extensions

- Promote Governance Preflight to a required branch-protection check after
  stabilization.
- Aggregate release-readiness checks alongside governance checks.
- Add an AI-agent preflight wrapper that prints required reading before
  running the checks (see recommended PR-013).
