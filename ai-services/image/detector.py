"""Image deepfake detector.

Default model: ``prithivMLmods/Deep-Fake-Detector-v2-Model`` — a public
fine-tuned ViT classifier on HuggingFace producing two labels:
``Real`` and ``Fake``.

The model is loaded lazily on the first call and cached. Swap this for any
other binary image classifier by editing ``MODEL_NAME``.
"""
from __future__ import annotations

import io
import os
from threading import Lock
from typing import Any

import sys
from pathlib import Path

from PIL import Image

sys.path.append(str(Path(__file__).resolve().parents[1]))
from common import DetectionResult, make_result  # type: ignore  # noqa: E402

MODEL_NAME = os.getenv(
    "DEEPFAKE_IMAGE_MODEL", "prithivMLmods/Deep-Fake-Detector-v2-Model"
)

_pipeline: Any | None = None
_lock = Lock()


def _load_pipeline():
    global _pipeline
    if _pipeline is not None:
        return _pipeline
    with _lock:
        if _pipeline is not None:
            return _pipeline
        try:
            from transformers import pipeline

            _pipeline = pipeline(
                "image-classification", model=MODEL_NAME, device=-1
            )
        except Exception as exc:  # pragma: no cover
            _pipeline = ("error", str(exc))
    return _pipeline


def detect_image(data: bytes) -> DetectionResult:
    """Return deepfake probability for an image."""
    img = Image.open(io.BytesIO(data)).convert("RGB")

    pipe = _load_pipeline()
    if isinstance(pipe, tuple) and pipe[0] == "error":
        # Fallback heuristic so the system stays usable when the model can't load.
        return _heuristic_fallback(img, model_error=pipe[1])

    preds = pipe(img)  # list[{'label': str, 'score': float}]
    fake_score = 0.0
    for p in preds:
        if p["label"].lower() in {"fake", "ai", "ai_generated", "deepfake"}:
            fake_score = max(fake_score, float(p["score"]))
    if not fake_score and preds:
        # If model labels are different, assume the highest score = "fake-ish"
        fake_score = float(preds[0]["score"])

    explanation = (
        f"Model {MODEL_NAME} classified this image with a deepfake "
        f"probability of {fake_score * 100:.2f}%. Top predictions: "
        + ", ".join(f"{p['label']}={p['score']:.2f}" for p in preds[:3])
    )
    return make_result(fake_score, explanation, positive="AI Generated", negative="Real")


def _heuristic_fallback(img: Image.Image, model_error: str) -> DetectionResult:
    """Very rough heuristic used only if the HF model can't be loaded."""
    import numpy as np

    arr = np.asarray(img.convert("L"), dtype=np.float32) / 255.0
    # GAN-y faces tend to have very smooth low-frequency patches and abnormal
    # symmetry. We use std of Laplacian as a proxy for natural texture.
    from scipy import ndimage

    lap = ndimage.laplace(arr)
    sharpness = float(lap.std())
    # Map sharpness to a fake-ish score (very crude, illustrative only).
    score = max(0.0, min(1.0, 1.0 - sharpness * 4))
    return make_result(
        score,
        f"Model unavailable ({model_error[:120]}). Heuristic score from "
        f"image sharpness={sharpness:.4f}.",
    )
