# ADR Index (Original Design)

> Index of Architecture Decision Records for the **Original Design governance
> layer** (`src/po_core_original/` + its governance docs/scripts/CI). This is
> a separate, independently-numbered ADR system from the main `po_core`
> package's `docs/adr/` (see ADR-0001 for why). Validated by
> `scripts/check_adr_index.py` — see `docs/operations/adr_process.md`.

| ADR | Title | Status | Date | Summary |
|---|---|---|---|---|
| ADR-0001 | Adopt ADR System for Original Design Architecture Changes | Accepted | 2026-07-02 | Establishes ADR governance for Original Design architecture-impacting changes, in a directory separate from the main-track `docs/adr/` to avoid a case-only filename collision. |
| ADR-0002 | Po_trace_blocked / Po_self_seedling / Semantic Jump Tensor — Seed-Level Contracts | Accepted | 2026-07-02 | Grows `jump`, blocked-trace preservation, and Po_self bootstrap evaluation from documentation-only into seed-level, feature-flagged, non-destructive runtime; extends `TRACE_CONTINUITY_V1.md` with 6 new rules before the corresponding runtime shipped. |
| ADR-0003 | Blocked Trace Reactivation Planning — Seed-Level Contract | Accepted | 2026-07-03 | Adds `PoTraceReactivationPlanner`, the first control layer converting a blocked trace + seedling reading into a traceable reactivation-candidate plan (never reactivation execution); extends `TRACE_CONTINUITY_V1.md` with 2 new rules (+1 broadened) before the corresponding runtime shipped. |
| ADR-0004 | Controlled Blocked Trace Reactivation Proposal Executor — Seed-Level Contract | Accepted | 2026-07-04 | Adds `ControlledBlockedTraceReactivationProposalExecutor`, the second control layer converting a `PoTraceReactivationPlan` into a deterministic reactivation proposal (never reactivation execution); extends `TRACE_CONTINUITY_V1.md` with 1 new rule before the corresponding runtime shipped. |
| ADR-0005 | Semantic Jump Frame Proposal Executor — Seed-Level Contract | Accepted | 2026-07-05 | Adds `ControlledSemanticJumpFrameProposalExecutor`, converting a `SemanticJumpPlan` into a deterministic `SemanticFrameProposal` (never an actual semantic frame change); re-verifies the plan's `requires_human_review` invariant and the originating tensor's `jump_recommended` flag in place of `*_allowed` flags; extends `TRACE_CONTINUITY_V1.md` with 1 new rule before the corresponding runtime shipped. |
| ADR-0006 | Semantic Jump Human Review Gate — Seed-Level Contract | Accepted | 2026-07-08 | Adds `SemanticJumpHumanReviewGate`, sending a `SemanticFrameProposal` to a human-reviewable gate and recording an `approved`/`rejected`/`needs_revision` decision (never an actual semantic jump execution, even when approved); `execution_authorized` is data for a future executor only, with no code path to execution; extends `TRACE_CONTINUITY_V1.md` with 2 new rules before the corresponding runtime shipped. |

`ADR-0000-template.md` is the template and is intentionally **not** listed
above as a decision.
