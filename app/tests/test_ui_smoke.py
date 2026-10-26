"""UI 冒烟：主窗口能在离屏平台构建、完成页面切换与一次真实生成渲染而不崩溃。"""
from __future__ import annotations

import time

import pytest


@pytest.fixture(scope="module")
def qapp():
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    yield app


def _pump(qapp, rounds=6, delay=0.02):
    for _ in range(rounds):
        qapp.processEvents()
        time.sleep(delay)


def test_main_window_builds_and_navigates(qapp, fresh_db):
    from app.ui.main_window import MainWindow

    win = MainWindow()
    win.show()
    _pump(qapp)

    for key in ("home", "workspace", "history", "account", "home"):
        win.navigate(key)
        _pump(qapp)

    assert win.stack.currentWidget() is win.pages["home"]
    win.close()
    _pump(qapp, 2)


def test_result_page_renders_generation(qapp, fresh_db, sync_generation):
    from app.services import facade as svc
    from app.tasks.generation_exec import run_generation
    from app.ui.main_window import MainWindow

    up = svc.upload_image("selfie", b"\xff\xd8mock", "image/jpeg")
    created = svc.create_generation(selfie_key=up["object_key"], template_id=1, quantity=1)
    run_generation(created["generation_id"])

    win = MainWindow()
    win.show()
    win.navigate("result", created["generation_id"])
    _pump(qapp, 8, 0.03)

    assert win.stack.currentWidget() is win.pages["result"]
    win.close()
    _pump(qapp, 2)