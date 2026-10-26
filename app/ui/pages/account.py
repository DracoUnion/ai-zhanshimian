"""我的页：本机资料 + 更多入口（免费无限次，无余额/解锁概念）。"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)

from services import facade as svc

from ui.worker import call_error_message, run_in_worker
from ui.pages.base import ScrollPage


class AccountPage(ScrollPage):
    def __init__(self, ctx, parent=None):
        super().__init__(parent)
        self.ctx = ctx
        self._build_profile()
        self._build_more()

    def showEvent(self, event) -> None:  # noqa: D102
        super().showEvent(event)
        self._refresh()

    # ---------------- 资料 ----------------
    def _build_profile(self) -> None:
        card = QFrame()
        card.setProperty("card", True)
        lay = QVBoxLayout(card)
        lay.setContentsMargins(16, 16, 16, 16)
        lay.setSpacing(10)

        t = QLabel("资料")
        t.setProperty("class", "section")
        lay.addWidget(t)

        self.nick_input = QLineEdit()
        self.nick_input.setPlaceholderText("昵称（用于个人简介建议）")
        self.nick_input.setMaxLength(16)
        lay.addWidget(self.nick_input)

        self.save_btn = QPushButton("保存")
        self.save_btn.setProperty("class", "ghost")
        self.save_btn.setProperty("block", True)
        self.save_btn.clicked.connect(self._save)
        lay.addWidget(self.save_btn)

        self.phone_note = QLabel("本机账户（单机模式，无需登录）")
        self.phone_note.setProperty("class", "faint")
        lay.addWidget(self.phone_note)

        self.body.addWidget(card)

    # ---------------- 更多 ----------------
    def _build_more(self) -> None:
        card = QFrame()
        card.setProperty("card", True)
        lay = QVBoxLayout(card)
        lay.setContentsMargins(16, 16, 16, 16)
        lay.setSpacing(8)

        t = QLabel("更多")
        t.setProperty("class", "section")
        lay.addWidget(t)

        lay.addWidget(self._row_btn("生成记录", lambda: self.ctx.navigate("history")))
        lay.addWidget(self._row_btn("关于 AI 展示面大师（v0.1.0）", lambda: None))

        self.body.addWidget(card)

    def _row_btn(self, text: str, callback) -> QPushButton:
        btn = QPushButton(text)
        btn.setProperty("ghost", True)
        btn.setStyleSheet("text-align:left; padding:13px 14px; font-size:14px; border-radius:12px;")
        btn.clicked.connect(lambda: callback())
        return btn

    # ---------------- 数据刷新 ----------------
    def _refresh(self) -> None:
        run_in_worker(svc.state, self._apply_state, lambda e: self.ctx.toast.show(call_error_message(e), "error"))

    def _apply_state(self, state: dict) -> None:
        self.nick_input.setText(state.get("nickname") or "")

    def _save(self) -> None:
        self.save_btn.setEnabled(False)
        self.save_btn.setText("保存中…")

        def _done(_r) -> None:
            self.save_btn.setEnabled(True)
            self.save_btn.setText("保存")
            self.ctx.toast.show("已保存", "success")

        def _fail(err) -> None:
            self.save_btn.setEnabled(True)
            self.save_btn.setText("保存")
            self.ctx.toast.show(call_error_message(err), "error")

        run_in_worker(svc.update_profile, _done, _fail, nickname=self.nick_input.text().strip() or None)