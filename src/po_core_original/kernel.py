"""po_core_original.kernel

``PoCoreKernel`` — the first runtime activation point of the Po_core tensor
kernel (PR-003), bridging the PR-002 design contracts into executable code.

Flow::

    raw input text
        -> PoCoreKernel.process(input_text)
        -> SemanticStep[]              (via StepDecomposer + SemanticProfileEngine)
        -> SemanticProfile[]
        -> PoTraceEvent("SemanticProfileComputed")
        -> KernelResult

Scope (honesty requirement, docs/STRICT_CORE_RULES.md):
    This is the first executable seed of the full architecture — the Po_core
    (Layer 1) side: deterministic step decomposition, deterministic
    semantic-profile scoring, and one ``SemanticProfileComputed`` Po_trace
    emission. It is structurally aligned with the final three-layer model so
    the later layers can grow onto it without redesign: Po_self (Layer 2) will
    read the emitted trace; Viewer (Layer 3) will return feedback tensors. It
    is not a generic evaluator and not a reduced product.

    Not yet grown (preserved as concepts, see docs/): Po_self recursion,
    the Viewer feedback loop, philosopher deliberation, safety-gate runtime,
    LLM calls, and ML tensor scoring.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from .models import (
    SEMANTIC_STEP_SCHEMA_VERSION,
    KernelResult,
    SemanticStep,
    SemanticStepSource,
)
from .semantic_profile_engine import SemanticProfileEngine, _short_request_id
from .step_decomposer import StepDecomposer
from .trace import create_trace_event

# Fixed provenance for the MVP: every step comes from Po_core, one proposal.
_MVP_PROPOSAL_ID = "kernel_mvp"
_MVP_ORIGIN = "po_core"
_SEMANTIC_PROFILE_COMPUTED = "SemanticProfileComputed"


class PoCoreKernel:
    """Po_core (Layer 1) kernel seed: text -> semantic steps + Po_trace."""

    def __init__(
        self,
        decomposer: Optional[StepDecomposer] = None,
        profile_engine: Optional[SemanticProfileEngine] = None,
    ) -> None:
        self._decomposer = decomposer or StepDecomposer()
        self._profile_engine = profile_engine or SemanticProfileEngine()

    def process(
        self, input_text: str, *, request_id: Optional[str] = None
    ) -> KernelResult:
        """Decompose ``input_text``, profile each step, and emit one trace event.

        Raises:
            ValueError: if ``input_text`` is empty/whitespace-only.
        """
        if request_id is None:
            request_id = f"req_{uuid.uuid4().hex}"

        request_short = _short_request_id(request_id)
        output_id = f"out_{request_short}"

        contents = self._decomposer.decompose(input_text)

        steps = []
        step_summaries = []
        for index, content in enumerate(contents, start=1):
            profile = self._profile_engine.profile_step(
                content, step_index=index, request_id=request_id
            )
            step = SemanticStep(
                schema_version=SEMANTIC_STEP_SCHEMA_VERSION,
                step_id=f"step_{index:03d}",
                source=SemanticStepSource(
                    output_id=output_id,
                    proposal_id=_MVP_PROPOSAL_ID,
                    origin=_MVP_ORIGIN,
                ),
                content=content,
                semantic_profile=profile,
                trace_refs=[],  # populated below once the event id exists
                created_at=datetime.now(timezone.utc).isoformat(),
            )
            steps.append(step)
            step_summaries.append(
                {
                    "step_id": step.step_id,
                    "profile_id": profile.profile_id,
                    "primary_axis": profile.primary_axis,
                    "priority_score": profile.priority_score,
                    "alert_level": profile.alert_level.level,
                }
            )

        payload = {
            "output_id": output_id,
            "proposal_id": _MVP_PROPOSAL_ID,
            "step_count": len(steps),
            "steps": step_summaries,
        }

        trace_event = create_trace_event(
            request_id=request_id,
            event_type=_SEMANTIC_PROFILE_COMPUTED,
            payload=payload,
        )

        # Back-reference the emitted event id from every semantic step so
        # Po_self (a future consumer) can follow trace_refs -> Po_trace event.
        for step in steps:
            step.trace_refs.append(trace_event.event_id)

        return KernelResult(
            request_id=request_id,
            input_text=input_text,
            semantic_steps=steps,
            trace_events=[trace_event],
        )
