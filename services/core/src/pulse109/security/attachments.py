"""Security validation, MIME inspection, and malware scanning for appeal attachments."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol

DEFAULT_ALLOWED_MIMES = frozenset(
    {
        "application/pdf",
        "image/jpeg",
        "image/png",
        "image/webp",
        "text/plain",
    }
)

MAX_ATTACHMENT_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB

# Dangerous signatures that should never be permitted
_EXECUTABLE_SIGNATURES = (
    b"MZ",  # Windows PE
    b"\x7fELF",  # Linux ELF
    b"\xca\xfe\xba\xbe",  # Java Class
    b"#!",  # Shell script shebang
)

_SCRIPT_PATTERN = re.compile(
    rb"(?i)(<script[\s>]|javascript:|onload\s*=|onerror\s*=|document\.cookie)"
)


@dataclass(frozen=True, slots=True)
class AttachmentValidationResult:
    is_valid: bool
    detected_mime: str | None
    error_code: str | None
    error_message: str | None
    sha256: str
    byte_size: int


@dataclass(frozen=True, slots=True)
class MalwareScanResult:
    is_clean: bool
    threat_name: str | None
    scanner_id: str
    scan_sha256: str
    scanned_at: datetime


class MalwareScanner(Protocol):
    def scan(self, content: bytes, object_hash: str) -> MalwareScanResult: ...


class MockMalwareScanner:
    """Deterministic in-memory scanner for testing and offline environments."""

    def __init__(self, *, known_bad_hashes: set[str] | None = None) -> None:
        self.known_bad_hashes = known_bad_hashes or set()

    def scan(self, content: bytes, object_hash: str) -> MalwareScanResult:
        now = datetime.now(timezone.utc)
        if object_hash in self.known_bad_hashes:
            return MalwareScanResult(
                is_clean=False,
                threat_name="EICAR_OR_KNOWN_MALICIOUS_HASH",
                scanner_id="mock-scanner-v1",
                scan_sha256=object_hash,
                scanned_at=now,
            )
        return MalwareScanResult(
            is_clean=True,
            threat_name=None,
            scanner_id="mock-scanner-v1",
            scan_sha256=object_hash,
            scanned_at=now,
        )


def inspect_mime_type(content: bytes) -> str | None:
    """Inspect magic bytes to determine true MIME type."""
    if len(content) < 4:
        return None
    if content.startswith(b"%PDF-"):
        return "application/pdf"
    if content.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if content.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if len(content) >= 12 and content[:4] == b"RIFF" and content[8:12] == b"WEBP":
        return "image/webp"
    # Plain text check: decode as UTF-8 without null bytes
    try:
        sample = content[:4096].decode("utf-8")
        if "\x00" not in sample:
            return "text/plain"
    except UnicodeDecodeError:
        pass
    return None


def validate_attachment(
    content: bytes,
    declared_mime: str,
    *,
    allowed_mimes: frozenset[str] = DEFAULT_ALLOWED_MIMES,
    max_size_bytes: int = MAX_ATTACHMENT_SIZE_BYTES,
) -> AttachmentValidationResult:
    digest = hashlib.sha256(content).hexdigest()
    size = len(content)

    if size == 0:
        return AttachmentValidationResult(
            is_valid=False,
            detected_mime=None,
            error_code="attachment_empty",
            error_message="Attachment payload is empty.",
            sha256=digest,
            byte_size=0,
        )

    if size > max_size_bytes:
        return AttachmentValidationResult(
            is_valid=False,
            detected_mime=None,
            error_code="attachment_too_large",
            error_message=f"Attachment size {size} exceeds limit of {max_size_bytes} bytes.",
            sha256=digest,
            byte_size=size,
        )

    # Check for executable magic bytes
    for sig in _EXECUTABLE_SIGNATURES:
        if content.startswith(sig):
            return AttachmentValidationResult(
                is_valid=False,
                detected_mime="application/x-executable",
                error_code="executable_attachment_forbidden",
                error_message="Executable attachments are strictly forbidden.",
                sha256=digest,
                byte_size=size,
            )

    # Check for embedded script injections in text or SVG
    if _SCRIPT_PATTERN.search(content[:8192]):
        return AttachmentValidationResult(
            is_valid=False,
            detected_mime="text/html",
            error_code="script_injection_detected",
            error_message="Embedded scripts or active content detected.",
            sha256=digest,
            byte_size=size,
        )

    detected_mime = inspect_mime_type(content)
    if detected_mime is None:
        return AttachmentValidationResult(
            is_valid=False,
            detected_mime=None,
            error_code="unknown_mime_signature",
            error_message="Attachment does not match any recognized magic byte signature.",
            sha256=digest,
            byte_size=size,
        )

    if detected_mime not in allowed_mimes:
        return AttachmentValidationResult(
            is_valid=False,
            detected_mime=detected_mime,
            error_code="mime_not_allowed",
            error_message=f"MIME type '{detected_mime}' is not on the approved allowlist.",
            sha256=digest,
            byte_size=size,
        )

    if declared_mime != detected_mime:
        return AttachmentValidationResult(
            is_valid=False,
            detected_mime=detected_mime,
            error_code="mime_mismatch",
            error_message=(
                f"Declared MIME '{declared_mime}' does not match "
                f"detected magic signature '{detected_mime}'."
            ),
            sha256=digest,
            byte_size=size,
        )

    return AttachmentValidationResult(
        is_valid=True,
        detected_mime=detected_mime,
        error_code=None,
        error_message=None,
        sha256=digest,
        byte_size=size,
    )
