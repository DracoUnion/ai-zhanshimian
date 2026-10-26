"""UI 上下文：页面与主窗口之间的回调集合（无支付；解锁为本地一次性操作）。"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:
    from .toast import ToastManager


class AppContext:
    """注入给所有页面/组件的最小回调集。"""

    def __init__(self, window, toast: "ToastManager", navigate: Callable, refresh_balance: Callable, unlock: Callable):
        self.window = window
        self.toast = toast
        self.navigate = navigate
        self.refresh_balance = refresh_balance
        self.unlock = unlock