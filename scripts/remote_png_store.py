"""Private, bounded Google Cloud Storage backing for remote PNG delivery."""

from __future__ import annotations

import hashlib
import os
import re
import secrets
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from typing import Mapping
from urllib.parse import urlsplit


DEFAULT_TTL_SECONDS = 24 * 60 * 60
MIN_TTL_SECONDS = 60
MAX_TTL_SECONDS = 24 * 60 * 60
MAX_STORED_PNG_BYTES = 8 * 1024 * 1024
DEFAULT_UPLOADS_PER_HOUR = 60
MAX_UPLOADS_PER_HOUR = 600
DEFAULT_UPLOAD_BURST = 5
MAX_UPLOAD_BURST = 10
DEFAULT_CONCURRENT_UPLOADS = 2
MAX_CONCURRENT_UPLOADS = 8
TOKEN_BYTES = 24  # 192 random bits; comfortably above the 128-bit minimum.
TOKEN_PATTERN = re.compile(r"^[A-Za-z0-9_-]{32}$")
_BUCKET_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{1,220}[a-z0-9]$")


class RemotePngNotFound(LookupError):
    """Uniform internal signal for missing, invalid, expired, or corrupt exports."""


class RemotePngRateLimited(RuntimeError):
    """The bounded per-process upload budget is temporarily exhausted."""

    def __init__(self, retry_after_seconds: int):
        super().__init__("Remote PNG upload rate limit reached.")
        self.retry_after_seconds = max(1, retry_after_seconds)


class RemotePngBusy(RuntimeError):
    """All bounded per-process GCS upload slots are in use."""


@dataclass(frozen=True)
class RemotePngConfig:
    bucket: str
    public_origin: str
    ttl_seconds: int = DEFAULT_TTL_SECONDS
    uploads_per_hour: int = DEFAULT_UPLOADS_PER_HOUR
    upload_burst: int = DEFAULT_UPLOAD_BURST
    concurrent_uploads: int = DEFAULT_CONCURRENT_UPLOADS

    @classmethod
    def from_environment(
        cls, environ: Mapping[str, str] | None = None
    ) -> "RemotePngConfig | None":
        """Return a usable configuration, or disable delivery for incomplete input."""
        values = os.environ if environ is None else environ
        bucket = values.get("QCB_PNG_BUCKET", "").strip()
        origin = values.get("QCB_PUBLIC_ORIGIN", "").strip()
        if not bucket or not origin or not _BUCKET_PATTERN.fullmatch(bucket):
            return None

        parsed = urlsplit(origin)
        if (
            parsed.scheme != "https"
            or not parsed.hostname
            or parsed.username is not None
            or parsed.password is not None
            or parsed.query
            or parsed.fragment
            or parsed.path not in ("", "/")
        ):
            return None
        try:
            port = parsed.port
        except ValueError:
            return None
        if port not in (None, 443):
            return None

        ttl_text = values.get("QCB_PNG_TTL_SECONDS", str(DEFAULT_TTL_SECONDS)).strip()
        rate_text = values.get(
            "QCB_PNG_UPLOADS_PER_HOUR", str(DEFAULT_UPLOADS_PER_HOUR)
        ).strip()
        burst_text = values.get("QCB_PNG_UPLOAD_BURST", str(DEFAULT_UPLOAD_BURST)).strip()
        concurrent_text = values.get(
            "QCB_PNG_MAX_CONCURRENT_UPLOADS", str(DEFAULT_CONCURRENT_UPLOADS)
        ).strip()
        try:
            ttl_seconds = int(ttl_text)
            uploads_per_hour = int(rate_text)
            upload_burst = int(burst_text)
            concurrent_uploads = int(concurrent_text)
        except ValueError:
            return None
        if (
            not MIN_TTL_SECONDS <= ttl_seconds <= MAX_TTL_SECONDS
            or not 1 <= uploads_per_hour <= MAX_UPLOADS_PER_HOUR
            or not 1 <= upload_burst <= min(MAX_UPLOAD_BURST, uploads_per_hour)
            or not 1 <= concurrent_uploads <= MAX_CONCURRENT_UPLOADS
        ):
            return None

        normalized_origin = f"https://{parsed.hostname.lower()}"
        return cls(
            bucket=bucket,
            public_origin=normalized_origin,
            ttl_seconds=ttl_seconds,
            uploads_per_hour=uploads_per_hour,
            upload_burst=upload_burst,
            concurrent_uploads=concurrent_uploads,
        )


@dataclass(frozen=True)
class PublishedPng:
    url: str
    filename: str
    sha256: str
    expires_at: str


@dataclass(frozen=True)
class StoredPng:
    data: bytes
    filename: str
    sha256: str
    expires_at: str


def _timestamp(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _parse_timestamp(value: object) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise RemotePngNotFound
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise RemotePngNotFound from exc
    if parsed.tzinfo is None:
        raise RemotePngNotFound
    return parsed.astimezone(timezone.utc)


def _is_gcs_not_found(exc: Exception) -> bool:
    """Avoid importing the Google client on local-only startup paths."""
    try:
        from google.api_core.exceptions import NotFound
    except ImportError:  # pragma: no cover - production dependency is pinned
        return False
    return isinstance(exc, NotFound)


class UploadLimiter:
    """Thread-safe token bucket plus a non-blocking concurrency gate."""

    def __init__(
        self,
        *,
        uploads_per_hour: int,
        burst: int,
        concurrent_uploads: int,
        clock=time.monotonic,
    ):
        self._rate_per_second = uploads_per_hour / 3600.0
        self._capacity = float(burst)
        self._tokens = float(burst)
        self._clock = clock
        self._last_refill = clock()
        self._lock = threading.Lock()
        self._slots = threading.BoundedSemaphore(concurrent_uploads)

    def acquire(self) -> None:
        if not self._slots.acquire(blocking=False):
            raise RemotePngBusy("Remote PNG upload capacity is busy.")
        try:
            with self._lock:
                now = self._clock()
                elapsed = max(0.0, now - self._last_refill)
                self._tokens = min(
                    self._capacity,
                    self._tokens + elapsed * self._rate_per_second,
                )
                self._last_refill = now
                if self._tokens < 1.0:
                    wait = int((1.0 - self._tokens) / self._rate_per_second) + 1
                    raise RemotePngRateLimited(wait)
                self._tokens -= 1.0
        except Exception:
            self._slots.release()
            raise

    def release(self) -> None:
        self._slots.release()


class GcsPngStore:
    """Store private PNG objects and mediate every capability-URL read."""

    def __init__(
        self,
        config: RemotePngConfig,
        client: object | None = None,
        limiter: UploadLimiter | None = None,
    ):
        self.config = config
        if client is None:
            from google.cloud import storage

            client = storage.Client()
        self._bucket = client.bucket(config.bucket)
        self._limiter = limiter or UploadLimiter(
            uploads_per_hour=config.uploads_per_hour,
            burst=config.upload_burst,
            concurrent_uploads=config.concurrent_uploads,
        )

    @staticmethod
    def _object_name(token: str) -> str:
        if not TOKEN_PATTERN.fullmatch(token):
            raise RemotePngNotFound
        return f"exports/{token}.png"

    def publish(self, data: bytes, *, now: datetime | None = None) -> PublishedPng:
        if len(data) > MAX_STORED_PNG_BYTES:
            raise ValueError("PNG exceeds the 8 MiB remote delivery limit.")
        created = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
        expires = created + timedelta(seconds=self.config.ttl_seconds)
        digest = hashlib.sha256(data).hexdigest()
        filename = f"quote-card-{digest[:16]}.png"

        # A collision is already cryptographically implausible; the generation
        # precondition also guarantees that one can never replace an object.
        self._limiter.acquire()
        try:
            token = secrets.token_urlsafe(TOKEN_BYTES)
            blob = self._bucket.blob(self._object_name(token))
            blob.cache_control = "private, no-store, max-age=0"
            blob.content_disposition = f'inline; filename="{filename}"'
            blob.metadata = {
                "qcb-created-at": _timestamp(created),
                "qcb-expires-at": _timestamp(expires),
                "qcb-sha256": digest,
                "qcb-filename": filename,
            }
            blob.upload_from_string(data, content_type="image/png", if_generation_match=0)
        finally:
            self._limiter.release()
        return PublishedPng(
            url=f"{self.config.public_origin}/exports/{token}.png",
            filename=filename,
            sha256=digest,
            expires_at=_timestamp(expires),
        )

    def fetch(
        self, token: str, *, now: datetime | None = None
    ) -> StoredPng:
        checked_at = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
        try:
            blob = self._bucket.blob(self._object_name(token))
            blob.reload()
            metadata = blob.metadata if isinstance(blob.metadata, dict) else {}
            created = _parse_timestamp(metadata.get("qcb-created-at"))
            expires = _parse_timestamp(metadata.get("qcb-expires-at"))
            digest = metadata.get("qcb-sha256")
            filename = metadata.get("qcb-filename")
            if (
                checked_at < created - timedelta(minutes=5)
                or expires <= checked_at
                or expires <= created
                or expires - created > timedelta(seconds=MAX_TTL_SECONDS)
                or not isinstance(digest, str)
                or not re.fullmatch(r"[0-9a-f]{64}", digest)
                or filename != f"quote-card-{digest[:16]}.png"
                or blob.content_type != "image/png"
                or not isinstance(blob.size, int)
                or not 1 <= blob.size <= MAX_STORED_PNG_BYTES
            ):
                raise RemotePngNotFound
            data = blob.download_as_bytes(if_generation_match=blob.generation)
        except RemotePngNotFound:
            raise
        except Exception as exc:
            if _is_gcs_not_found(exc):
                raise RemotePngNotFound from exc
            raise

        # Check again after the network read and reject altered object bytes.
        post_read_at = datetime.now(timezone.utc) if now is None else checked_at
        if post_read_at >= expires or hashlib.sha256(data).hexdigest() != digest:
            raise RemotePngNotFound
        return StoredPng(data=data, filename=filename, sha256=digest, expires_at=_timestamp(expires))


@lru_cache(maxsize=4)
def _store_for_config(config: RemotePngConfig) -> GcsPngStore:
    return GcsPngStore(config)


def configured_public_origin(environ: Mapping[str, str] | None = None) -> str | None:
    config = RemotePngConfig.from_environment(environ)
    return config.public_origin if config else None


def remote_delivery_configured(environ: Mapping[str, str] | None = None) -> bool:
    return RemotePngConfig.from_environment(environ) is not None


def get_remote_png_store(environ: Mapping[str, str] | None = None) -> GcsPngStore | None:
    config = RemotePngConfig.from_environment(environ)
    return _store_for_config(config) if config else None
