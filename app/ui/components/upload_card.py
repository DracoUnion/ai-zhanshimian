"""上传卡片：点击选图 → 压缩 → 上传 → 预览。"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QFileDialog, QFrame, QLabel, QVBoxLayout

from app.services import facade as svc
from app.ui.image_tools import compress_image_bytes
from app.ui.worker import call_error_message, run_in_worker


class UploadCard(QFrame):
    """选择并上传一张图片；上传成功发 `changed(object_key, view_url)`。"""

    changed = Signal(str, str)

    def __init__(self, label: str, hint: str, kind: str, ctx, parent=None):
        super().__init__(parent)
        self.kind = kind
        self.hint = hint
        self.ctx = ctx
        self.object_key: str | None = None
        self.view_url: str | None = None
        self.busy = False

        self.setFixedSize(168, 224)
        self.setProperty("soft", True)
        self.setCursor(Qt.PointingHandCursor)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(10, 10, 10, 10)
        lay.setSpacing(6)

        self.preview = QLabel(self)
        self.preview.setAlignment(Qt.AlignCenter)
        self.preview.setStyleSheet("background:transparent;")
        self.preview.setFixedHeight(150)
        lay.addWidget(self.preview, 1)

        self.name_label = QLabel(label, self)
        self.name_label.setAlignment(Qt.AlignCenter)
        self.name_label.setStyleSheet("background:transparent; font-size:13px; font-weight:600;")
        lay.addWidget(self.name_label)

        self.hint_label = QLabel(hint, self)
        self.hint_label.setAlignment(Qt.AlignCenter)
        self.hint_label.setProperty("class", "faint")
        self.hint_label.setStyleSheet("background:transparent;")
        lay.addWidget(self.hint_label)

        self.set_empty()

    def set_empty(self) -> None:
        self.preview.setText("＋")
        self.preview.setStyleSheet(
            "background:rgba(30,24,48,0.6); border:1.5px dashed rgba(255,255,255,0.18); border-radius:12px;"
            " color:#6f675c; font-size:26px;"
        )
        self.hint_label.setText(self._busy_text())

    def _busy_text(self) -> str:
        return "上传中…" if self.busy else (self.hint if hasattr(self, "hint") else "点击选择/拍照")

    def set_preview(self, view_url: str) -> None:
        pm = QPixmap(view_url)
        if pm.isNull():
            self.set_empty()
            return
        pm = pm.scaled(148, 150, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.preview.setPixmap(pm)
        self.preview.setStyleSheet("background:transparent;")
        self.hint_label.setText("点击更换")

    def mousePressEvent(self, event) -> None:  # noqa: D102
        if not self.busy:
            self.pick()
        super().mousePressEvent(event)

    def pick(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            f"选择{self.name_label.text()}",
            "",
            "图片文件 (*.jpg *.jpeg *.png *.webp *.heic)",
        )
        if not path:
            return
        self.busy = True
        self.setCursor(Qt.WaitCursor)
        self.hint_label.setText("上传中…")

        def _compress():
            return compress_image_bytes(path)

        def _done(result):
            data, content_type = result
            run_in_worker(
                svc.upload_image,
                lambda r: self._uploaded(r),
                lambda e: self._failed(e),
                self.kind,
                data,
                content_type,
            )

        def _failed(err):
            self.busy = False
            self.setCursor(Qt.PointingHandCursor)
            self.hint_label.setText("点击选择/拍照")
            self.ctx.toast.show(call_error_message(err), "error")

        run_in_worker(_compress, _done, _failed)

    def _uploaded(self, result: dict) -> None:
        self.busy = False
        self.setCursor(Qt.PointingHandCursor)
        self.object_key = result["object_key"]
        self.view_url = result["view_url"]
        self.set_preview(self.view_url)
        self.changed.emit(self.object_key, self.view_url)
        self.ctx.toast.show("已上传", "success")

    def _failed(self, err) -> None:
        self.busy = False
        self.setCursor(Qt.PointingHandCursor)
        self.hint_label.setText("点击选择/拍照")
        self.ctx.toast.show(call_error_message(err), "error")

    def clear(self) -> None:
        self.object_key = None
        self.view_url = None
        self.set_empty()