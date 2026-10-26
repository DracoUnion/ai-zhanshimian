"""首页（落地页）。"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout

from ..widgets import banner_label
from .base import ScrollPage

STEPS = [
    ("01", "上传一张正面自拍", "不改变五官，只优化穿搭、光线与场景"),
    ("02", "选择喜欢的风格", "海边、咖啡厅、健身房… 多款氛围可选"),
    ("03", "AI 生成展示面", "约 1 元/张，成功后才扣次数"),
]


class HomePage(ScrollPage):
    def __init__(self, ctx, parent=None):
        super().__init__(parent)
        self.ctx = ctx

        # ---- 首屏 Hero ----
        hero = QFrame()
        hero.setStyleSheet(
            "background:qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(216,178,95,0.22), stop:0.7 #0b0910);"
            " border:none; border-radius:0;"
        )
        hy = QVBoxLayout(hero)
        hy.setContentsMargins(16, 30, 16, 26)
        hy.setSpacing(12)
        hy.setAlignment(Qt.AlignHCenter)

        badge = banner_label("先免费生成 1 张", "gold")
        badge.setFixedWidth(120)
        hy.addWidget(badge, 0, Qt.AlignCenter)

        title = QLabel("普通男生，也能有\n让人多看一眼的照片")
        title.setProperty("class", "hero")
        title.setAlignment(Qt.AlignCenter)
        hy.addWidget(title)

        sub = QLabel("手机相册全是工作截图？让 AI 帮你把一张自拍，变成自带氛围感的社交展示面。")
        sub.setProperty("class", "hero-note")
        sub.setAlignment(Qt.AlignCenter)
        sub.setWordWrap(True)
        hy.addWidget(sub)

        go = QPushButton("免费生成一张 →")
        go.setProperty("class", "gold")
        go.setFixedWidth(180)
        go.clicked.connect(lambda: self.ctx.navigate("workspace"))
        hy.addWidget(go, 0, Qt.AlignCenter)

        notes = QHBoxLayout()
        for t in ("无需会拍照", "无需懂 AI", "手机就能用"):
            n = QLabel(t)
            n.setProperty("class", "faint")
            notes.addWidget(n)
        hy.addLayout(notes)

        self.body.addWidget(hero)

        # ---- 三步 ----
        how = QFrame()
        how.setProperty("card", True)
        hly = QVBoxLayout(how)
        hly.setContentsMargins(18, 18, 18, 18)
        hly.setSpacing(14)
        htitle = QLabel("三步获得展示面")
        htitle.setProperty("class", "section")
        hly.addWidget(htitle)
        for no, t, d in STEPS:
            row = QHBoxLayout()
            row.setSpacing(12)
            lab = QLabel(no)
            lab.setProperty("class", "step-no")
            col = QVBoxLayout()
            tlab = QLabel(t)
            tlab.setProperty("class", "step-t")
            dlab = QLabel(d)
            dlab.setProperty("class", "muted")
            col.addWidget(tlab)
            col.addWidget(dlab)
            row.addWidget(lab)
            row.addLayout(col)
            row.addStretch(1)
            hly.addLayout(row)
        self.body.addWidget(how)

        # ---- 定价 teaser ----
        teaser = QFrame()
        teaser.setProperty("card", True)
        tly = QVBoxLayout(teaser)
        tly.setContentsMargins(18, 18, 18, 18)
        tly.setSpacing(10)
        tfree = banner_label("先体验 · 再付费", "gold")
        tfree.setFixedWidth(110)
        tly.addWidget(tfree, 0, Qt.AlignCenter)
        price = QLabel("¥69 解锁全部功能")
        price.setProperty("class", "h2")
        price.setAlignment(Qt.AlignCenter)
        tly.addWidget(price)
        pnote = QLabel("约 1 元/张 · 用完按需充值 · 失败自动退回")
        pnote.setProperty("class", "muted")
        pnote.setAlignment(Qt.AlignCenter)
        tly.addWidget(pnote)
        tp = QPushButton("查看套餐")
        tp.setProperty("class", "ghost")
        tp.setFixedWidth(140)
        tp.clicked.connect(lambda: self.ctx.navigate("pricing"))
        tly.addWidget(tp, 0, Qt.AlignCenter)
        self.body.addWidget(teaser)