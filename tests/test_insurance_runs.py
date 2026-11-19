"""持久任务、版本、幂等与协作取消；不读取密钥或请求外部模型。"""

from concurrent.futures import ThreadPoolExecutor
from contextlib import nullcontext
from copy import deepcopy
import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from agent_learning.insurance.catalog import Catalog
from agent_learning.insurance.runs import RunManager
from agent_learning.insurance.store import SessionStore, StoreConflict
from agent_learning.insurance.workflow import run_comparison


REQUEST = {"question": "比较保障和续保。", "profile": {"focus": ["coverage", "renewal"]},
           "selections": [{"product_id": "demo_hospital", "version": "demo-v1"},
                          {"product_id": "demo_outpatient", "version": "demo-v1"}]}


class InsuranceRunTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.store = SessionStore(self.temp.name)
        self.managers, self.gates = [], []
        self.calls = []

    def tearDown(self):
        for gate in self.gates:
            gate.set()
        for manager in self.managers:
            manager.close()
        self.temp.cleanup()

    def session(self, request=None, confirmed=True):
        session_id = self.store.create(deepcopy(REQUEST if request is None else request))
        if confirmed:
            record = self.store.load(session_id)
            self.store.update_brief(session_id, record["request"], expected_version=1)
        return session_id

    def runner(self, store, session_id, *, request=None, catalog=None, on_event=None, should_cancel=None,
               expected_version=None, **kwargs):
        self.calls.append(kwargs)
        on_event({"type": "read", "message": "读取资料。"})
        result = run_comparison(request or store.load(session_id)["request"], catalog=catalog)
        store.save(session_id, result, expected_version=expected_version)
        return result

    def manager(self, runner=None, **kwargs):
        manager = RunManager(self.store, runner or self.runner, catalogs={"demo": Catalog()}, **kwargs)
        self.managers.append(manager)
        return manager

    def submit(self, manager, session_id, token="request-1", **payload):
        return manager.submit(session_id, kind="comparison", payload={"mode": "offline", **payload},
                              expected_version=1, client_request_id=token)

    def test_duplicate_submission_does_not_execute_twice_even_after_completion(self):
        session_id, manager = self.session(), self.manager()
        first = self.submit(manager, session_id)
        completed = manager.wait(first["id"])
        second = manager.submit(session_id, kind="comparison", payload={"mode": "offline"},
                                expected_version=1, client_request_id="request-1")
        self.assertEqual(second["id"], first["id"])
        self.assertEqual(completed["status"], "succeeded")
        self.assertEqual(len(self.calls), 1)
        with self.assertRaises(StoreConflict):
            self.submit(manager, session_id, mode="live")
        self.assertIsNone(self.store.load(session_id)["active_run"])

    def test_simultaneous_duplicate_submission_has_one_persistent_run(self):
        session_id, manager = self.session(), self.manager()
        with ThreadPoolExecutor(max_workers=4) as pool:
            submitted = list(pool.map(lambda _: self.submit(manager, session_id), range(8)))
        self.assertEqual(len({run["id"] for run in submitted}), 1)
        manager.wait(submitted[0]["id"])
        self.assertEqual(len(self.calls), 1)

    def test_events_have_replay_cursor_and_survive_new_store_instance(self):
        session_id, manager = self.session(), self.manager()
        run = self.submit(manager, session_id)
        completed = manager.wait(run["id"])
        self.assertEqual([event["seq"] for event in completed["events"]], list(range(1, completed["last_seq"] + 1)))
        after = manager.get(run["id"], after_seq=2)
        self.assertTrue(all(event["seq"] > 2 for event in after["events"]))
        persisted = SessionStore(self.temp.name).load_run(run["id"])
        self.assertEqual(persisted["last_seq"], completed["last_seq"])
        self.assertNotIn("payload", completed)
        self.assertNotIn("owner_pid", completed)

    def test_cancellation_keeps_partial_result_and_stops_at_boundary(self):
        started, gate = threading.Event(), threading.Event()
        self.gates.append(gate)
        calls = []
        def cancellable(store, session_id, *, on_event, should_cancel, expected_version, **kwargs):
            calls.append("first")
            on_event({"type": "model_started", "message": "正在读取依据。"})
            started.set()
            gate.wait(3)
            if not should_cancel():
                calls.append("second")
            report = {"request": store.load(session_id)["request"], "status": "cancelled", "sources": []}
            store.save(session_id, report, expected_version=expected_version)
            return report
        session_id, manager = self.session(), self.manager(cancellable)
        run = self.submit(manager, session_id)
        self.assertTrue(started.wait(2))
        self.assertEqual(manager.cancel(run["id"])["status"], "cancelling")
        gate.set()
        completed = manager.wait(run["id"])
        self.assertEqual(completed["status"], "cancelled")
        self.assertEqual(calls, ["first"])
        self.assertEqual(self.store.load(session_id)["result"]["status"], "cancelled")
        self.assertEqual(manager.cancel(run["id"])["status"], "cancelled")

    def test_queued_cancel_never_invokes_runner_and_capacity_is_bounded(self):
        started, gate = threading.Event(), threading.Event()
        self.gates.append(gate)
        def waiting(*args, **kwargs):
            started.set()
            gate.wait(3)
            return {"status": "cancelled" if kwargs["should_cancel"]() else "ok"}
        manager = self.manager(waiting, max_workers=1, max_queue=1)
        first = self.submit(manager, self.session())
        self.assertTrue(started.wait(2))
        second = self.submit(manager, self.session())
        with self.assertRaises(StoreConflict):
            self.submit(manager, self.session())
        self.assertEqual(manager.cancel(second["id"])["status"], "cancelled")
        gate.set()
        manager.wait(first["id"])
        self.assertEqual(manager.get(second["id"])["events"][-1]["type"], "cancel_requested")

    def test_active_run_blocks_new_run_brief_and_external_writer(self):
        started, gate = threading.Event(), threading.Event()
        self.gates.append(gate)
        def waiting(*args, **kwargs):
            started.set()
            gate.wait(3)
            return {"status": "ok"}
        session_id, manager = self.session(), self.manager(waiting)
        run = self.submit(manager, session_id)
        self.assertTrue(started.wait(2))
        other = SessionStore(self.temp.name)
        with self.assertRaises(StoreConflict):
            other.update_brief(session_id, REQUEST, expected_version=1)
        with self.assertRaises(StoreConflict):
            other.save(session_id, {"request": REQUEST}, expected_version=1)
        with self.assertRaises(StoreConflict):
            self.submit(manager, session_id, token="different")
        gate.set()
        manager.wait(run["id"])

    def test_confirmation_completeness_and_version_conflicts(self):
        manager = self.manager()
        unconfirmed = self.session(confirmed=False)
        with self.assertRaises(StoreConflict):
            self.submit(manager, unconfirmed)
        incomplete = self.session(request={})
        with self.assertRaises(StoreConflict):
            self.submit(manager, incomplete)
        changed = deepcopy(REQUEST)
        changed["question"] = "进一步比较。"
        self.store.update_brief(unconfirmed, changed, expected_version=1)
        with self.assertRaises(StoreConflict):
            manager.submit(unconfirmed, kind="comparison", payload={}, expected_version=1, client_request_id="old")

    def test_restart_marks_dead_owner_interrupted_without_model_replay(self):
        session_id = self.session()
        run, _ = self.store.create_run(session_id, kind="comparison", payload={"mode": "live"},
            client_request_id="lost", expected_version=1, owner_id="old-worker", owner_pid=-1)
        self.store.change_run(run["id"], status="running")
        manager = self.manager()
        self.assertEqual(manager.get(run["id"])["status"], "interrupted")
        self.assertIsNone(self.store.load(session_id)["active_run"])
        self.assertEqual(self.calls, [])

    def test_restart_does_not_interrupt_another_live_process_owner(self):
        session_id = self.session()
        run, _ = self.store.create_run(session_id, kind="comparison", payload={}, client_request_id="active",
            expected_version=1, owner_id="other-manager", owner_pid=os.getpid())
        manager = self.manager()
        self.assertEqual(manager.get(run["id"])["status"], "queued")
        manager.cancel(run["id"])

    def test_unexpected_exception_is_sanitized_and_releases_session(self):
        def broken(*args, **kwargs):
            raise RuntimeError("SECRET_SENTINEL")
        session_id, manager = self.session(), self.manager(broken)
        run = self.submit(manager, session_id)
        completed = manager.wait(run["id"])
        self.assertEqual(completed["status"], "failed")
        self.assertNotIn("SECRET_SENTINEL", json.dumps(completed))
        self.assertIsNone(self.store.load(session_id)["active_run"])

    def test_structured_model_error_keeps_result_but_run_is_failed(self):
        def structured_error(*args, **kwargs):
            return {"status": "model_error", "content": "本次消息未完成。", "model_calls": 1}
        session_id, manager = self.session(), self.manager(structured_error)
        run = self.submit(manager, session_id)
        completed = manager.wait(run["id"])
        self.assertEqual(completed["status"], "failed")
        self.assertEqual(completed["result"]["model_calls"], 1)
        self.assertEqual(completed["events"][-1]["type"], "failed")


class InsuranceStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.store = SessionStore(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def test_legacy_json_is_migrated_without_deleting_original(self):
        session_id = "a" * 32
        legacy = {"id": session_id, "request": REQUEST, "catalog_kind": "demo", "result": {"request": REQUEST},
                  "revision": 1, "history": [], "updated_at": "2026-01-01"}
        path = Path(self.temp.name) / (session_id + ".json")
        original = json.dumps(legacy)
        path.write_text(original, encoding="utf-8")
        record = self.store.load(session_id)
        self.assertEqual(record["schema_version"], 2)
        self.assertEqual(record["brief_version"], 1)
        self.assertEqual(record["confirmed_version"], 0)
        self.assertFalse(record["result_stale"])
        self.assertEqual(path.read_text(encoding="utf-8"), original)
        self.assertEqual(self.store.list_sessions()[0]["id"], session_id)

    def test_session_summary_uses_draft_title_without_changing_confirmed_request(self):
        request = {"question": "比较选定医疗险的保障与限制。"}
        session_id = self.store.create(request)
        first_message = "我想比较普通门诊和住院的保障条件。" * 5
        self.store.append_message(session_id, "user", first_message)
        self.store.append_message(session_id, "user", "后面的消息不替换第一条标题。")
        self.assertEqual(self.store.list_sessions()[0]["title"], first_message[:60])
        self.store.set_proposal(session_id, {"request": request, "questions": []}, expected_version=1)
        self.assertEqual(self.store.list_sessions()[0]["title"], first_message[:60])
        self.store.set_proposal(session_id, {"request": {"question": "比较门诊与续保安排"}, "questions": []}, expected_version=1)
        self.assertEqual(self.store.list_sessions()[0]["title"], "比较门诊与续保安排")
        self.assertEqual(self.store.load(session_id)["request"], request)
        explicit = {"question": "已经确认的具体比较需求"}
        self.store.update_brief(session_id, explicit, expected_version=1)
        self.store.set_proposal(session_id, {"request": {"question": "新的建议标题"}, "questions": []}, expected_version=2)
        self.assertEqual(self.store.list_sessions()[0]["title"], explicit["question"])
        self.assertEqual(self.store.load(session_id)["request"], explicit)

    def test_proposal_does_not_mutate_brief_and_confirmation_marks_old_report_stale(self):
        session_id = self.store.create(REQUEST)
        self.store.save(session_id, {"request": REQUEST, "status": "completed"}, expected_version=1)
        proposal = {"request": {**REQUEST, "question": "新需求"}, "questions": [], "summary": "补充关注点"}
        self.store.set_proposal(session_id, proposal, expected_version=1)
        self.assertEqual(self.store.load(session_id)["request"], REQUEST)
        updated = self.store.update_brief(session_id, proposal["request"], expected_version=1)
        self.assertEqual(updated["brief_version"], 2)
        self.assertEqual(updated["confirmed_version"], 2)
        self.assertTrue(updated["result_stale"])
        self.assertIsNone(updated["proposal"])
        other = SessionStore(self.temp.name)
        with self.assertRaises(StoreConflict):
            other.save(session_id, {"request": REQUEST}, expected_version=1)

    def test_messages_and_report_history_are_preserved_across_instances(self):
        session_id = self.store.create(REQUEST)
        message = self.store.append_message(session_id, "user", "我想了解续保。", kind="intake", mode="offline")
        self.assertEqual(message["kind"], "intake")
        for index in range(7):
            self.store.save(session_id, {"request": REQUEST, "marker": index})
        record = SessionStore(self.temp.name).load(session_id)
        self.assertEqual(record["messages"], [message])
        self.assertEqual(len(record["history"]), 5)
        self.assertEqual(record["result"]["marker"], 6)
        self.assertEqual(record["revision"], 7)

    def test_synchronous_claim_is_reentrant_for_owner_and_blocks_other_process(self):
        session_id = self.store.create(REQUEST)
        code = """import sys
from agent_learning.insurance.store import SessionStore, StoreConflict
store = SessionStore(sys.argv[1])
try:
    with store.claim_session(sys.argv[2]):
        print('UNEXPECTED_EXECUTION')
except StoreConflict:
    print('blocked-before-model')
"""
        with self.store.claim_session(session_id) as run_id:
            with self.store.claim_session(session_id) as nested:
                self.assertEqual(nested, run_id)
            child = subprocess.run([sys.executable, "-c", code, self.temp.name, session_id],
                                   capture_output=True, text=True, timeout=10)
            self.assertEqual(child.returncode, 0, child.stderr)
            self.assertEqual(child.stdout.strip(), "blocked-before-model")
            self.store.append_message(session_id, "assistant", "任务完成。")
        self.assertIsNone(self.store.load(session_id)["active_run"])
        self.assertEqual(self.store.load_run(run_id)["status"], "succeeded")

    def test_service_claim_blocks_second_process_before_model_configuration_and_saves_one_revision(self):
        from agent_learning.insurance.service import run_session
        from agent_learning.insurance.workflow import prepare_request
        from tests.test_insurance_workflow import scripted_model
        catalog = Catalog()
        request = prepare_request(REQUEST, catalog)["request"]
        session_id = self.store.create(request)
        scripted, requests = scripted_model(catalog)
        started, gate = threading.Event(), threading.Event()
        def create_response(**kwargs):
            if not requests:
                started.set()
                gate.wait(20)
            return scripted(kwargs["messages"], kwargs["tools"])
        client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create_response)))
        settings = SimpleNamespace(model="fake-test-model", request_options={}, create_client=lambda: nullcontext(client))
        child_code = """import json, sys
from unittest.mock import patch
from agent_learning.insurance.service import run_session
from agent_learning.insurance.store import SessionStore, StoreConflict
store = SessionStore(sys.argv[1])
with patch('agent_learning.insurance.service.load_settings', side_effect=AssertionError('must-not-request-model')) as configure:
    try:
        run_session(store, sys.argv[2], mode='live')
        raise AssertionError('second-run-was-not-blocked')
    except StoreConflict:
        record=store.load(sys.argv[2])
        print(json.dumps({'configuration_calls': configure.call_count, 'revision': record['revision'], 'brief_version': record['brief_version']}))
"""
        with patch("agent_learning.insurance.service.load_settings", return_value=settings):
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(run_session, self.store, session_id, mode="live")
                try:
                    self.assertTrue(started.wait(3))
                    child = subprocess.run([sys.executable, "-c", child_code, self.temp.name, session_id],
                                           capture_output=True, text=True, timeout=15)
                    self.assertEqual(child.returncode, 0, child.stderr)
                    self.assertEqual(json.loads(child.stdout), {"configuration_calls": 0, "revision": 0, "brief_version": 1})
                finally:
                    gate.set()
                report = future.result(timeout=5)
        self.assertEqual(report["model_calls"], 3)
        first = SessionStore(self.temp.name).load(session_id)
        self.assertEqual(first["revision"], 1)
        self.assertEqual(first["result"]["revision"], 1)
        self.assertEqual(first["brief_version"], 1)
        self.assertEqual(first["history"], [])
        self.assertIsNone(first["active_run"])
        run_session(self.store, session_id)
        second = self.store.load(session_id)
        self.assertEqual(second["revision"], 2)
        self.assertEqual(second["result"]["revision"], 2)
        self.assertEqual(second["history"][0]["revision"], 1)


if __name__ == "__main__":
    unittest.main()
