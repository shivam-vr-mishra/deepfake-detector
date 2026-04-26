"""AI-text detector.

Combines:
  1. A pre-trained classifier (``roberta-base-openai-detector``)
  2. A perplexity-style burstiness signal computed from token entropy

The two signals are fused with a weighted average. Both are fully
swappable — change ``MODEL_NAME`` to plug in a different classifier.
"""
from __future__ import annotations

import math
import os
import sys
from collections import Counter
from pathlib import Path
from threading import Lock
from typing import Any

sys.path.append(str(Path(__file__).resolve().parents[1]))
from common import DetectionResult, make_result  # type: ignore  # noqa: E402

MODEL_NAME = os.getenv("DEEPFAKE_TEXT_MODEL", "roberta-base-openai-detector")

_pipe: Any | None = None
_lock = Lock()


def _load_pipe():
    global _pipe
    if _pipe is not None:
        return _pipe
    with _lock:
        if _pipe is not None:
            return _pipe
        try:
            from transformers import pipeline

            _pipe = pipeline("text-classification", model=MODEL_NAME, device=-1)
        except Exception as exc:  # pragma: no cover
            _pipe = ("error", str(exc))
    return _pipe


def _burstiness(text: str) -> float:
    """A naive burstiness/perplexity proxy in [0,1].

    Lower entropy ⇒ more uniform / repetitive ⇒ more likely AI.
    """
    tokens = [t.lower() for t in text.split() if t.strip()]
    if not tokens:
        return 0.5
    counts = Counter(tokens)
    total = sum(counts.values())
    entropy = -sum((c / total) * math.log2(c / total) for c in counts.values())
    # Normalize roughly into [0,1]: AI-y text tends to have entropy ~6-8 vs
    # ~9-12 for varied human prose.
    norm = max(0.0, min(1.0, (10.0 - entropy) / 6.0))
    return norm


def detect_text(text: str) -> DetectionResult:
    text = text.strip()
    if not text:
        return make_result(0.5, "Empty text.")

    burst = _burstiness(text)

    pipe = _load_pipe()
    if isinstance(pipe, tuple) and pipe[0] == "error":
        return make_result(
            burst,
            f"Text classifier unavailable ({pipe[1][:120]}). "
            f"Falling back to lexical-burstiness score = {burst:.3f}.",
        )

    # Most classifiers truncate; just send first 4000 chars.
    preds = pipe(text[:4000], top_k=None)
    ai_score = 0.0
    for p in preds:
        label = p["label"].lower()
        if label in {"fake", "ai", "machine-generated", "label_1", "ai-generated"}:
            ai_score = max(ai_score, float(p["score"]))
    if not ai_score and preds:
        # Pick the higher of the two scores when label naming is unfamiliar.
        ai_score = max(float(p["score"]) for p in preds)

    final = 0.7 * ai_score + 0.3 * burst
    explanation = (
        f"Classifier {MODEL_NAME}: AI-prob={ai_score:.3f}. "
        f"Lexical burstiness signal: {burst:.3f}. "
        f"Fused score = 0.7·classifier + 0.3·burstiness = {final:.3f}."
    )
    return make_result(final, explanation, positive="AI Generated", negative="Human")
