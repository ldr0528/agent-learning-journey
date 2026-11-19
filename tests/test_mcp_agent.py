"""原生工具消息的离线合同测试；假模型不读取配置、不请求 API。"""

from copy import deepcopy
import importlib.util
import json
from types import SimpleNamespace as NS
import unittest

from agent_learning.integrations.mcp_agent import run_mcp_agent, run_model_tool_loop


TOOLS = [NS(name="weather", description="模拟天气", inputSchema={
    "type": "object", "properties": {"city": {"type": "string"}}, "required": ["city"],
})]


def completion(*, text=None, calls=None):
    return NS(choices=[NS(finish_reason="tool_calls" if calls else "stop",
                         message=NS(content=text, tool_calls=calls))])


def tool_call(name="weather", arguments='{"city":"北京"}', call_id="call_1"):
    return NS(id=call_id, function=NS(name=name, arguments=arguments))


class FakeModel:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.inputs = []

    def __call__(self, messages, tools):
        self.inputs.append({"messages": deepcopy(messages), "tools": deepcopy(tools)})
        return next(self.responses)


class MCPAgentLoopTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.executions = []

    async def execute(self, name, arguments):
        self.executions.append((name, arguments))
        return NS(isError=False, structuredContent={"city": arguments["city"],
                  "weather": "下雨，12℃", "simulated": True})

    async def run_loop(self, model, **kwargs):
        return await run_model_tool_loop(question="北京的模拟天气？", tools=TOOLS,
                                         request_model=model, call_tool=self.execute, **kwargs)

    async def test_actual_tool_result_and_original_id_enter_next_model_request(self):
        model = FakeModel([completion(calls=[tool_call()]), completion(text="北京 12℃，模拟数据。")])
        result = await self.run_loop(model)
        self.assertEqual((result["status"], result["model_calls"], result["tool_calls"]),
                         ("finished", 2, 1))
        self.assertEqual(self.executions, [("weather", {"city": "北京"})])
        second = model.inputs[1]["messages"]
        self.assertEqual(second[-2]["tool_calls"][0]["id"], "call_1")
        self.assertEqual(second[-1]["role"], "tool")
        self.assertEqual(second[-1]["tool_call_id"], "call_1")
        self.assertEqual(json.loads(second[-1]["content"])["weather"], "下雨，12℃")
        schema = model.inputs[0]["tools"][0]["function"]
        self.assertEqual(schema["parameters"], TOOLS[0].inputSchema)
        self.assertEqual(schema["description"], "模拟天气")
        self.assertFalse(any(m["role"] == "tool" for m in model.inputs[0]["messages"]))

    async def test_last_request_tool_result_does_not_create_hidden_summary_request(self):
        model = FakeModel([completion(calls=[tool_call()])])
        result = await self.run_loop(model, max_calls=1)
        self.assertEqual(result["status"], "step_limit")
        self.assertIsNone(result["answer"])
        self.assertEqual((len(model.inputs), len(self.executions)), (1, 1))
        self.assertEqual(result["messages"][-1]["role"], "tool")

    async def test_unknown_tool_is_not_dispatched_and_error_reaches_model(self):
        model = FakeModel([completion(calls=[tool_call(name="invented")]),
                           completion(calls=[tool_call(call_id="call_2")]),
                           completion(text="已取得北京模拟天气。")])
        result = await self.run_loop(model)
        self.assertEqual(result["tool_errors"], 1)
        self.assertEqual(len(self.executions), 1)
        self.assertEqual(self.executions[0][0], "weather")
        feedback = json.loads(model.inputs[1]["messages"][-1]["content"])
        self.assertTrue(feedback["isError"])
        self.assertIn("未知工具", feedback["error"])

    async def test_invalid_json_does_not_execute_tool(self):
        model = FakeModel([completion(calls=[tool_call(arguments="not-json")])])
        result = await self.run_loop(model, max_calls=1)
        self.assertEqual(self.executions, [])
        self.assertEqual(result["tool_errors"], 1)

    async def test_tool_execution_budget_limits_multiple_requests_in_one_reply(self):
        model = FakeModel([completion(calls=[tool_call(), tool_call(call_id="call_2")])])
        result = await self.run_loop(model, max_calls=1, max_tool_calls=1)
        self.assertEqual(len(self.executions), 1)
        self.assertEqual(result["tool_calls"], 1)
        tool_messages = [m for m in result["messages"] if m["role"] == "tool"]
        self.assertEqual(len(tool_messages), 2)
        self.assertIn("预算", json.loads(tool_messages[-1]["content"])["error"])

    async def test_direct_answer_without_tool_evidence_is_not_success(self):
        result = await self.run_loop(FakeModel([completion(text="北京应该很暖和。")]))
        self.assertEqual(result["status"], "no_evidence")
        self.assertEqual(result["tool_calls"], 0)

    async def test_protocol_tool_error_is_sent_back_as_error_not_evidence(self):
        model = FakeModel([completion(calls=[tool_call()]), completion(text="没有有效天气数据。")])

        async def fail(name, arguments):
            return NS(isError=True)

        result = await run_model_tool_loop(question="北京？", tools=TOOLS, request_model=model,
                                          call_tool=fail)
        self.assertEqual(result["status"], "no_evidence")
        self.assertTrue(json.loads(model.inputs[1]["messages"][-1]["content"])["isError"])

    async def test_tool_exception_is_bounded_and_does_not_expose_exception_body(self):
        model = FakeModel([completion(calls=[tool_call()]), completion(text="工具不可用。")])

        async def fail(name, arguments):
            raise TimeoutError("private-response-sentinel")

        result = await run_model_tool_loop(question="北京？", tools=TOOLS, request_model=model,
                                          call_tool=fail, max_calls=2)
        feedback = model.inputs[1]["messages"][-1]["content"]
        self.assertIn("TimeoutError", feedback)
        self.assertNotIn("private-response-sentinel", feedback)
        self.assertEqual((result["model_calls"], result["tool_calls"], result["tool_errors"]), (2, 1, 1))
        self.assertEqual(result["status"], "no_evidence")

    async def test_duplicate_call_ids_are_rejected_before_tool_execution(self):
        model = FakeModel([completion(calls=[tool_call(), tool_call()])])
        with self.assertRaises(ValueError):
            await self.run_loop(model)
        self.assertEqual(self.executions, [])

    async def test_model_request_failure_is_not_automatically_retried(self):
        attempts = []

        def fail(messages, tools):
            attempts.append(1)
            raise ConnectionError("fake-offline-failure")

        with self.assertRaises(ConnectionError):
            await self.run_loop(fail)
        self.assertEqual(attempts, [1])
        self.assertEqual(self.executions, [])


@unittest.skipUnless(importlib.util.find_spec("mcp"), "需要可选依赖 .[mcp]")
class MCPModelBridgeIntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def test_fake_model_receives_result_from_real_stdio_server(self):
        model = FakeModel([completion(calls=[tool_call()]), completion(text="北京 12℃，模拟数据。")])
        requests = []

        def create(**kwargs):
            requests.append(kwargs)
            return model(kwargs["messages"], kwargs["tools"])

        client = NS(chat=NS(completions=NS(create=create)))
        settings = NS(model="fake-model-no-api", request_options={})
        result = await run_mcp_agent(client, settings, question="北京的模拟天气？")
        self.assertEqual(result["server"], "agent-learning-tools")
        self.assertEqual(result["status"], "finished")
        self.assertEqual(set(result["tools"]), {"weather", "search_notes"})
        self.assertEqual(json.loads(model.inputs[1]["messages"][-1]["content"])["weather"], "下雨，12℃")
        self.assertFalse(requests[0]["parallel_tool_calls"])
        self.assertEqual(requests[0]["tool_choice"], "auto")


if __name__ == "__main__":
    unittest.main()
