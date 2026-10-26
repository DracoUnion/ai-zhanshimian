"""Toast 轻提示：顶部居中浮层，自动淡出。"""
from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, Qt, QTimer
from PySide6.QtWidgets import QGraphicsOpacityEffect, QLabel, QWidget

from ui.theme import ACCENT_DIM, BORDER, DANGER, OK, SURFACE_2, TEXT

_KIND_STYLE = {
    "info": f"color:{TEXT}; background:{SURFACE_2}; border:1px solid {BORDER};",
    "success": f"color:{OK}; background:{SURFACE_2}; border:1px solid rgba(124,192,124,0.4);",
    "error": f"color:{DANGER}; background:{SURFACE_2}; border:1px solid rgba(224,106,106,0.4);",
    "gold": f"color:#f0d48a; background:{SURFACE_2}; border:1px solid {ACCENT_DIM};",
}


class ToastManager:
    """附着在 overlay 上展示 toast 的简单管理器。"""

    def __init__(self, parent: QWidget):
        self.parent = parent
        self._active: list[QLabel] = []

    def show(self, text: str, kind: str = "info", ms: int = 2200) -> None:
        label = QLabel(text, self.parent)
        label.setAlignment(Qt.AlignCenter)
        label.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        label.setStyleSheet(
            f"border-radius:999px; padding:10px 18px; font-size:13px; {_KIND_STYLE.get(kind, _KIND_STYLE['info'])}"
        )
        label.adjustSize()
        label.setAttribute(Qt.WA_StyledBackground, True)
        label.setWordWrap(False)
        label.setFixedWidth(min(label.width() + 24, self.parent.width() - 40))
        opacity = QGraphicsOpacityEffect(label)
        label.setGraphicsEffect(opacity)

        self._relayout()
        label.show()
        self._active.append(label)

        anim = QPropertyAnimation(opacity, b"opacity", label)
        anim.setDuration(240)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.OutCubic)
        anim.start(QPropertyAnimation.DeleteWhenStopped)

        def _fade_and_remove():
            self._active.remove(label)
            label.deleteLater()
            self._relayout()

        QTimer.singleShot(ms, lambda: _fade_out(label, _fade_and_remove))

    def _relayout(self) -> None:
        y = 12
        for lab in self._active:
            x = (self.parent.width() - lab.width()) // 2
            lab.move(x, y)
            y += lab.height() + 8


def _fade_out(label: QLabel, done) -> None:
    effect = label.graphicsEffect()
    if not isinstance(effect, QGraphicsOpacityEffect):
        label.hide()
        done()
        return
    anim = QPropertyAnimation(effect, b"opacity", label)
    anim.setDuration(200)
    anim.setStartValue(1.0)
    anim.setEndValue(0.0)
    anim.setEasingCurve(QEasingCurve.InCubic)
    anim.finished.connect(done)
    anim.start(QPropertyAnimation.DeleteWhenStopped)