"""定价页：69 解锁包（本地一次性解锁，无充值/支付）。"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout

from ..widgets import banner_label
from ..worker import run_in_worker
from .base import ScrollPage

_FEATS = [
    "免费体验 1 张之后，无限继续生成",
    "解锁即赠 69 次生成额度",
    "全部风格模板 + 多张成组",
    "生成失败自动退回次数",
]


class PricingPage(ScrollPage):
    def __init__(self, ctx, parent=None):
        super().__init__(parent)
        self.ctx = ctx
        self._build_unlock()

        note = QLabel("单机本地版：解锁为一次性本地操作，无需登录与支付。")
        note.setProperty("class", "faint")
        note.setAlignment(Qt.AlignCenter)
        self.body.addWidget(note)

    def showEvent(self, event) -> None:  # noqa: D102
        super().showEvent(event)
        self._refresh_unlock_btn()

    def _build_unlock(self) -> None:
        card = QFrame()
        card.setProperty("accent-card", True)
        lay = QVBoxLayout(card)
        lay.setContentsMargins(20, 20, 20, 20)
        lay.setSpacing(12)

        top = QHBoxLayout()
        tag = banner_label("最多人购买", "gold")
        tag.setFixedWidth(90)
        top.addWidget(tag)
        top.addStretch(1)
        lay.addLayout(top)

        h2 = QLabel("69 元解锁全部功能")
        h2.setProperty("class", "h2")
        lay.addWidget(h2)

        for feat in _FEATS:
            row = QHBoxLayout()
            row.setSpacing(8)
            ck = QLabel("✓")
            ck.setProperty("class", "accent")
            ck.setStyleSheet("font-weight:700; background:transparent;")
            f = QLabel(feat)
            f.setProperty("class", "muted")
            row.addWidget(ck)
            row.addWidget(f)
            row.addStretch(1)
            lay.addLayout(row)

        self.unlock_btn = QPushButton("¥69 立即解锁")
        self.unlock_btn.setProperty("class", "gold")
        self.unlock_btn.setProperty("block", True)
        self.unlock_btn.clicked.connect(self._do_unlock)
        lay.addWidget(self.unlock_btn)

        self.body.addWidget(card)

    def _do_unlock(self) -> None:
        if not self.unlock_btn.isEnabled():
            return
        self.unlock_btn.setEnabled(False)
        self.unlock_btn.setText("解锁中…")
        self.ctx.unlock(on_done=lambda: self._refresh_unlock_btn())

    def _refresh_unlock_btn(self) -> None:
        def _apply(state: dict):
            if state.get("unlocked"):
                self.unlock_btn.setText("已解锁 ✓")
                self.unlock_btn.setEnabled(False)
            else:
                self.unlock_btn.setText("¥69 立即解锁")
                self.unlock_btn.setEnabled(True)

        run_in_worker(_fetch_state, _apply, lambda _e: None)


def _fetch_state() -> dict:
    from app.services import facade as svc

    return svc.state()