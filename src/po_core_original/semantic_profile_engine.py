"""po_core_original.semantic_profile_engine

Deterministic seed scoring for computing a ``SemanticProfile`` from step text.

IMPORTANT: This is the **deterministic seed of the Po_core tensor computation,
not yet the final semantic intelligence.** It occupies the real architectural
slot where the full tensor engine will grow; today it is a transparent,
rule-based keyword/heuristic placeholder with NO machine learning, NO
embeddings, and NO LLM. Its only guarantees are:

  * same input text + same request_id + same step_index -> identical profile
    (except ``created_at``, which is a timestamp);
  * every field lands inside the ranges required by
    ``schemas/semantic_profile_v1.schema.json``.

A future runtime PR is expected to replace this scoring with the real Po_core
tensor computation (see docs/contracts/SEMANTIC_PROFILE_V1.md, section 9).
"""

from __future__ import annotations

from datetime import datetime, timezone

from .models import (
    SEMANTIC_PROFILE_SCHEMA_VERSION,
    AlertLevel,
    ImpactFieldTensor,
    SemanticProfile,
)

# Base value every axis starts at before heuristics fire.
_BASE_AXIS = 0.1
# Amount each matched keyword/rule adds to an axis.
_INCREMENT = 0.2

# Axis weights used to turn a normalized alert score into an action-ordering
# priority score. Ethical / responsibility axes weigh most (Po_core's mission
# is meaning + responsibility, not generic helpfulness).
_WEIGHTS = {
    "factual_axis": 2.0,
    "causal_axis": 1.7,
    "emotional_axis": 1.2,
    "ethical_axis": 2.5,
    "responsibility_axis": 2.3,
    "mixed": 2.0,
}

# Keyword tables. Japanese entries are matched as-is; English entries are
# matched case-insensitively (content is lowercased before English lookup).
_FACTUAL_KEYWORDS = [
    "事実",
    "データ",
    "証拠",
    "火星",
    "地球",
    "酸素",
    "大気",
    "fact",
    "data",
    "evidence",
    "mars",
    "earth",
    "oxygen",
    "atmosphere",
]
_CAUSAL_KEYWORDS = [
    "だから",
    "なぜなら",
    "原因",
    "結果",
    "影響",
    "because",
    "therefore",
    "cause",
    "result",
    "leads to",
]
_EMOTIONAL_KEYWORDS = [
    "夢",
    "怖い",
    "嬉しい",
    "悲しい",
    "不安",
    "hope",
    "fear",
    "happy",
    "sad",
    "anxiety",
]
_ETHICAL_KEYWORDS = [
    "倫理",
    "責任",
    "危険",
    "害",
    "安全",
    "正義",
    "ethical",
    "responsibility",
    "harm",
    "safe",
    "justice",
    "risk",
]
_RESPONSIBILITY_KEYWORDS = [
    "べき",
    "しなければならない",
    "判断",
    "決断",
    "責任",
    "should",
    "must",
    "decision",
    "accountable",
    "responsible",
]


def _short_request_id(request_id: str) -> str:
    """Deterministic short form of a request id (for profile_id stability)."""
    return request_id.replace("-", "")[:8] or "req"


def _count_hits(content_lower: str, keywords: list[str]) -> int:
    """Count how many distinct keywords appear in ``content_lower``."""
    return sum(1 for kw in keywords if kw in content_lower)


def _axis_score(hits: int) -> float:
    """Map a hit count to a clamped 0.0..1.0 axis score."""
    return min(_BASE_AXIS + _INCREMENT * hits, 1.0)


class SemanticProfileEngine:
    """Compute a deterministic ``SemanticProfile`` for one step of content."""

    def profile_step(
        self, content: str, *, step_index: int, request_id: str
    ) -> SemanticProfile:
        content_lower = content.lower()

        # --- axis heuristics -------------------------------------------------
        factual_hits = _count_hits(content_lower, _FACTUAL_KEYWORDS)
        # Numbers / percentages read as factual-looking claims.
        if any(ch.isdigit() for ch in content):
            factual_hits += 1
        causal_hits = _count_hits(content_lower, _CAUSAL_KEYWORDS)
        emotional_hits = _count_hits(content_lower, _EMOTIONAL_KEYWORDS)
        ethical_hits = _count_hits(content_lower, _ETHICAL_KEYWORDS)
        responsibility_hits = _count_hits(content_lower, _RESPONSIBILITY_KEYWORDS)

        total_hits = (
            factual_hits
            + causal_hits
            + emotional_hits
            + ethical_hits
            + responsibility_hits
        )

        axes = {
            "factual_axis": _axis_score(factual_hits),
            "causal_axis": _axis_score(causal_hits),
            "emotional_axis": _axis_score(emotional_hits),
            "ethical_axis": _axis_score(ethical_hits),
            "responsibility_axis": _axis_score(responsibility_hits),
        }

        tensor = ImpactFieldTensor(
            factual_axis=round(axes["factual_axis"], 4),
            causal_axis=round(axes["causal_axis"], 4),
            emotional_axis=round(axes["emotional_axis"], 4),
            ethical_axis=round(axes["ethical_axis"], 4),
            responsibility_axis=round(axes["responsibility_axis"], 4),
        )

        # --- primary axis ----------------------------------------------------
        # Sort by (score desc, name asc) so ties are broken deterministically.
        ranked = sorted(axes.items(), key=lambda kv: (-kv[1], kv[0]))
        top_name, top_score = ranked[0]
        second_score = ranked[1][1]
        if (top_score - second_score) <= 0.05:
            primary_axis = "mixed"
        else:
            primary_axis = top_name

        # --- alert score / level --------------------------------------------
        alert_score = round(max(axes.values()), 4)
        alert_level = _classify_alert(alert_score)
        if primary_axis == "mixed":
            tied = [name for name, score in axes.items() if (top_score - score) <= 0.05]
            reason = (
                f"Multiple axes are close ({', '.join(sorted(tied))}); "
                f"no single axis dominates at score {alert_score}."
            )
        else:
            reason = (
                f"{primary_axis} dominated at score {alert_score} "
                f"({'no' if total_hits == 0 else 'keyword'} heuristics fired)."
            )

        # --- derived pressures ----------------------------------------------
        priority_score = round(alert_score * _WEIGHTS[primary_axis], 4)
        ethics_delta = round(_clamp(axes["ethical_axis"] - _BASE_AXIS, -1.0, 1.0), 4)
        responsibility_pressure = round(axes["responsibility_axis"], 4)
        freedom_pressure = round(
            max(axes["ethical_axis"], axes["responsibility_axis"], axes["causal_axis"]),
            4,
        )
        confidence = 0.6 if total_hits > 0 else 0.3

        profile_id = f"sp_{_short_request_id(request_id)}_{step_index}"
        created_at = datetime.now(timezone.utc).isoformat()

        justification = (
            "Deterministic seed scoring (rule-based keyword heuristics, not yet "
            f"final tensor intelligence): {reason}"
        )

        return SemanticProfile(
            schema_version=SEMANTIC_PROFILE_SCHEMA_VERSION,
            profile_id=profile_id,
            impact_field_tensor=tensor,
            alert_level=AlertLevel(score=alert_score, level=alert_level, reason=reason),
            primary_axis=primary_axis,
            priority_score=priority_score,
            ethics_delta=ethics_delta,
            responsibility_pressure=responsibility_pressure,
            freedom_pressure=freedom_pressure,
            confidence=confidence,
            justification=justification,
            created_at=created_at,
        )


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _classify_alert(score: float) -> str:
    if score < 0.25:
        return "low"
    if score < 0.5:
        return "medium"
    if score < 0.8:
        return "high"
    return "critical"
