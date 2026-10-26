"""生成记录页：列表 + 分页加载。"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout

from schemas.generation import GenerationListItem

from ui.image import ImageLoader, is_local
from ui.worker import call_error_message, run_in_worker
from ui.pages.base import ScrollPage

_STATUS_TEXT = {
    "pending": "排队中",
    "processing": "生成中",
    "success": "完成",
    "failed": "失败",
}


def _fmt_time(created_at: str | None) -> str:
    if not created_at:
        return "-"
    try:
        from datetime import datetime

        dt = datetime.fromisoformat(created_at)
        return dt.strftime("%m/%d %H:%M")
    except Exception:  # noqa: BLE001
        return "-"


class HistoryPage(ScrollPage):
    def __init__(self, ctx, parent=None):
        super().__init__(parent)
        self.ctx = ctx
        self.page = 1
        self.has_more = False
        self._loading = False
        self._loader = ImageLoader(self)
        self._pending: dict[str, QLabel] = {}
        self._loader.loaded.connect(self._on_image_ready)

        self._title = QLabel("我的生成记录")
        self._title.setProperty("class", "section")
        self.body.addWidget(self._title)

        self._list_box = QFrame()
        self._list_box.setStyleSheet("background:transparent;")
        self._list_lay = QVBoxLayout(self._list_box)
        self._list_lay.setContentsMargins(0, 0, 0, 0)
        self._list_lay.setSpacing(10)
        self.body.addWidget(self._list_box)

        self.more_btn = QPushButton("加载更多")
        self.more_btn.setProperty("class", "ghost")
        self.more_btn.setProperty("block", True)
        self.more_btn.clicked.connect(self._load_more)
        self.more_btn.hide()
        self.body.addWidget(self.more_btn)

    def showEvent(self, event) -> None:  # noqa: D102
        super().showEvent(event)
        self.reload()

    def reload(self) -> None:
        self.page = 1
        self._clear_items()
        self._fetch()

    def _clear_items(self) -> None:
        while self._list_lay.count():
            item = self._list_lay.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        self.more_btn.hide()

    def _fetch(self) -> None:
        if self._loading:
            return
        self._loading = True
        self.more_btn.setEnabled(False)

        def _done(data: dict) -> None:
            self._loading = False
            self.more_btn.setEnabled(True)
            self.has_more = data["has_more"]
            items = [GenerationListItem(**it) for it in data["items"]]
            for it in items:
                self._list_lay.addWidget(self._item(it))
            if self.has_more:
                self.more_btn.show()

        def _fail(err) -> None:
            self._loading = False
            self.ctx.toast.show(call_error_message(err), "error")

        run_in_worker(_fetch_generations, _done, _fail, self.page)

    def _load_more(self) -> None:
        self.page += 1
        self._fetch()

    def _item(self, it: GenerationListItem) -> QFrame:
        from ui.widgets import ClickableCard

        row = ClickableCard()
        row.setProperty("listrow", True)
        lay = QHBoxLayout(row)
        lay.setContentsMargins(10, 10, 10, 10)
        lay.setSpacing(12)

        thumb = QLabel()
        thumb.setAlignment(Qt.AlignCenter)
        thumb.setFixedSize(54, 72)
        thumb.setStyleSheet("background:#1e1830; border-radius:8px;")
        thumb.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        text = _STATUS_TEXT.get(it.status, it.status)
        if it.first_result_url:
            self._pending[it.first_result_url] = thumb
            self._loader.load(it.first_result_url, 54, 72)
        else:
            thumb.setText(text)
            thumb.setProperty("class", "faint")
        lay.addWidget(thumb)

        info = QVBoxLayout()
        info.setSpacing(4)
        name = QLabel(it.template_name or "自定义提示词")
        name.setStyleSheet("background:transparent; font-weight:600; font-size:14px;")
        name.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        meta = QLabel(f"{_fmt_time(it.created_at)} · {it.quantity} 张")
        meta.setProperty("class", "faint")
        meta.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        info.addWidget(name)
        info.addWidget(meta)
        lay.addLayout(info, 1)

        badge = QLabel(text)
        badge.setProperty("badge", "ok" if it.status == "success" else "danger" if it.status == "failed" else "")
        badge.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        lay.addWidget(badge)

        row.clicked.connect(lambda gid=it.generation_id: self._open(gid))
        return row

    def _open(self, gen_id: int) -> None:
        self.ctx.navigate("result", gen_id)

    def _on_image_ready(self, src: str, pm) -> None:
        label = self._pending.pop(src, None)
        if label is None or pm is None or pm.isNull():
            return
        label.setPixmap(pm)
        label.setStyleSheet("background:transparent;")


def _fetch_generations(page: int) -> dict:
    from services import facade as svc

    return svc.generation_list(page, 20)