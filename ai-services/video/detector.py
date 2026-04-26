"""Video deepfake detector — frame sampling + image classifier.

We sample N evenly-spaced frames from the video, classify each frame using
the image deepfake detector, then aggregate (mean + max) into a single score.
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path
from typing import List

import cv2
import numpy as np
from PIL import Image

sys.path.append(str(Path(__file__).resolve().parents[1]))
from common import DetectionResult, make_result  # type: ignore  # noqa: E402
from image.detector import detect_image  # type: ignore  # noqa: E402

NUM_FRAMES = 16


def _sample_frames(path: str, num: int = NUM_FRAMES) -> List[np.ndarray]:
    cap = cv2.VideoCapture(path)
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    if total <= 0:
        cap.release()
        return []
    indices = np.linspace(0, max(0, total - 1), num=num, dtype=int)
    frames: list[np.ndarray] = []
    for idx in indices:
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(idx))
        ok, frame = cap.read()
        if ok:
            frames.append(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    cap.release()
    return frames


def detect_video(data: bytes) -> DetectionResult:
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
        tmp.write(data)
        tmp_path = tmp.name

    try:
        frames = _sample_frames(tmp_path)
    finally:
        try:
            Path(tmp_path).unlink(missing_ok=True)
        except OSError:
            pass

    if not frames:
        return make_result(0.5, "No frames could be extracted from the video.")

    scores: list[float] = []
    for frame in frames:
        pil = Image.fromarray(frame)
        import io as _io

        buf = _io.BytesIO()
        pil.save(buf, format="JPEG", quality=85)
        result = detect_image(buf.getvalue())
        scores.append(float(result["score"]))

    arr = np.asarray(scores, dtype=np.float32)
    mean_score = float(arr.mean())
    max_score = float(arr.max())
    # Aggregate: 70% mean + 30% peak — the peak helps catch isolated
    # heavily-manipulated frames.
    final = 0.7 * mean_score + 0.3 * max_score

    explanation = (
        f"Sampled {len(frames)} frames from the video. "
        f"Per-frame deepfake score: mean={mean_score:.3f}, "
        f"max={max_score:.3f}, std={arr.std():.3f}. "
        f"Aggregated score = 0.7·mean + 0.3·max = {final:.3f}."
    )
    return make_result(final, explanation, positive="AI Generated", negative="Real")
