"""Exact-byte PNG delivery, transport isolation and fixed destination checks."""
import asyncio
import base64
import importlib.util
import struct
import sys
import tempfile
import unittest
import zlib
from pathlib import Path
from unittest import mock
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
if importlib.util.find_spec("mcp") and importlib.util.find_spec("openai_mcp_extensions"):
    import mcp_server
else:
    mcp_server = None


def png_bytes(width=1440, height=1440):
    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xffffffff)
    header = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    pixels = (b"\x00" + b"\x12\x34\x56\xff" * width) * height
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) + chunk(b"IDAT", zlib.compress(pixels)) + chunk(b"IEND", b"")


@unittest.skipIf(mcp_server is None, "MCP dependencies are required for local delivery tests")
class LocalDeliveryTests(unittest.TestCase):
    def test_local_tool_saves_exact_bytes_idempotently_and_is_app_private(self):
        from mcp import Client
        from mcp.client import advertise
        payload = png_bytes()
        async def exercise():
            async with Client(mcp_server.mcp, extensions=[advertise("io.modelcontextprotocol/ui", {"mimeTypes":["text/html;profile=mcp-app"]})]) as client:
                tool = next(t for t in (await client.list_tools()).tools if t.name == "quote_card_builder_save_png")
                self.assertEqual(["app"], tool.meta["ui"]["visibility"])
                self.assertFalse(tool.annotations.read_only_hint)
                first = await client.call_tool(tool.name, {"png_base64":base64.b64encode(payload).decode()})
                second = await client.call_tool(tool.name, {"png_base64":base64.b64encode(payload).decode()})
                self.assertFalse(first.is_error)
                self.assertEqual(first.structured_content, second.structured_content)
                path = Path(first.structured_content["path"])
                self.assertEqual(home / "Downloads" / "Quote Card Builder", path.parent)
                self.assertEqual(payload, path.read_bytes())
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            with mock.patch.object(mcp_server, "LOCAL_FILE_DELIVERY", True), mock.patch.object(Path, "home", return_value=home):
                asyncio.run(exercise())

    def test_remote_server_rejects_saving_without_touching_filesystem(self):
        with mock.patch.object(mcp_server, "LOCAL_FILE_DELIVERY", False), mock.patch.object(Path, "home", side_effect=AssertionError("filesystem touched")):
            with self.assertRaisesRegex(ValueError, "disabled"):
                mcp_server.quote_card_builder_save_png(base64.b64encode(png_bytes()).decode())

    def test_rejects_corrupt_truncated_or_wrong_sized_pngs(self):
        payload = png_bytes()
        for data in (b"not PNG", payload[:-1], payload + b"extra", payload[:50] + b"x" + payload[51:], png_bytes(100,100)):
            with self.subTest(size=len(data)), self.assertRaises(ValueError):
                mcp_server._validated_png(base64.b64encode(data).decode())
        with self.assertRaises(ValueError):
            mcp_server._validated_png("not base64!")

    def test_both_card_formats_are_accepted(self):
        for size in ((1440,1440),(1440,1800)):
            payload = png_bytes(*size)
            self.assertEqual(payload, mcp_server._validated_png(base64.b64encode(payload).decode()))

    def test_existing_conflicting_file_is_never_overwritten(self):
        payload = png_bytes()
        blob = base64.b64encode(payload).decode()
        with tempfile.TemporaryDirectory() as directory, mock.patch.object(mcp_server, "LOCAL_FILE_DELIVERY", True), mock.patch.object(Path, "home", return_value=Path(directory)):
            result = mcp_server.quote_card_builder_save_png(blob)
            path = Path(result.path)
            path.write_bytes(b"user file")
            with self.assertRaisesRegex(ValueError, "different file"):
                mcp_server.quote_card_builder_save_png(blob)
            self.assertEqual(b"user file", path.read_bytes())

    def test_http_cannot_enable_local_delivery(self):
        with mock.patch.object(sys, "argv", ["server", "--transport", "streamable-http", "--local-file-delivery"]), mock.patch.object(mcp_server.mcp, "run") as run:
            with self.assertRaises(SystemExit):
                mcp_server.main()
            run.assert_not_called()

    def test_simultaneous_download_and_chat_save_share_one_complete_file(self):
        payload = png_bytes()
        blob = base64.b64encode(payload).decode()
        with tempfile.TemporaryDirectory() as directory, mock.patch.object(mcp_server, "LOCAL_FILE_DELIVERY", True), mock.patch.object(Path, "home", return_value=Path(directory)):
            with ThreadPoolExecutor(max_workers=2) as pool:
                results = list(pool.map(mcp_server.quote_card_builder_save_png, [blob,blob]))
            self.assertEqual(results[0], results[1])
            path = Path(results[0].path)
            self.assertEqual(payload, path.read_bytes())
            self.assertEqual([path], list(path.parent.iterdir()))


if __name__ == "__main__":
    unittest.main()
