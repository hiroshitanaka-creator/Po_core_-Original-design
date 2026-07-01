"""
PR-003 Po_core Kernel MVP.

PoCoreKernel.process() is the first minimal runtime bridge from the PR-002
design contracts to executable code: it decomposes raw text into
semantic_step objects, computes a deterministic semantic_profile stub for
each step, and emits exactly one SemanticProfileComputed Po_trace event.

This is NOT the full Po_core runtime. It does not implement Po_self
recursion, Viewer feedback, philosopher deliberation, safety gates, or any
ML scoring. See docs/contracts/CONTRACT_OVERVIEW.md and docs/ROADMAP.md
Phase 2.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from po_core_original.models import KernelResult, SemanticStep, SemanticStepSource
from po_core_original.semantic_profile_engine import SemanticProfileEngine
from po_core_original.step_decomposer import StepDecomposer
from po_core_original.trace import create_trace_event

_PROPOSAL_ID = "kernel_mvp"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


class PoCoreKernel:
    """Deterministic MVP bridge: text -> semantic_step[] -> Po_trace event.

    Not a final AI answer -- a traceable semantic profiling kernel.
    """

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
        request_id = request_id or f"req_{uuid.uuid4().hex}"
        output_id = f"out_{request_id[:8]}"

        segments = self._decomposer.decompose(input_text)

        semantic_steps: List[SemanticStep] = []
        step_summaries: List[Dict[str, Any]] = []

        for index, content in enumerate(segments, start=1):
            profile = self._profile_engine.profile_step(
                content, step_index=index, request_id=request_id
            )
            step_id = f"step_{index:03d}"
            step = SemanticStep(
                step_id=step_id,
                source=SemanticStepSource(
                    output_id=output_id,
                    proposal_id=_PROPOSAL_ID,
                    origin="po_core",
                ),
                content=content,
                semantic_profile=profile,
                created_at=_utc_now_iso(),
            )
            semantic_steps.append(step)
            step_summaries.append(
                {
                    "step_id": step_id,
                    "profile_id": profile.profile_id,
                    "primary_axis": profile.primary_axis,
                    "priority_score": profile.priority_score,
                    "alert_level": profile.alert_level.level,
                    # ethics_delta / responsibility_pressure (PR-004): included so
                    # PoSelfController can evaluate reconstruct triggers by reading
                    # this trace event's payload alone, without reaching back into
                    # semantic_steps -- Po_trace is the substrate Po_self reads
                    # (docs/contracts/PO_TRACE_EVENT_V1.md).
                    "ethics_delta": profile.ethics_delta,
                    "responsibility_pressure": profile.responsibility_pressure,
                }
            )

        payload = {
            "output_id": output_id,
            "proposal_id": _PROPOSAL_ID,
            "step_count": len(semantic_steps),
            "steps": step_summaries,
        }

        trace_event = create_trace_event(
            request_id=request_id,
            event_type="SemanticProfileComputed",
            payload=payload,
        )

        for step in semantic_steps:
            step.trace_refs.append(trace_event.event_id)

        return KernelResult(
            request_id=request_id,
            input_text=input_text,
            semantic_steps=semantic_steps,
            trace_events=[trace_event],
        )
