"""后台任务层。

- ``generation_exec``：生图专用后台执行（保留现有重试/兜底逻辑）。
- ``task``：通用 Task/TaskManager 状态机（零 Qt，UI 桥使用）。
"""
from __future__ import annotations

from tasks.task import Task, TaskCancelled, TaskManager, TaskState

__all__ = ["Task", "TaskState", "TaskManager", "TaskCancelled"]