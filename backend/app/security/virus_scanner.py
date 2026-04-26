"""ClamAV virus scanner client.

Connects to a ClamAV daemon over TCP (clamd) and scans files **before** they
are passed to any AI processing. If the daemon is unreachable, the scanner is
configured to FAIL CLOSED — i.e. the file will be rejected. This is the safe
default for a security-critical pipeline.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO

import clamd

from app.core.config import settings
from app.core.logging import get_logger

log = get_logger(__name__)


class VirusScanError(Exception):
    """Raised when the virus scanner cannot complete a scan."""


@dataclass
class ScanResult:
    is_clean: bool
    is_infected: bool
    signature: str | None
    raw: dict | None

    @property
    def safe(self) -> bool:
        return self.is_clean and not self.is_infected


class VirusScanner:
    """Thin wrapper around a clamd network connection."""

    def __init__(
        self,
        host: str | None = None,
        port: int | None = None,
        timeout: int | None = None,
    ) -> None:
        self.host = host or settings.clamav_host
        self.port = port or settings.clamav_port
        self.timeout = timeout or settings.clamav_timeout
        self._client: clamd.ClamdNetworkSocket | None = None

    def _connect(self) -> clamd.ClamdNetworkSocket:
        if self._client is None:
            self._client = clamd.ClamdNetworkSocket(
                host=self.host, port=self.port, timeout=self.timeout
            )
        return self._client

    def ping(self) -> bool:
        try:
            client = self._connect()
            return client.ping() == "PONG"
        except Exception as exc:
            log.warning("clamav.ping_failed", error=str(exc))
            return False

    def version(self) -> str | None:
        try:
            return self._connect().version()
        except Exception as exc:
            log.warning("clamav.version_failed", error=str(exc))
            return None

    def scan_file(self, file_path: str | Path) -> ScanResult:
        """Scan a file on disk. The path must be readable by clamd.

        For a containerized setup we instead recommend ``scan_stream``, which
        does not require a shared volume between the API container and the
        ClamAV container.
        """
        path = str(file_path)
        try:
            client = self._connect()
            raw = client.scan(path)
        except Exception as exc:
            log.error("clamav.scan_file_error", path=path, error=str(exc))
            raise VirusScanError(f"ClamAV scan failed: {exc}") from exc

        return self._parse(raw, path)

    def scan_stream(self, stream: BinaryIO) -> ScanResult:
        """Stream the file contents to clamd and scan in-memory.

        This is the preferred method in containerized deployments.
        """
        try:
            client = self._connect()
            raw = client.instream(stream)
        except Exception as exc:
            log.error("clamav.scan_stream_error", error=str(exc))
            raise VirusScanError(f"ClamAV stream scan failed: {exc}") from exc

        return self._parse(raw, "<stream>")

    @staticmethod
    def _parse(raw: dict | None, label: str) -> ScanResult:
        if not raw:
            raise VirusScanError("Empty response from ClamAV")

        # clamd returns a dict like {'<path>': ('OK', None)} or
        # {'<path>': ('FOUND', 'Eicar-Test-Signature')}
        first = next(iter(raw.values()))
        status, signature = first[0], first[1]

        if status == "OK":
            return ScanResult(
                is_clean=True, is_infected=False, signature=None, raw=raw
            )
        if status == "FOUND":
            log.warning("clamav.virus_found", target=label, signature=signature)
            return ScanResult(
                is_clean=False, is_infected=True, signature=signature, raw=raw
            )

        # ERROR or unknown -> fail closed
        raise VirusScanError(f"ClamAV returned status={status} signature={signature}")


_default_scanner: VirusScanner | None = None


def get_virus_scanner() -> VirusScanner:
    global _default_scanner
    if _default_scanner is None:
        _default_scanner = VirusScanner()
    return _default_scanner
