"""同一比较任务的配置、模型适配与会话保存；密钥只留在客户端。"""

from pathlib import Path
import threading

from ..config import load_settings
from .catalog import Catalog
from .workflow import run_comparison


_RUN_LOCK = threading.Lock()


def load_catalog(kind="demo"):
    if kind not in ("demo", "official"):
        raise ValueError("资料目录需为 demo 或 official。")
    return Catalog() if kind == "demo" else Catalog(Path(__file__).resolve().parents[1] / "data" / "insurance_official.json")


def model_adapter(client, settings):
    def request(messages, tools):
        options = dict(settings.request_options)
        # 比较完成工具需要列出多产品的证据编号，单次文本练习的输出额度不足。
        if "max_tokens" in options:
            options["max_tokens"] = 2200
        elif "max_completion_tokens" in options:
            options["max_completion_tokens"] = 4096
        return client.chat.completions.create(model=settings.model, messages=messages, tools=tools,
                                             tool_choice="auto", parallel_tool_calls=False, **options)
    return request


def run_session(store, session_id, request=None, mode="offline", catalog=None, max_calls=6):
    if mode not in ("offline", "live"):
        raise ValueError("运行模式需为 offline 或 live。")
    if not _RUN_LOCK.acquire(blocking=False):
        raise ValueError("已有比较任务正在运行，请等待完成后再试。")
    try:
        record = store.load(session_id)
        catalog = catalog or load_catalog(record["catalog_kind"])
        current = request if request is not None else record["request"]
        # 缺需求时不创建模型客户端；补充后从保存的需求重新取证，避免混用旧资料。
        from .workflow import prepare_request
        ready = prepare_request(current, catalog)
        if mode == "offline" or ready["status"] == "needs_input":
            report = run_comparison(current, catalog=catalog, mode="offline")
            report["mode"] = mode
        else:
            settings = load_settings()
            with settings.create_client() as client:
                report = run_comparison(current, catalog=catalog, mode="live", max_calls=max_calls,
                                        request_model=model_adapter(client, settings))
        report.update(session_id=session_id, catalog_kind=record["catalog_kind"],
                      revision=record["revision"] + 1)
        store.save(session_id, report)
        return report
    finally:
        _RUN_LOCK.release()
