"""图片工具：本地路径直接 QPixmap；http(s) 用 QNetworkAccessManager 异步加载。"""
from __future__ import annotations

from PySide6.QtCore import QObject, Qt, QUrl, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest


def is_local(src: str) -> bool:
    if not src:
        return False
    if src.startswith(("http://", "https://")):
        return False
    return True


def load_local_pixmap(src: str, max_width: int = 0, max_height: int = 0) -> QPixmap | None:
    """加载本地图片，可选按最大边长等比缩放。"""
    if not src or not is_local(src):
        return None
    path = src[len("file://"):] if src.startswith("file://") else src
    pm = QPixmap(path)
    if pm.isNull():
        return None
    if max_width > 0 and max_height > 0 and (pm.width() > max_width or pm.height() > max_height):
        pm = pm.scaled(max_width, max_height, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    return pm


class ImageLoader(QObject):
    """异步图片加载：URL 走网络，本地走磁盘。加载完成后发 `loaded(src, QPixmap)`。"""

    loaded = Signal(str, object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._nam: QNetworkAccessManager | None = None

    def _nam_instance(self) -> QNetworkAccessManager:
        if self._nam is None:
            self._nam = QNetworkAccessManager(self)
            self._nam.finished.connect(self._on_finished)
        return self._nam

    def load(self, src: str, max_width: int = 0, max_height: int = 0) -> None:
        if not src:
            return
        if is_local(src):
            pm = load_local_pixmap(src, max_width, max_height)
            if pm is not None:
                self.loaded.emit(src, pm)
            return
        req = QNetworkRequest(QUrl(src))
        reply = self._nam_instance().get(req)
        reply.setProperty("_w", max_width)
        reply.setProperty("_h", max_height)

    def _on_finished(self, reply: QNetworkReply) -> None:
        try:
            src = reply.url().toString()
            if reply.error() == QNetworkReply.NetworkError.NoError:
                data = reply.readAll()
                pm = QPixmap()
                if pm.loadFromData(data):
                    max_w = int(reply.property("_w") or 0)
                    max_h = int(reply.property("_h") or 0)
                    if max_w > 0 and max_h > 0 and (pm.width() > max_w or pm.height() > max_h):
                        pm = pm.scaled(max_w, max_h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    self.loaded.emit(src, pm)
        except Exception:  # noqa: BLE001
            pass
        finally:
            reply.deleteLater()