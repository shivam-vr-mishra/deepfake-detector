"""URL / social-media content analyzer.

Pipeline:
  1. Fetch the page (timeout, size cap).
  2. Extract canonical metadata (OG tags, title, description, author).
  3. Extract main visible text via BeautifulSoup.
  4. Heuristic scoring on metadata (suspicious TLDs, no author, very recent).
  5. Run the *text* AI-detector on the extracted body.

The fetcher refuses redirects to private/internal IPs to prevent SSRF.
"""
from __future__ import annotations

import ipaddress
import socket
import sys
from pathlib import Path
from urllib.parse import urlparse

import requests
import tldextract
from bs4 import BeautifulSoup

sys.path.append(str(Path(__file__).resolve().parents[1]))
from common import DetectionResult, make_result  # type: ignore  # noqa: E402
from text.detector import detect_text  # type: ignore  # noqa: E402

USER_AGENT = "Mozilla/5.0 (DeepFakeDetector/1.0; +https://deepfake-detector.app)"
MAX_BYTES = 2 * 1024 * 1024  # 2MB cap
TIMEOUT = 10

SUSPICIOUS_TLDS = {"zip", "mov", "click", "xyz", "top", "loan", "country"}


def _is_safe_url(url: str) -> bool:
    """Block SSRF: refuse private / loopback IP targets."""
    try:
        host = urlparse(url).hostname
        if not host:
            return False
        infos = socket.getaddrinfo(host, None)
        for info in infos:
            ip = ipaddress.ip_address(info[4][0])
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
                return False
        return True
    except Exception:
        return False


def _fetch(url: str) -> tuple[int, str]:
    if not _is_safe_url(url):
        raise RuntimeError("Refusing to fetch private/internal URL")
    with requests.get(
        url,
        headers={"User-Agent": USER_AGENT},
        timeout=TIMEOUT,
        stream=True,
        allow_redirects=True,
    ) as r:
        r.raise_for_status()
        chunks = []
        size = 0
        for chunk in r.iter_content(8192):
            chunks.append(chunk)
            size += len(chunk)
            if size > MAX_BYTES:
                break
        body = b"".join(chunks).decode(r.encoding or "utf-8", errors="replace")
        return r.status_code, body


def _extract(html: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")

    def meta(name: str) -> str | None:
        tag = soup.find("meta", attrs={"property": name}) or soup.find(
            "meta", attrs={"name": name}
        )
        return tag.get("content") if tag else None

    title = soup.title.string.strip() if soup.title and soup.title.string else None
    for s in soup(["script", "style", "noscript"]):
        s.extract()
    body_text = " ".join(soup.get_text(separator=" ").split())[:8000]

    return {
        "title": title,
        "og_title": meta("og:title"),
        "og_description": meta("og:description"),
        "og_site_name": meta("og:site_name"),
        "author": meta("author"),
        "description": meta("description"),
        "body_text": body_text,
        "body_length": len(body_text),
    }


def detect_url(url: str) -> DetectionResult:
    try:
        status, html = _fetch(url)
    except Exception as exc:
        return make_result(
            0.5,
            f"Failed to fetch URL ({exc}). Cannot evaluate content.",
        )

    meta = _extract(html)
    body_text = meta["body_text"]

    text_result = (
        detect_text(body_text) if body_text else make_result(0.5, "No text on page.")
    )

    extracted = tldextract.extract(url)
    tld = (extracted.suffix or "").lower()
    metadata_signals = []
    metadata_score = 0.0
    if tld in SUSPICIOUS_TLDS:
        metadata_signals.append(f"suspicious TLD .{tld}")
        metadata_score += 0.25
    if not meta["author"]:
        metadata_signals.append("no author metadata")
        metadata_score += 0.10
    if not meta["og_title"] and not meta["title"]:
        metadata_signals.append("missing title")
        metadata_score += 0.10
    metadata_score = min(metadata_score, 0.6)

    final = 0.75 * float(text_result["score"]) + 0.25 * metadata_score

    explanation = (
        f"Fetched {url} ({status}). "
        f"Extracted {meta['body_length']} chars of body text. "
        f"Text-AI score = {text_result['score']:.3f} "
        f"({text_result['confidence']} confidence). "
        f"Metadata score = {metadata_score:.3f} "
        f"({', '.join(metadata_signals) or 'no flags'}). "
        f"Combined = {final:.3f}."
    )
    return make_result(final, explanation, positive="AI Generated / Suspicious", negative="Likely Human")
