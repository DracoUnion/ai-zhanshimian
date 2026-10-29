"""应用上下文（零 Qt）。

由 :func:`bootstrap.build_context` 装配，UI 持有并只经它访问服务。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from common.events import EventHub

if TYPE_CHECKING:
    from config import Settings
    from tasks import TaskManager


@dataclass
class AppContext:
    """bootstrap 注入的运行时服务包。"""

    settings: "Settings"
    events: EventHub
    tasks: "TaskManager"
    extras: dict[str, Any] = field(default_factory=dict)

    def extra(self, key: str, default: Any = None) -> Any:
        """读取可选的 bootstrap 注入依赖。"""
        return self.extras.get(key, default)