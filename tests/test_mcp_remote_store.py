"""Bounded private-GCS PNG publication and anonymous capability delivery."""

from __future__ import annotations

import asyncio
import base64
import hashlib
import importlib.util
import os
import socket
import struct
import subprocess
import sys
import threading
import time
import unittest
import zlib
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.request import urlopen
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import remote_png_store

if importlib.util.find_spec("mcp") and importlib.util.find_spec("openai_mcp_extensions"):
    import mcp_server
else:
    mcp_server = None


def png_bytes(width: int = 1440, height: int = 1440) -> bytes:
    def chunk(kind: bytes, data: bytes) -> bytes:
        checksum = zlib.crc32(kind + data) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", checksum)

    header = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    pixels = (b"\x00" + b"\x12\x34\x56\xff" * width) * height
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", header)
        + chunk(b"IDAT", zlib.compress(pixels))
        + chunk(b"IEND", b"")
    )


class FakeBlob:
    def __init__(self, name: str, objects: dict[str, dict[str, object]], lock: threading.Lock):
        self.name = name
        self._objects = objects
        self._lock = lock
        self.metadata = None
        self.cache_control = None
        self.content_disposition = None
        self.content_type = None
        self.generation = None
        self.size = None

    def upload_from_string(self, data: bytes, *, content_type: str, if_generation_match: int):
        if if_generation_match != 0:
            raise AssertionError("uploads must be create-only")
        with self._lock:
            if self.name in self._objects:
                raise AssertionError("object replaced")
            self._objects[self.name] = {
                "data": data,
                "metadata": dict(self.metadata),
                "cache_control": self.cache_control,
                "content_disposition": self.content_disposition,
                "content_type": content_type,
                "generation": len(self._objects) + 1,
            }

    def reload(self):
        with self._lock:
            item = self._objects.get(self.name)
            if item is None:
                raise remote_png_store.RemotePngNotFound
            self.metadata = dict(item["metadata"])
            self.cache_control = item["cache_control"]
            self.content_disposition = item["content_disposition"]
            self.content_type = item["content_type"]
            self.generation = item["generation"]
            self.size = len(item["data"])

    def download_as_bytes(self, *, if_generation_match: int) -> bytes:
        with self._lock:
            item = self._objects[self.name]
            if item["generation"] != if_generation_match:
                raise AssertionError("generation was not pinned")
            return item["data"]


class FakeBucket:
    def __init__(self):
        self.objects: dict[str, dict[str, object]] = {}
        self.lock = threading.Lock()

    def blob(self, name: str) -> FakeBlob:
        return FakeBlob(name, self.objects, self.lock)


class FakeClient:
    def __init__(self):
        self.bucket_name = None
        self.value = FakeBucket()

    def bucket(self, name: str) -> FakeBucket:
        self.bucket_name = name
        return self.value


def config(**changes) -> remote_png_store.RemotePngConfig:
    values = {
        "bucket": "qcb-private-exports",
        "public_origin": "https://qcb.example.test",
        "ttl_seconds": 86400,
        "uploads_per_hour": 60,
        "upload_burst": 5,
        "concurrent_uploads": 2,
    }
    values.update(changes)
    return remote_png_store.RemotePngConfig(**values)


class RemotePngStoreTests(unittest.TestCase):
    def test_configuration_is_https_complete_and_bounded(self):
        valid = {
            "QCB_PNG_BUCKET": "qcb-private-exports",
            "QCB_PUBLIC_ORIGIN": "https://QCB.EXAMPLE.TEST/",
            "QCB_PNG_TTL_SECONDS": "3600",
            "QCB_PNG_UPLOADS_PER_HOUR": "12",
            "QCB_PNG_UPLOAD_BURST": "3",
            "QCB_PNG_MAX_CONCURRENT_UPLOADS": "2",
        }
        parsed = remote_png_store.RemotePngConfig.from_environment(valid)
        self.assertEqual("https://qcb.example.test", parsed.public_origin)
        self.assertEqual(3600, parsed.ttl_seconds)
        for key, value in (
            ("QCB_PNG_TTL_SECONDS", "86401"),
            ("QCB_PNG_UPLOADS_PER_HOUR", "601"),
            ("QCB_PNG_UPLOAD_BURST", "11"),
            ("QCB_PNG_MAX_CONCURRENT_UPLOADS", "9"),
            ("QCB_PNG_BUCKET", "QCB-Private-Exports"),
            ("QCB_PUBLIC_ORIGIN", "http://qcb.example.test"),
            ("QCB_PUBLIC_ORIGIN", "https://qcb.example.test/path"),
        ):
            invalid = {**valid, key: value}
            with self.subTest(key=key, value=value):
                self.assertIsNone(remote_png_store.RemotePngConfig.from_environment(invalid))

    def test_publish_and_fetch_preserve_exact_bytes_private_metadata_and_expiry(self):
        client = FakeClient()
        store = remote_png_store.GcsPngStore(config(), client=client)
        now = datetime(2026, 10, 13, 8, 0, tzinfo=timezone.utc)
        payload = png_bytes()
        published = store.publish(payload, now=now)
        token = published.url.removeprefix("https://qcb.example.test/exports/").removesuffix(".png")

        self.assertRegex(token, r"^[A-Za-z0-9_-]{32}$")
        self.assertEqual(hashlib.sha256(payload).hexdigest(), published.sha256)
        self.assertEqual(f"quote-card-{published.sha256[:16]}.png", published.filename)
        self.assertEqual("2026-10-14T08:00:00Z", published.expires_at)
        item = client.value.objects[f"exports/{token}.png"]
        self.assertEqual(payload, item["data"])
        self.assertEqual("image/png", item["content_type"])
        self.assertEqual("private, no-store, max-age=0", item["cache_control"])
        self.assertEqual(payload, store.fetch(token, now=now + timedelta(hours=23)).data)
        with self.assertRaises(remote_png_store.RemotePngNotFound):
            store.fetch(token, now=now + timedelta(hours=24))

    def test_invalid_token_metadata_size_and_bytes_are_uniformly_hidden(self):
        client = FakeClient()
        store = remote_png_store.GcsPngStore(config(), client=client)
        now = datetime(2026, 10, 13, 8, 0, tzinfo=timezone.utc)
        published = store.publish(png_bytes(), now=now)
        token = published.url.split("/")[-1][:-4]
        for invalid in ("short", token + ".png", "!" * 32):
            with self.subTest(token=invalid), self.assertRaises(remote_png_store.RemotePngNotFound):
                store.fetch(invalid, now=now)

        name = f"exports/{token}.png"
        client.value.objects[name]["metadata"]["qcb-expires-at"] = "2026-10-15T08:00:00Z"
        with self.assertRaises(remote_png_store.RemotePngNotFound):
            store.fetch(token, now=now)
        client.value.objects[name]["metadata"]["qcb-expires-at"] = published.expires_at
        client.value.objects[name]["data"] = b"changed"
        with self.assertRaises(remote_png_store.RemotePngNotFound):
            store.fetch(token, now=now)

    def test_concurrent_publications_use_unique_objects(self):
        client = FakeClient()
        cfg = config(uploads_per_hour=100, upload_burst=10, concurrent_uploads=8)
        store = remote_png_store.GcsPngStore(cfg, client=client)
        payload = png_bytes()
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(store.publish, [payload] * 8))
        self.assertEqual(8, len({result.url for result in results}))
        self.assertEqual(8, len(client.value.objects))
        self.assertTrue(all(item["data"] == payload for item in client.value.objects.values()))

    def test_rate_limiter_reports_retry_time(self):
        times = iter([0.0, 0.0, 0.0])
        limiter = remote_png_store.UploadLimiter(
            uploads_per_hour=60,
            burst=1,
            concurrent_uploads=1,
            clock=lambda: next(times),
        )
        limiter.acquire()
        limiter.release()
        with self.assertRaises(remote_png_store.RemotePngRateLimited) as caught:
            limiter.acquire()
        self.assertGreaterEqual(caught.exception.retry_after_seconds, 60)

    def test_limiter_rejects_excess_concurrent_upload_without_waiting(self):
        limiter = remote_png_store.UploadLimiter(
            uploads_per_hour=60,
            burst=2,
            concurrent_uploads=1,
        )
        limiter.acquire()
        try:
            with self.assertRaises(remote_png_store.RemotePngBusy):
                limiter.acquire()
        finally:
            limiter.release()


@unittest.skipIf(mcp_server is None, "MCP dependencies are required for server delivery tests")
class RemotePngServerTests(unittest.TestCase):
    def test_publish_tool_is_app_private_exact_and_never_touches_home(self):
        payload = png_bytes()
        published = remote_png_store.PublishedPng(
            url="https://qcb.example.test/exports/" + "A" * 32 + ".png",
            filename="quote-card-test.png",
            sha256=hashlib.sha256(payload).hexdigest(),
            expires_at="2026-10-14T08:00:00Z",
        )
        store = mock.Mock()
        store.publish.return_value = published
        with mock.patch.object(mcp_server, "get_remote_png_store", return_value=store), mock.patch.object(
            Path, "home", side_effect=AssertionError("home touched")
        ):
            result = mcp_server.quote_card_builder_publish_png(base64.b64encode(payload).decode())
        store.publish.assert_called_once_with(payload)
        self.assertEqual("image/png", result.mime_type)
        self.assertEqual(published.url, result.url)

        async def metadata():
            from mcp import Client
            from mcp.client import advertise

            async with Client(
                mcp_server.mcp,
                extensions=[advertise("io.modelcontextprotocol/ui", {"mimeTypes": ["text/html;profile=mcp-app"]})],
            ) as client:
                return next(
                    tool
                    for tool in (await client.list_tools()).tools
                    if tool.name == "quote_card_builder_publish_png"
                )

        tool = asyncio.run(metadata())
        self.assertEqual(["app"], tool.meta["ui"]["visibility"])
        self.assertFalse(tool.annotations.read_only_hint)
        self.assertFalse(tool.annotations.idempotent_hint)

    def test_disabled_remote_delivery_rejects_before_png_or_filesystem_work(self):
        with mock.patch.object(mcp_server, "get_remote_png_store", return_value=None), mock.patch.object(
            mcp_server, "_validated_png", side_effect=AssertionError("PNG validation ran")
        ), mock.patch.object(Path, "home", side_effect=AssertionError("home touched")):
            with self.assertRaisesRegex(ValueError, "disabled"):
                mcp_server.quote_card_builder_publish_png("anything")

    def test_publish_tool_turns_capacity_failures_into_actionable_errors(self):
        payload = base64.b64encode(png_bytes()).decode()
        for error, message in (
            (remote_png_store.RemotePngRateLimited(45), "about 45 seconds"),
            (remote_png_store.RemotePngBusy("busy"), "busy"),
            (RuntimeError("credential detail"), "failed"),
        ):
            store = mock.Mock()
            store.publish.side_effect = error
            with self.subTest(error=type(error).__name__), mock.patch.object(
                mcp_server, "get_remote_png_store", return_value=store
            ):
                with self.assertRaisesRegex(ValueError, message):
                    mcp_server.quote_card_builder_publish_png(payload)

    def test_produce_reports_both_delivery_modes(self):
        with mock.patch.object(mcp_server, "remote_delivery_configured", return_value=True), mock.patch.object(
            mcp_server, "LOCAL_FILE_DELIVERY", False
        ):
            result = mcp_server.produce_quote_card(text="Remote delivery is explicit.")
        self.assertFalse(result.structured_content["local_file_delivery"])
        self.assertTrue(result.structured_content["remote_file_delivery"])

    @staticmethod
    def _request(method: str, token: str, query: bytes = b""):
        from starlette.requests import Request

        return Request(
            {
                "type": "http",
                "http_version": "1.1",
                "method": method,
                "scheme": "https",
                "path": f"/exports/{token}.png",
                "raw_path": f"/exports/{token}.png".encode(),
                "query_string": query,
                "headers": [],
                "client": ("127.0.0.1", 1),
                "server": ("qcb.example.test", 443),
                "path_params": {"token": token},
            }
        )

    def test_get_head_and_download_headers_serve_exact_bytes(self):
        token = "A" * 32
        payload = png_bytes()
        stored = remote_png_store.StoredPng(
            data=payload,
            filename="quote-card-deadbeef.png",
            sha256=hashlib.sha256(payload).hexdigest(),
            expires_at="2026-10-14T08:00:00Z",
        )
        store = mock.Mock()
        store.fetch.return_value = stored
        with mock.patch.object(mcp_server, "get_remote_png_store", return_value=store), mock.patch.object(
            Path, "home", side_effect=AssertionError("home touched")
        ):
            response = asyncio.run(mcp_server.serve_remote_png(self._request("GET", token)))
            download = asyncio.run(
                mcp_server.serve_remote_png(self._request("GET", token, b"download=1"))
            )
            head = asyncio.run(mcp_server.serve_remote_png(self._request("HEAD", token)))
        self.assertEqual(payload, response.body)
        self.assertEqual("image/png", response.headers["content-type"])
        self.assertEqual(str(len(payload)), response.headers["content-length"])
        self.assertTrue(response.headers["content-disposition"].startswith("inline"))
        self.assertTrue(download.headers["content-disposition"].startswith("attachment"))
        self.assertEqual(b"", head.body)
        self.assertEqual(str(len(payload)), head.headers["content-length"])
        for item in (response, download, head):
            self.assertIn("no-store", item.headers["cache-control"])
            self.assertEqual("nosniff", item.headers["x-content-type-options"])

    def test_invalid_expired_missing_and_disabled_are_the_same_404(self):
        token = "A" * 32
        for store in (
            None,
            mock.Mock(fetch=mock.Mock(side_effect=remote_png_store.RemotePngNotFound)),
        ):
            with self.subTest(store=store), mock.patch.object(
                mcp_server, "get_remote_png_store", return_value=store
            ):
                response = asyncio.run(mcp_server.serve_remote_png(self._request("GET", token)))
                self.assertEqual(404, response.status_code)
                self.assertEqual(b"", response.body)
                self.assertIn("no-store", response.headers["cache-control"])
                self.assertEqual("nosniff", response.headers["x-content-type-options"])

    def test_http_startup_is_stateless_json_and_body_bounded(self):
        with mock.patch.object(
            sys, "argv", ["server", "--transport", "streamable-http"]
        ), mock.patch.object(mcp_server.mcp, "run") as run:
            self.assertEqual(0, mcp_server.main())
        kwargs = run.call_args.kwargs
        self.assertTrue(kwargs["stateless_http"])
        self.assertTrue(kwargs["json_response"])
        self.assertEqual(mcp_server.MCP_HTTP_MAX_REQUEST_BYTES, kwargs["max_request_body_size"])
        self.assertGreater(kwargs["max_request_body_size"], (mcp_server.MAX_PNG_BYTES * 4) // 3)

    def test_real_http_supports_modern_discovery_apps_resources_and_legacy(self):
        from mcp import Client
        from mcp.client import advertise
        import mcp_app

        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            port = listener.getsockname()[1]
        process = subprocess.Popen(
            [
                sys.executable,
                str(SCRIPTS / "mcp_server.py"),
                "--transport",
                "streamable-http",
                "--host",
                "127.0.0.1",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env={
                **os.environ,
                "PORT": str(port),
                "QCB_PNG_BUCKET": "qcb-private-exports",
                "QCB_PUBLIC_ORIGIN": "https://qcb.example.test",
            },
        )
        try:
            deadline = time.monotonic() + 5
            while True:
                try:
                    with urlopen(f"http://127.0.0.1:{port}/health", timeout=0.3):
                        break
                except OSError:
                    if process.poll() is not None:
                        self.fail("stateless HTTP server exited before becoming ready")
                    if time.monotonic() >= deadline:
                        self.fail("stateless HTTP server did not become ready")
                    time.sleep(0.05)

            extensions = [
                advertise(
                    "io.modelcontextprotocol/ui",
                    {"mimeTypes": ["text/html;profile=mcp-app"]},
                )
            ]

            async def exercise():
                url = f"http://127.0.0.1:{port}/mcp"
                async with Client(url, mode="auto", extensions=extensions) as modern:
                    self.assertEqual("2026-07-28", modern.protocol_version)
                    tools = await modern.list_tools()
                    self.assertIn("quote_card_builder_publish_png", [item.name for item in tools.tools])
                    resources = await modern.list_resources()
                    preview_resource = next(
                        item
                        for item in resources.resources
                        if str(item.uri) == mcp_app.QUOTE_CARD_PREVIEW_RESOURCE
                    )
                    self.assertEqual(
                        ["https://qcb.example.test"],
                        preview_resource.meta["ui"]["csp"]["connectDomains"],
                    )
                    self.assertEqual(
                        ["https://qcb.example.test"],
                        preview_resource.meta["ui"]["csp"]["resourceDomains"],
                    )
                    self.assertIn(
                        "https://qcb.example.test",
                        preview_resource.meta["openai/widgetCSP"]["redirect_domains"],
                    )
                    preview_uri = next(
                        str(item.uri)
                        for item in resources.resources
                        if str(item.uri) == mcp_app.QUOTE_CARD_PREVIEW_RESOURCE
                    )
                    contents = await modern.read_resource(preview_uri)
                    self.assertIn("Quote Card Builder", contents.contents[0].text)

                async with Client(url, mode="legacy", extensions=extensions) as legacy:
                    self.assertEqual("2025-11-25", legacy.protocol_version)
                    tools = await legacy.list_tools()
                    self.assertIn("quote_card_builder_publish_png", [item.name for item in tools.tools])

            asyncio.run(exercise())
        finally:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()


if __name__ == "__main__":
    unittest.main()
