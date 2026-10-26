"""我的页：本机余额/解锁/试用状态 + 资料 + 更多入口。"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)

from app.services import facade as svc

from ..worker import call_error_message, run_in_worker
from .base import ScrollPage


class AccountPage(ScrollPage):
    def __init__(self, ctx, parent=None):
        super().__init__(parent)
        self.ctx = ctx
        self._build_balance()
        self._build_profile()
        self._build_more()

    def showEvent(self, event) -> None:  # noqa: D102
        super().showEvent(event)
        self._refresh()

    # ---------------- 余额卡 ----------------
    def _build_balance(self) -> None:
        card = QFrame()
        card.setProperty("accent-card", True)
        lay = QVBoxLayout(card)
        lay.setContentsMargins(20, 20, 20, 20)
        lay.setSpacing(10)

        row = QHBoxLayout()
        col = QVBoxLayout()
        muted = QLabel("可用生成次数")
        muted.setProperty("class", "muted")
        self.balance_num = QLabel("—")
        self.balance_num.setProperty("class", "money")
        col.addWidget(muted)
        col.addWidget(self.balance_num)
        row.addLayout(col)
        row.addStretch(1)
        self.unlock_btn = QPushButton("¥69 解锁")
        self.unlock_btn.setProperty("class", "gold")
        self.unlock_btn.clicked.connect(self._do_unlock)
        self.unlock_btn.hide()
        row.addWidget(self.unlock_btn)
        lay.addLayout(row)

        status_row = QHBoxLayout()
        status_row.setSpacing(8)
        self.unlock_st = QLabel("解锁：—")
        self.trial_st = QLabel("试用：—")
        for st in (self.unlock_st, self.trial_st):
            st.setProperty("badge", "")
            status_row.addWidget(st)
        status_row.addStretch(1)
        lay.addLayout(status_row)

        self.body.addWidget(card)

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
        lay.addWidget(self._row_btn("解锁与说明", lambda: self.ctx.navigate("pricing")))
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
        self.balance_num.setText(str(state["credits"]))
        self.unlock_st.setText(f"解锁：{'已解锁 69 包' if state['unlocked'] else '未解锁'}")
        self.trial_st.setText(f"试用：{'已用' if state['trial_used'] else '未用（可用 1 次）'}")
        self.nick_input.setText(state.get("nickname") or "")
        self.unlock_btn.setVisible(not state["unlocked"])
        self.unlock_btn.setEnabled(True)
        self.unlock_btn.setText("¥69 解锁")

    def _do_unlock(self) -> None:
        if not self.unlock_btn.isEnabled():
            return
        self.unlock_btn.setEnabled(False)
        self.unlock_btn.setText("解锁中…")
        self.ctx.unlock(on_done=self._refresh)

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