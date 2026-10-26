"""生成结果页：轮询生成状态 → 展示成组结果 / 失败原因。"""

from __future__ import annotations

import os
import shutil

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

from schemas.generation import GenerationDetail, ResultImage

from ui.image import ImageLoader, is_local
from ui.worker import Poller, call_error_message, run_in_worker
from ui.pages.base import ScrollPage


class ResultPage(ScrollPage):
    def __init__(self, ctx, parent=None):
        super().__init__(parent)
        self.ctx = ctx
        self.generation_id: int | None = None
        self._loader = ImageLoader(self)
        self._pending: dict[str, QLabel] = {}
        self._loader.loaded.connect(self._on_image_ready)

        self.poller = Poller(self, 2000)
        self.poller.timer.timeout.connect(self._reload)

    # ---------------- 加载 ----------------
    def load(self, gen_id: int) -> None:
        self.generation_id = gen_id
        self._clear_content()
        self._show_loading()
        self._reload()

    def showEvent(self, event) -> None:  # noqa: D102
        super().showEvent(event)
        if self.generation_id:
            self._reload()

    def hideEvent(self, event) -> None:  # noqa: D102
        self.poller.stop()
        super().hideEvent(event)

    # ---------------- 渲染 ----------------
    def _clear_content(self) -> None:
        while self.body.count():
            item = self.body.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

    def _show_loading(self) -> None:
        box = QFrame()
        box.setProperty("card", True)
        ly = QVBoxLayout(box)
        ly.setContentsMargins(20, 44, 20, 44)
        ly.setSpacing(12)
        ly.setAlignment(Qt.AlignCenter)

        spin = QLabel("⟳")
        spin.setAlignment(Qt.AlignCenter)
        spin.setStyleSheet("color:#d8b25f; font-size:34px;")
        t = QLabel("AI 正在为你生成…")
        t.setAlignment(Qt.AlignCenter)
        t.setProperty("class", "h2")
        s = QLabel("约 30 秒~2 分钟，失败会自动提示，请稍候")
        s.setAlignment(Qt.AlignCenter)
        s.setProperty("class", "muted")
        ly.addWidget(spin)
        ly.addWidget(t)
        ly.addWidget(s)
        self.body.addWidget(box)

    def _reload(self) -> None:
        if not self.generation_id:
            return
        run_in_worker(
            _fetch_detail,
            lambda d: self._render(d),
            lambda e: self._render_error(call_error_message(e)),
            self.generation_id,
        )

    def _render(self, data: dict) -> None:
        detail = GenerationDetail(**data)
        self._clear_content()

        if detail.status in ("pending", "processing"):
            self._show_loading()
            self.poller.start()
            return
        self.poller.stop()

        if detail.status == "success":
            self._render_success(detail)
        else:
            self._render_failed(detail)

    def _render_success(self, detail: GenerationDetail) -> None:
        card = QFrame()
        card.setProperty("card", True)
        lay = QVBoxLayout(card)
        lay.setContentsMargins(16, 16, 16, 16)
        lay.setSpacing(10)
        t = QLabel(f"已生成 {len(detail.results)} 张")
        t.setProperty("class", "section")
        lay.addWidget(t)
        grid = QGridLayout()
        grid.setSpacing(10)
        for i, shot in enumerate(detail.results):
            grid.addWidget(self._shot(shot, i), i // 2, i % 2)
        lay.addLayout(grid)
        self.body.addWidget(card)

        row = QFrame()
        row.setStyleSheet("background:transparent;")
        rl = QVBoxLayout(row)
        rl.setContentsMargins(0, 0, 0, 0)
        btns = QHBoxLayout()
        btns.setSpacing(10)
        again = QPushButton("再生成一组")
        again.setProperty("class", "ghost")
        again.clicked.connect(lambda: self.ctx.navigate("workspace"))
        hist = QPushButton("查看我的记录")
        hist.setProperty("class", "gold")
        hist.clicked.connect(lambda: self.ctx.navigate("history"))
        btns.addWidget(again)
        btns.addWidget(hist)
        rl.addLayout(btns)
        self.body.addWidget(row)

    def _shot(self, shot: ResultImage, index: int) -> QFrame:
        box = QFrame()
        box.setProperty("soft", True)
        box.setFixedSize(240, 360)
        ly = QVBoxLayout(box)
        ly.setContentsMargins(8, 8, 8, 8)
        ly.setSpacing(6)

        img = QLabel()
        img.setAlignment(Qt.AlignCenter)
        img.setStyleSheet("background:#1e1830; border-radius:10px;")
        img.setFixedHeight(300)
        img.setText("…")
        img.setProperty("class", "faint")
        self._pending[shot.url] = img
        self._loader.load(shot.url, 224, 300)
        ly.addWidget(img)

        save = QPushButton("保存")
        save.setProperty("class", "ghost")
        save.clicked.connect(lambda: self._save_shot(shot, index))
        h = QHBoxLayout()
        h.addStretch(1)
        h.addWidget(save)
        h.addStretch(1)
        ly.addLayout(h)
        return box

    def _on_image_ready(self, src: str, pm) -> None:
        label = self._pending.pop(src, None)
        if label is None or pm is None or pm.isNull():
            return
        label.setPixmap(pm)
        label.setStyleSheet("background:transparent;")

    def _save_shot(self, shot: ResultImage, index: int) -> None:
        if not shot.url or not is_local(shot.url):
            self.ctx.toast.show("该图片暂不支持本地保存", "info")
            return
        default = os.path.join(os.path.expanduser("~"), "Pictures", f"展示面-{index + 1}.jpg")
        path, _ = QFileDialog.getSaveFileName(self, "保存图片", default, "图片文件 (*.jpg)")
        if not path:
            return
        try:
            shutil.copyfile(shot.url, path)
            self.ctx.toast.show("已保存", "success")
        except Exception as e:  # noqa: BLE001
            self.ctx.toast.show(f"保存失败：{e}", "error")

    def _render_failed(self, detail: GenerationDetail) -> None:
        box = QFrame()
        box.setProperty("card", True)
        ly = QVBoxLayout(box)
        ly.setContentsMargins(20, 40, 20, 40)
        ly.setSpacing(10)
        ly.setAlignment(Qt.AlignCenter)

        t = QLabel("生成未成功")
        t.setProperty("class", "h2")
        t.setAlignment(Qt.AlignCenter)
        s = QLabel(detail.fail_reason or "未知错误")
        s.setProperty("class", "muted")
        s.setAlignment(Qt.AlignCenter)
        s.setWordWrap(True)
        ly.addWidget(t)
        ly.addWidget(s)
        self.body.addWidget(box)

        btn = QPushButton("重新生成")
        btn.setProperty("class", "gold")
        btn.setProperty("block", True)
        btn.clicked.connect(lambda: self.ctx.navigate("workspace"))
        self.body.addWidget(btn)

    def _render_error(self, message: str) -> None:
        self._clear_content()
        box = QFrame()
        box.setProperty("card", True)
        ly = QVBoxLayout(box)
        ly.setContentsMargins(20, 40, 20, 40)
        t = QLabel("找不到这条生成记录")
        t.setProperty("class", "h2")
        t.setAlignment(Qt.AlignCenter)
        s = QLabel(message)
        s.setProperty("class", "muted")
        s.setAlignment(Qt.AlignCenter)
        ly.addWidget(t)
        ly.addWidget(s)
        self.body.addWidget(box)


def _fetch_detail(gen_id: int) -> dict:
    from services import facade as svc

    return svc.generation_detail(gen_id)