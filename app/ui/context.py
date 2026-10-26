"""UI 上下文：页面与主窗口之间的回调集合（无支付/解锁/余额）。"""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from app.ui.toast import ToastManager


class AppContext:
    """注入给所有页面/组件的最小回调集。"""

    def __init__(self, window, toast: "ToastManager", navigate: Callable):
        self.window = window
        self.toast = toast
        self.navigate = navigate