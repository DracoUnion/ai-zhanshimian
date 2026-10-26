"""页面基类：滚动容器 + 居中内容列（对齐移动端 540px 观感）。"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QScrollArea, QVBoxLayout, QWidget


class ScrollPage(QWidget):
    """整页可滚动，内容列居中（最大宽度 560px）。子类往 self.body 加内容。"""

    def __init__(self, parent=None):
        super().__init__(parent)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self.scroll = QScrollArea(self)
        self.scroll.setWidgetResizable(True)
        self.scroll.setAlignment(Qt.AlignHCenter | Qt.AlignTop)
        outer.addWidget(self.scroll)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        self.center = QWidget()
        self.center.setMaximumWidth(560)
        self.body = QVBoxLayout(self.center)
        self.body.setContentsMargins(16, 18, 16, 24)
        self.body.setSpacing(14)
        self.body.setAlignment(Qt.AlignTop)

        content_layout.addWidget(self.center)
        content_layout.setAlignment(Qt.AlignHCenter | Qt.AlignTop)

        self.scroll.setWidget(content)
        self.scroll.viewport().setStyleSheet("background:transparent;")