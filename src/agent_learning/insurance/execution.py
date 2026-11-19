"""运行事件与合作取消，独立于 HTTP、存储和模型供应商。"""


class ExecutionCancelled(Exception):
    """取消只在可检查的边界生效，不代表撤回已发出的网络请求。"""


def check_cancelled(should_cancel=None):
    if should_cancel is not None and should_cancel():
        raise ExecutionCancelled("本次操作已停止。")


def emit(on_event, event_type, message, **details):
    if on_event is not None:
        on_event({"type": event_type, "message": message, **details})
