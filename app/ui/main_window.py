"""主窗口：侧边导航 + 顶栏 + 页面栈 + Toast 浮层。"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QMainWindow, QStackedWidget, QVBoxLayout, QWidget

from .context import AppContext
from .pages.account import AccountPage
from .pages.history import HistoryPage
from .pages.home import HomePage
from .pages.result import ResultPage
from .pages.workspace import WorkspacePage
from .toast import ToastManager
from .widgets import Sidebar, TopBar

_PAGE_TITLES = {
    "home": "AI 展示面大师",
    "workspace": "生成",
    "result": "生成结果",
    "history": "生成记录",
    "account": "我的",
}


class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("AI 展示面大师")
        self.resize(1000, 720)
        self.setMinimumSize(860, 620)

        central = QWidget()
        central.setObjectName("root")
        outer = QVBoxLayout(central)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # 顶栏
        self.topbar = TopBar()
        outer.addWidget(self.topbar)

        # 主体
        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)

        self.sidebar = Sidebar()
        self.sidebar.navigate.connect(self.navigate)
        body.addWidget(self.sidebar)

        self.stack = QStackedWidget()
        body.addWidget(self.stack, 1)
        outer.addLayout(body)

        self.setCentralWidget(central)

        # Toast 浮层（覆盖内容区，鼠标穿透）
        self.toast_overlay = QWidget(self)
        self.toast_overlay.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.toast_overlay.setAttribute(Qt.WA_StyledBackground, True)
        self.toast = ToastManager(self.toast_overlay)

        # 上下文
        self.ctx = AppContext(
            window=self,
            toast=self.toast,
            navigate=self.navigate,
        )

        # 页面
        self.pages = {
            "home": HomePage(self.ctx),
            "workspace": WorkspacePage(self.ctx),
            "result": ResultPage(self.ctx),
            "history": HistoryPage(self.ctx),
            "account": AccountPage(self.ctx),
        }
        for p in self.pages.values():
            self.stack.addWidget(p)

        self.navigate("home")

    # ---------------- 导航 ----------------
    def navigate(self, key: str, *args) -> None:
        if key not in self.pages:
            key = "home"
        page = self.pages[key]
        if key == "result" and args:
            page.load(int(args[0]))
        self.stack.setCurrentWidget(page)
        self.sidebar.set_active(key)
        self.topbar.set_title(_PAGE_TITLES.get(key, "AI 展示面大师"))

    def resizeEvent(self, event) -> None:  # noqa: D102
        super().resizeEvent(event)
        self.toast_overlay.setGeometry(self.sidebar.width(), 0, self.width() - self.sidebar.width(), self.height())