"""后台执行辅助：把阻塞的服务调用放到线程池，结果/异常送回 UI 线程。

- `run_in_worker(fn, on_done, on_error, *args, **kwargs)`：后台执行，回调在主线程；
- `Poller`：QTimer 轮询辅助（生成/订单状态等待）。
"""
from __future__ import annotations

import traceback
from typing import Callable, Optional

from PySide6.QtCore import QObject, QRunnable, QThreadPool, QTimer, Signal
from PySide6.QtWidgets import QWidget

_pool: Optional[QThreadPool] = None


class _Signal(QObject):
    done = Signal(object)  # result
    err = Signal(object)  # Exception


class _Runner(QRunnable):
    def __init__(self, sig: _Signal, fn: Callable, args: tuple, kwargs: dict):
        super().__init__()
        self.sig = sig
        self.fn = fn
        self.args = args
        self.kwargs = kwargs

    def run(self) -> None:  # worker thread
        try:
            result = self.fn(*self.args, **self.kwargs)
        except Exception as exc:  # noqa: BLE001
            self.sig.err.emit(_wrap(exc))
        else:
            self.sig.done.emit(result)


class _CallError:
    """跨线程包装的异常：保留信息，附带堆栈便于定位。"""

    def __init__(self, exc: BaseException):
        self.exc = exc
        self.tb = traceback.format_exc()


def _wrap(exc: BaseException):
    return _CallError(exc)


def run_in_worker(
    fn: Callable,
    on_done: Optional[Callable] = None,
    on_error: Optional[Callable] = None,
    *args,
    **kwargs,
) -> None:
    """后台执行 fn；成功回调 on_done(result)，失败回调 on_error(_CallError)。均在 UI 线程调用。"""
    global _pool
    if _pool is None:
        _pool = QThreadPool.globalInstance()

    sig = _Signal()
    if on_done:
        sig.done.connect(on_done)
    if on_error:
        sig.err.connect(on_error)
    _pool.start(_Runner(sig, fn, args, kwargs))


def call_error_message(ce: _CallError) -> str:
    from app.core.errors import BizError

    if isinstance(ce.exc, BizError):
        return ce.exc.message
    return str(ce.exc) or "操作失败"


class Poller(QObject):
    """在父控件存活期内周期性触发 tick（QTimer，默认 2s）。析构自动停止。"""

    def __init__(self, parent: "QWidget | None" = None, interval_ms: int = 2000):
        super().__init__(parent)
        self.timer = QTimer(self)
        self.timer.setInterval(interval_ms)
        self.timer.timeout.connect(self.on_tick)

    def start(self) -> None:
        self.timer.start()

    def stop(self) -> None:
        self.timer.stop()

    def on_tick(self) -> None:  # 子类覆写
        pass

    def dispose(self) -> None:
        self.timer.stop()