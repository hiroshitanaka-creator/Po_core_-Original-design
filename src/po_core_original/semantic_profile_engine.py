"""
PR-003 Po_core Kernel MVP — semantic_profile generation engine.

This is a **deterministic MVP stub, not final semantic intelligence**.
Scores are produced by simple keyword/rule heuristics over five fixed axes
(factual, causal, emotional, ethical, responsibility). It exists to give the
Po_trace substrate a real (if placeholder) semantic_profile payload to carry,
per docs/contracts/SEMANTIC_PROFILE_V1.md -- it is not real ML scoring and
must not be described as such.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Dict, List, Tuple

from po_core_original.models import AlertLevel, ImpactFieldTensor, SemanticProfile

_BASE_SCORE = 0.1
_KEYWORD_INCREMENT = 0.15

_FACTUAL_KEYWORDS: List[str] = [
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
_CAUSAL_KEYWORDS: List[str] = [
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
_EMOTIONAL_KEYWORDS: List[str] = [
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
_ETHICAL_KEYWORDS: List[str] = [
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
_RESPONSIBILITY_KEYWORDS: List[str] = [
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

_NUMERIC_PATTERN = re.compile(r"\d|%|％")

_PRIORITY_WEIGHTS: Dict[str, float] = {
    "factual_axis": 2.0,
    "causal_axis": 1.7,
    "emotional_axis": 1.2,
    "ethical_axis": 2.5,
    "responsibility_axis": 2.3,
    "mixed": 2.0,
}

_ALERT_THRESHOLDS: Tuple[Tuple[float, str], ...] = (
    (0.8, "critical"),
    (0.5, "high"),
    (0.25, "medium"),
)


def _clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, value))


def _count_hits(content_lower: str, keywords: List[str]) -> int:
    return sum(1 for kw in keywords if kw.lower() in content_lower)


def _score_axis(hits: int) -> float:
    return _clamp(_BASE_SCORE + hits * _KEYWORD_INCREMENT)


def _alert_level_for(score: float) -> str:
    for threshold, level in _ALERT_THRESHOLDS:
        if score >= threshold:
            return level
    return "low"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


class SemanticProfileEngine:
    """Deterministic MVP stub, not final semantic intelligence."""

    def profile_step(
        self, content: str, *, step_index: int, request_id: str
    ) -> SemanticProfile:
        content_lower = content.lower()

        factual_hits = _count_hits(content_lower, _FACTUAL_KEYWORDS)
        has_numeric = bool(_NUMERIC_PATTERN.search(content))
        if has_numeric:
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

        factual_axis = _score_axis(factual_hits)
        causal_axis = _score_axis(causal_hits)
        emotional_axis = _score_axis(emotional_hits)
        ethical_axis = _score_axis(ethical_hits)
        responsibility_axis = _score_axis(responsibility_hits)

        axis_scores: Dict[str, float] = {
            "factual_axis": factual_axis,
            "causal_axis": causal_axis,
            "emotional_axis": emotional_axis,
            "ethical_axis": ethical_axis,
            "responsibility_axis": responsibility_axis,
        }
        ranked = sorted(axis_scores.items(), key=lambda kv: kv[1], reverse=True)
        top_axis, top_score = ranked[0]
        second_axis, second_score = ranked[1]

        if (top_score - second_score) <= 0.05:
            primary_axis = "mixed"
            reason = (
                f"Top axes '{top_axis}' ({top_score:.2f}) and '{second_axis}' "
                f"({second_score:.2f}) are within 0.05; classified as mixed."
            )
        else:
            primary_axis = top_axis
            reason = f"'{top_axis}' scored highest at {top_score:.2f}, dominating the profile."

        alert_score = top_score
        alert_level_name = _alert_level_for(alert_score)
        alert_level = AlertLevel(
            score=round(alert_score, 4),
            level=alert_level_name,
            reason=reason,
        )

        priority_score = round(alert_score * _PRIORITY_WEIGHTS[primary_axis], 4)
        ethics_delta = round(_clamp(ethical_axis - _BASE_SCORE, -1.0, 1.0), 4)
        responsibility_pressure = round(responsibility_axis, 4)
        freedom_pressure = round(max(ethical_axis, responsibility_axis, causal_axis), 4)
        confidence = 0.6 if total_hits > 0 else 0.3

        request_id_short = request_id[:8] if request_id else "unknown"
        profile_id = f"sp_{request_id_short}_{step_index}"

        justification = f"Deterministic MVP stub scoring: {total_hits} keyword/rule hit(s) detected. {reason}"

        return SemanticProfile(
            profile_id=profile_id,
            impact_field_tensor=ImpactFieldTensor(
                factual_axis=factual_axis,
                causal_axis=causal_axis,
                emotional_axis=emotional_axis,
                ethical_axis=ethical_axis,
                responsibility_axis=responsibility_axis,
            ),
            alert_level=alert_level,
            primary_axis=primary_axis,
            priority_score=priority_score,
            ethics_delta=ethics_delta,
            responsibility_pressure=responsibility_pressure,
            freedom_pressure=freedom_pressure,
            confidence=confidence,
            justification=justification,
            created_at=_utc_now_iso(),
        )
