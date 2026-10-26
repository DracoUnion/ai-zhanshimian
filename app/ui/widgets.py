"""侧边导航 + 顶栏。"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QButtonGroup, QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout

_PAGES = [
    ("home", "首页"),
    ("workspace", "生成"),
    ("history", "记录"),
    ("account", "我的"),
]


class Sidebar(QFrame):
    """左侧导航：首页 / 生成 / 记录 / 我的。切换发 `navigate(str)`。"""

    navigate = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setProperty("sidebar", True)
        self.setFixedWidth(184)
        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        self._buttons: dict[str, QPushButton] = {}

        root = QVBoxLayout(self)
        root.setContentsMargins(14, 20, 14, 16)
        root.setSpacing(4)

        brand = QLabel("✦  AI 展示面大师")
        brand.setProperty("class", "brand")
        root.addWidget(brand)
        root.addSpacing(16)

        for key, label in _PAGES:
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setProperty("nav", True)
            btn.setCursor(Qt.PointingHandCursor)
            self._group.addButton(btn)
            self._buttons[key] = btn
            btn.clicked.connect(lambda _=False, k=key: self.navigate.emit(k))
            root.addWidget(btn)

        root.addStretch(1)

    def set_active(self, key: str) -> None:
        if key in self._buttons:
            self._buttons[key].setChecked(True)


class TopBar(QFrame):
    """顶栏：当前页标题。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setProperty("topbar", True)
        self.setFixedHeight(54)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(20, 0, 20, 0)
        self.title = QLabel("AI 展示面大师")
        self.title.setProperty("class", "brand")
        lay.addWidget(self.title)
        lay.addStretch(1)

    def set_title(self, text: str) -> None:
        self.title.setText(text)


class ClickableCard(QFrame):
    """可点击卡片：点击整卡发 `clicked` 信号（子控件设 WA_TransparentForMouseEvents 以免拦截）。"""

    clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCursor(Qt.PointingHandCursor)

    def mouseReleaseEvent(self, event) -> None:  # noqa: D102
        if event.button() == Qt.LeftButton and self.rect().contains(event.position().toPoint()):
            self.clicked.emit()
        super().mouseReleaseEvent(event)


def section_card(title: str = "", sub: str = "") -> tuple[QFrame, QVBoxLayout, QLabel]:
    """生成一个卡片容器，返回 (frame, 内部 layout, 标题 label)。"""
    frame = QFrame()
    frame.setProperty("card", True)
    lay = QVBoxLayout(frame)
    lay.setContentsMargins(16, 16, 16, 16)
    lay.setSpacing(12)
    title_label = None
    if title:
        title_label = QLabel(title)
        title_label.setProperty("class", "section")
        if sub:
            sub_label = QLabel(sub)
            sub_label.setProperty("class", "muted")
            row = QHBoxLayout()
            row.setSpacing(8)
            row.addWidget(title_label)
            row.addWidget(sub_label)
            row.addStretch(1)
            lay.addLayout(row)
        else:
            lay.addWidget(title_label)
    return frame, lay, title_label


def banner_label(text: str, kind: str = "gold") -> QLabel:
    lab = QLabel(text)
    lab.setProperty("badge", kind)
    lab.setAlignment(Qt.AlignCenter)
    return lab