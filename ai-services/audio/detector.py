"""Audio / voice-synthesis detector.

Default model: ``MelodyMachine/Deepfake-audio-detection-V2`` — a wav2vec2
classifier on HuggingFace. Falls back to a spectrogram-based heuristic if the
model can't be loaded.
"""
from __future__ import annotations

import io
import os
import sys
import tempfile
from pathlib import Path
from threading import Lock
from typing import Any

import numpy as np

sys.path.append(str(Path(__file__).resolve().parents[1]))
from common import DetectionResult, make_result  # type: ignore  # noqa: E402

MODEL_NAME = os.getenv(
    "DEEPFAKE_AUDIO_MODEL", "MelodyMachine/Deepfake-audio-detection-V2"
)

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

            _pipe = pipeline("audio-classification", model=MODEL_NAME, device=-1)
        except Exception as exc:  # pragma: no cover
            _pipe = ("error", str(exc))
    return _pipe


def _spectrogram_heuristic(samples: np.ndarray, sr: int, error: str) -> DetectionResult:
    """Heuristic fallback: synthetic voices tend to have flatter
    spectro-temporal energy. We compute the mean of the temporal derivative
    of the mel-spectrogram and map it to a score."""
    import librosa

    mel = librosa.feature.melspectrogram(y=samples, sr=sr, n_mels=64)
    mel_db = librosa.power_to_db(mel)
    flux = float(np.mean(np.abs(np.diff(mel_db, axis=1))))
    score = float(max(0.0, min(1.0, 1.0 - flux / 8.0)))
    return make_result(
        score,
        f"Audio model unavailable ({error[:120]}). Heuristic spectral-flux="
        f"{flux:.3f} → fake-score={score:.3f}.",
    )


def detect_audio(data: bytes, extension: str = ".wav") -> DetectionResult:
    import librosa

    with tempfile.NamedTemporaryFile(suffix=extension, delete=False) as tmp:
        tmp.write(data)
        tmp_path = tmp.name

    try:
        samples, sr = librosa.load(tmp_path, sr=16000, mono=True)
    finally:
        try:
            Path(tmp_path).unlink(missing_ok=True)
        except OSError:
            pass

    if samples.size == 0:
        return make_result(0.5, "Empty or unreadable audio stream.")

    pipe = _load_pipe()
    if isinstance(pipe, tuple) and pipe[0] == "error":
        return _spectrogram_heuristic(samples, sr, pipe[1])

    preds = pipe({"array": samples, "sampling_rate": sr})
    fake_score = 0.0
    for p in preds:
        if p["label"].lower() in {"fake", "spoof", "ai", "synthetic"}:
            fake_score = max(fake_score, float(p["score"]))
    if not fake_score and preds:
        fake_score = float(preds[0]["score"])

    explanation = (
        f"Model {MODEL_NAME} produced predictions: "
        + ", ".join(f"{p['label']}={p['score']:.2f}" for p in preds[:3])
        + f". Synthetic-voice probability = {fake_score:.3f}."
    )
    return make_result(fake_score, explanation, positive="AI Generated", negative="Real")
