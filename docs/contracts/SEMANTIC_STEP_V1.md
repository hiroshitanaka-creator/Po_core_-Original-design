# semantic_step v1 — Design Contract

> PR-002 domain contract. Schema/design only — no runtime wiring yet.
> See `docs/contracts/CONTRACT_OVERVIEW.md` for how this fits with the other four contracts.

## 1. Purpose

`semantic_step` represents one decomposed unit of generated speech plus its `semantic_profile`.

## 2. Role in three-layer architecture

`semantic_step` is the unit **Po_core (Layer 1)** emits for **Po_self (Layer 2)** to reason
about. A `po_self_decision`'s `target_step_ids` refer to `semantic_step.step_id` values, not raw
text offsets — this keeps Po_self's reasoning attached to structured, traceable units rather than
opaque strings.

## 3. Schema file path

`schemas/semantic_step_v1.schema.json`

## 4. Required fields

`schema_version`, `step_id`, `source`, `content`, `semantic_profile`, `trace_refs`, `created_at`.

## 5. Field table

| Field | Type | Range / Enum | Notes |
|---|---|---|---|
| `schema_version` | string (const) | `semantic_step_v1` | |
| `step_id` | string | non-empty | e.g. `step_001` |
| `source.output_id` | string | non-empty | |
| `source.proposal_id` | string | non-empty | |
| `source.origin` | enum | `po_core`/`philosopher_module`/`reconstructed`/`fallback`/`viewer`/`external` | |
| `content` | string | minLength 1 | |
| `semantic_profile` | object | mirrors `semantic_profile_v1` | see note below |
| `trace_refs` | array\<string\> | may be empty | related `Po_trace` event IDs |
| `created_at` | string | ISO 8601 date-time | |

**Note on `semantic_profile`:** the nested structure is duplicated inline in
`schemas/semantic_step_v1.schema.json` rather than referenced via JSON Schema `$ref`, to keep
this contract self-contained without requiring a multi-file schema resolver in the validation
tooling. The two definitions (`schemas/semantic_profile_v1.schema.json` and the inline copy) must
be kept in sync; a future runtime PR may switch to `$ref` once a schema registry/resolver is
part of the validation pipeline.

## 6. Invariants

- A `semantic_step` is not the entire response unless the response only has one step.
- Multiple `semantic_step` objects may belong to one proposal or output.
- Po_self decisions should refer to `semantic_step` IDs, not raw text offsets only.

## 7. Valid example path

`examples/contracts/semantic_step.valid.json`

## 8. What this contract does NOT implement yet

- No production code decomposes Po_core output into `semantic_step` objects today.
- `source.origin` values (`po_core`, `philosopher_module`, `reconstructed`, `fallback`, `viewer`,
  `external`) are conceptual placeholders for how a future pipeline might tag step provenance;
  none of these tags are emitted by the current `run_turn` pipeline.

## 9. Future implementation notes

- When Phase 2 (`docs/ROADMAP.md`) formalizes the mapping from existing tensor output to this
  contract, decide whether one `semantic_step` corresponds to one philosopher proposal, one
  Pareto-aggregated winner, or a finer decomposition of the winning proposal's text.
