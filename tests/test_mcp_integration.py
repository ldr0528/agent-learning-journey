"""真实 MCP stdio 子进程通信；不连接大模型服务。"""

import importlib.util
from types import SimpleNamespace
import unittest

from agent_learning.integrations.mcp_client import run_mcp_demo, unpack_result


class MCPResultTests(unittest.TestCase):
    def test_protocol_tool_error_is_not_treated_as_evidence(self):
        with self.assertRaises(ValueError):
            unpack_result(SimpleNamespace(isError=True))


@unittest.skipUnless(importlib.util.find_spec("mcp"), "需要可选依赖 .[mcp]")
class MCPIntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def test_initialize_discover_schema_and_call_real_server(self):
        result = await run_mcp_demo()
        self.assertEqual(result["server"], "agent-learning-tools")
        self.assertTrue(result["protocol_version"])
        schemas = {tool["name"]: tool["input_schema"] for tool in result["tools"]}
        self.assertEqual(set(schemas), {"weather", "search_notes"})
        self.assertEqual(schemas["weather"]["properties"]["city"]["type"], "string")
        self.assertIn("city", schemas["weather"]["required"])
        self.assertEqual(result["weather"], {"city": "北京", "weather": "下雨，12℃", "simulated": True})
        self.assertEqual([note["id"] for note in result["search"]["notes"]], ["N02"])

    async def test_missing_data_crosses_protocol_without_invented_values(self):
        result = await run_mcp_demo(city="广州", query="zzzz-unused-query")
        self.assertEqual(result["weather"]["weather"], "暂无天气数据")
        self.assertEqual(result["search"]["notes"], [])


if __name__ == "__main__":
    unittest.main()
