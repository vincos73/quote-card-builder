from __future__ import annotations

import asyncio
import importlib.util
import sys
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


class McpExtensionsProtocolTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if importlib.util.find_spec("mcp") is None:
            raise unittest.SkipTest("SDK MCP non installato: test Extensions saltato")
        if importlib.util.find_spec("openai_mcp_extensions") is None:
            raise unittest.SkipTest("SDK OpenAI MCP Extensions non installato: test Extensions saltato")

    @staticmethod
    async def _inspect_and_open_workspace():
        from mcp import Client
        from mcp.client import advertise

        import mcp_app
        import mcp_server

        with mock.patch.object(
            mcp_server,
            "_render_request",
            side_effect=AssertionError("workspace entrypoint must not invoke the renderer"),
        ):
            async with Client(
                mcp_server.mcp,
                extensions=[
                    advertise(
                        "io.modelcontextprotocol/ui",
                        {"mimeTypes": ["text/html;profile=mcp-app"]},
                    )
                ],
            ) as client:
                tools = (await client.list_tools()).tools
                resources = (await client.list_resources()).resources
                workspace_contents = await client.read_resource(
                    mcp_app.QUOTE_CARD_WORKSPACE_RESOURCE
                )
                preview_contents = await client.read_resource(
                    mcp_app.QUOTE_CARD_PREVIEW_RESOURCE
                )
                workspace_result = await client.call_tool(
                    "quote_card_builder_open_workspace",
                    arguments={},
                )
        return tools, resources, workspace_contents, preview_contents, workspace_result

    def test_global_entrypoint_accepts_empty_input_without_rendering(self):
        import mcp_app

        tools, resources, workspace_contents, preview_contents, result = asyncio.run(
            self._inspect_and_open_workspace()
        )
        tools_by_name = {tool.name: tool for tool in tools}
        workspace_tool = tools_by_name["quote_card_builder_open_workspace"]

        self.assertEqual("object", workspace_tool.input_schema["type"])
        self.assertEqual({}, workspace_tool.input_schema.get("properties", {}))
        self.assertFalse(workspace_tool.input_schema.get("required"))
        self.assertEqual(
            mcp_app.QUOTE_CARD_WORKSPACE_RESOURCE,
            workspace_tool.meta["ui"]["resourceUri"],
        )
        self.assertEqual(["app", "model"], workspace_tool.meta["ui"]["visibility"])
        self.assertEqual(
            [{"type": "global"}, {"type": "thread"}],
            workspace_tool.meta["openai/ui"]["entrypoints"],
        )
        self.assertTrue(workspace_tool.annotations.read_only_hint)
        self.assertFalse(workspace_tool.annotations.destructive_hint)

        self.assertFalse(result.is_error)
        self.assertEqual(
            {
                "mode": "workspace",
                "workspace_state": "empty",
                "rendered": False,
                "editor_state": None,
            },
            result.structured_content,
        )
        self.assertNotIn("svg", result.structured_content)
        self.assertNotIn("quoteCard", result.meta or {})
        self.assertFalse(any(item.type in {"image", "resource"} for item in result.content))

        resource_uris = {str(resource.uri) for resource in resources}
        self.assertIn(mcp_app.QUOTE_CARD_WORKSPACE_RESOURCE, resource_uris)
        self.assertIn(mcp_app.QUOTE_CARD_PREVIEW_RESOURCE, resource_uris)

        workspace_content = workspace_contents.contents[0]
        preview_content = preview_contents.contents[0]
        self.assertEqual(
            {
                "availableDisplayModes": ["fullscreen"],
                "preferredDisplayMode": "fullscreen",
            },
            workspace_content.meta["openai/ui"],
        )
        self.assertFalse(workspace_content.meta["ui"]["prefersBorder"])
        self.assertEqual(
            {
                "availableDisplayModes": ["fullscreen"],
                "preferredDisplayMode": "fullscreen",
            },
            preview_content.meta["openai/ui"],
        )
        self.assertTrue(preview_content.meta["ui"]["prefersBorder"])
        expected_widget_csp = {
            "connect_domains": [],
            "resource_domains": [],
            "redirect_domains": list(mcp_app.QUOTE_CARD_DOWNLOAD_REDIRECT_DOMAINS),
        }
        self.assertEqual(expected_widget_csp, workspace_content.meta["openai/widgetCSP"])
        self.assertEqual(expected_widget_csp, preview_content.meta["openai/widgetCSP"])

    def test_conversational_editor_contract_remains_compatible(self):
        from mcp import Client
        from mcp.client import advertise

        import mcp_app
        import mcp_server

        async def exercise():
            async with Client(
                mcp_server.mcp,
                extensions=[
                    advertise(
                        "io.modelcontextprotocol/ui",
                        {"mimeTypes": ["text/html;profile=mcp-app"]},
                    )
                ],
            ) as client:
                tools = {tool.name: tool for tool in (await client.list_tools()).tools}
                result = await client.call_tool(
                    "quote_card_builder_open_editor",
                    arguments={
                        "text": "La compatibilità resta visibile.",
                        "attribution": "",
                        "profile_mode": "neutral",
                    },
                )
            return tools, result

        tools, result = asyncio.run(exercise())
        editor_tool = tools["quote_card_builder_open_editor"]
        self.assertEqual(
            {"text"},
            set(editor_tool.input_schema["required"]),
        )
        self.assertEqual("", editor_tool.input_schema["properties"]["attribution"]["default"])
        self.assertEqual("neutral", editor_tool.input_schema["properties"]["profile_mode"]["default"])
        self.assertEqual(
            mcp_app.QUOTE_CARD_PREVIEW_RESOURCE,
            editor_tool.meta["ui"]["resourceUri"],
        )
        self.assertEqual(["model"], editor_tool.meta["ui"]["visibility"])
        self.assertNotIn("openai/ui", editor_tool.meta)
        self.assertFalse(result.is_error)
        self.assertTrue(result.structured_content["rendered"])
        self.assertEqual(
            "La compatibilità resta visibile.",
            result.structured_content["editor_state"]["text"],
        )


if __name__ == "__main__":
    unittest.main()
