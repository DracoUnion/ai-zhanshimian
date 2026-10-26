"""AI展示面大师 — PySide6 桌面客户端入口。

启动：
    python -m app
"""
from __future__ import annotations

import logging
import sys

from PySide6.QtWidgets import QApplication

from bootstrap import bootstrap
from config import get_settings
from ui.theme import apply_theme

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")


def main() -> int:
    settings = get_settings()
    bootstrap()

    app = QApplication(sys.argv)
    app.setApplicationName(settings.app_name)
    apply_theme(app)

    from ui.main_window import MainWindow

    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())