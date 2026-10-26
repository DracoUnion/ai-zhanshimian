"""模板选择：模板网格卡片（选中态 / 封面加载）。"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QButtonGroup, QGridLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from schemas.template import TemplateOut
from ui.image import ImageLoader, is_local

PALETTE = ["#2b2a45", "#223a34", "#381f2d", "#2e3a25", "#332e1d"]


class TemplateCard(QWidget):
    """单张模板卡：封面色块/封面图 + 名称，可选中。"""

    def __init__(self, template: TemplateOut, index: int, parent=None):
        super().__init__(parent)
        self.template = template
        self.setFixedSize(96, 118)

        self._btn = QPushButton(self)
        self._btn.setProperty("template", True)
        self._btn.setCheckable(True)
        self._btn.setCursor(Qt.PointingHandCursor)
        self._btn.setGeometry(0, 0, 96, 118)

        self._cover = QLabel(self)
        self._cover.setStyleSheet(f"background:{PALETTE[index % len(PALETTE)]}; border-radius:8px;")
        self._cover.setGeometry(6, 6, 84, 72)
        self._cover.setAlignment(Qt.AlignCenter)
        self._cover.setText(template.name[0])
        self._cover.setStyleSheet(
            self._cover.styleSheet() + " color:rgba(255,255,255,0.6); font-weight:700; font-size:20px;"
        )

        self._name = QLabel(template.name, self)
        self._name.setAlignment(Qt.AlignCenter)
        self._name.setStyleSheet("background:transparent; color:inherit; font-size:12px;")
        self._name.setGeometry(0, 84, 96, 30)

    def apply_cover(self, pm) -> None:
        if pm is None or pm.isNull():
            return
        self._cover.setText("")
        self._cover.setPixmap(pm.scaled(84, 72, Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def set_checked(self, checked: bool) -> None:
        self._btn.setChecked(checked)

    def clicked(self, callback) -> None:
        self._btn.clicked.connect(lambda _=False: callback())


class TemplatePicker(QWidget):
    """模板墙：点击发 `selected(int)`。"""

    selected = Signal(int)

    def __init__(self, templates: list[TemplateOut], parent=None):
        super().__init__(parent)
        self.templates = templates
        self._cards: list[TemplateCard] = []
        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        self._loader = ImageLoader(self)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(10)

        title = QLabel("选择风格")
        title.setProperty("class", "section")
        lay.addWidget(title)

        grid = QGridLayout()
        grid.setSpacing(10)
        lay.addLayout(grid)

        for i, t in enumerate(templates):
            card = TemplateCard(t, i, self)
            card.set_checked(False)
            card.clicked(lambda tid=t.id: self.selected.emit(tid))
            self._group.addButton(card._btn)
            self._cards.append(card)
            grid.addWidget(card, i // 3, i % 3)
            if t.cover_url and is_local(t.cover_url):
                self._loader.load(t.cover_url, 84, 72)
                self._loader.loaded.connect(lambda _src, pm, c=card: c.apply_cover(pm))

        self._value: int | None = None

    def select(self, template_id: int | None) -> None:
        self._value = template_id
        for card in self._cards:
            card.set_checked(card.template.id == template_id)

    def value(self) -> int | None:
        return self._value