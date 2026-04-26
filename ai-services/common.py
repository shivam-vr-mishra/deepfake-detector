"""Shared helpers for AI service modules."""
from __future__ import annotations

from typing import Literal, TypedDict


class DetectionResult(TypedDict):
    score: float
    label: str
    explanation: str
    confidence: Literal["low", "medium", "high"]


def confidence_band(score: float) -> str:
    """Map a probability into a coarse confidence label."""
    if score >= 0.85 or score <= 0.15:
        return "high"
    if score >= 0.7 or score <= 0.3:
        return "medium"
    return "low"


def label_from_score(score: float, *, positive: str = "AI Generated", negative: str = "Real") -> str:
    return positive if score >= 0.5 else negative


def make_result(score: float, explanation: str, *, positive: str = "AI Generated", negative: str = "Real") -> DetectionResult:
    score = max(0.0, min(1.0, float(score)))
    return DetectionResult(
        score=score,
        label=label_from_score(score, positive=positive, negative=negative),
        explanation=explanation,
        confidence=confidence_band(score),
    )
