"""主题：黑金暗色设计令牌 + QSS（对标原前端 theme.css/app.css）。"""
from __future__ import annotations

from PySide6.QtGui import QColor
from PySide6.QtWidgets import QApplication

BG = "#0b0910"
BG_SOFT = "#100d17"
SURFACE = "#161220"
SURFACE_2 = "#1e1830"
BORDER = "rgba(255,255,255,0.08)"
TEXT = "#f4f1ea"
TEXT_DIM = "#a79f90"
TEXT_FAINT = "#6f675c"
ACCENT = "#d8b25f"
ACCENT_BRIGHT = "#f0d48a"
ACCENT_DIM = "rgba(216,178,95,0.14)"
DANGER = "#e06a6a"
OK = "#7cc07c"


def hex_alpha(hex_color: str, alpha: int) -> str:
    c = QColor(hex_color)
    return f"rgba({c.red()},{c.green()},{c.blue()},{alpha})"


QSS = f"""
* {{
    font-family: "Microsoft YaHei UI", "PingFang SC", "Segoe UI", "Noto Sans CJK SC", sans-serif;
    font-size: 14px;
}}
QMainWindow, QDialog {{
    background-color: {BG};
}}
QWidget {{
    color: {TEXT};
    background: transparent;
}}
QScrollArea {{
    border: none;
    background: transparent;
}}
QScrollBar:vertical {{
    background: transparent; width: 10px; margin: 2px;
}}
QScrollBar::handle:vertical {{
    background: {hex_alpha("#ffffff", 26)};
    border-radius: 5px; min-height: 30px;
}}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; width: 0; }}
QScrollBar:horizontal {{ background: transparent; height: 10px; }}
QScrollBar::handle:horizontal {{
    background: {hex_alpha("#ffffff", 26)}; border-radius: 5px; min-width: 30px;
}}

/* ---------- 通用卡片 ---------- */
QFrame[card="true"] {{
    background-color: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 16px;
}}
QFrame[accent-card="true"] {{
    background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {hex_alpha(ACCENT, 36)}, stop:0.35 {SURFACE}, stop:1 {SURFACE});
    border: 1.5px solid {ACCENT_DIM};
    border-radius: 16px;
}}
QFrame[soft="true"] {{
    background-color: {SURFACE_2};
    border: 1px solid {BORDER};
    border-radius: 12px;
}}

/* ---------- 按钮 ---------- */
QPushButton {{
    border: 1px solid transparent;
    border-radius: 999px;
    padding: 9px 20px;
    font-weight: 600;
    background: {SURFACE_2};
    border-color: {BORDER};
}}
QPushButton:hover {{ background: {hex_alpha("#3a3152", 120)}; }}
QPushButton:pressed {{ padding-top: 10px; padding-bottom: 8px; }}
QPushButton:disabled {{ opacity: 0.45; }}

QPushButton[class="gold"] {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {ACCENT}, stop:1 {ACCENT_BRIGHT});
    color: #1c1505;
}}
QPushButton[class="gold"]:hover {{ background: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 {ACCENT_BRIGHT}, stop:1 {hex_alpha(ACCENT_BRIGHT, 220)}); }}

QPushButton[class="ghost"] {{
    background: {SURFACE_2};
    border: 1px solid {BORDER};
    color: {TEXT};
}}
QPushButton[class="ghost"]:hover {{ background: {hex_alpha("#3a3152", 120)}; }}

QPushButton[class="ghost"]:disabled, QPushButton[class="gold"]:disabled {{
    background: {SURFACE_2}; color: {TEXT_FAINT};
}}

QPushButton[block="true"] {{
    width: 100%;
    padding: 12px 20px;
    font-size: 15px;
}}

QPushButton[chip="true"] {{
    border-radius: 999px;
    padding: 6px 14px;
    font-size: 13px;
    font-weight: 500;
    background: {SURFACE_2};
    border: 1px solid {BORDER};
    color: {TEXT_DIM};
}}
QPushButton[chip="true"]:hover {{ color: {ACCENT_BRIGHT}; background: {ACCENT_DIM}; }}
QPushButton[chip="true"]:checked {{
    background: {ACCENT_DIM};
    border: 1px solid {hex_alpha(ACCENT, 120)};
    color: {ACCENT_BRIGHT};
}}

QPushButton[nav="true"] {{
    border-radius: 12px;
    padding: 11px 18px;
    font-size: 14px;
    text-align: left;
    background: transparent;
    border: none;
    color: {TEXT_FAINT};
    font-weight: 500;
}}
QPushButton[nav="true"]:hover {{ background: {ACCENT_DIM}; color: {TEXT_DIM}; }}
QPushButton[nav="true"]:checked {{
    background: {ACCENT_DIM};
    color: {ACCENT_BRIGHT};
    font-weight: 700;
}}

QPushButton[icon-only="true"] {{
    border-radius: 12px; padding: 8px; background: transparent; border: none;
}}

/* ---------- 输入 ---------- */
QLineEdit, QTextEdit, QPlainTextEdit {{
    background-color: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 12px;
    padding: 11px 14px;
    color: {TEXT};
    selection-background-color: {ACCENT_DIM};
}}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
    border-color: {ACCENT};
}}
QLineEdit::placeholder, QTextEdit::placeholder {{
    color: {TEXT_FAINT};
}}

/* chips 样式按钮（模板/提示词快捷词） */
QPushButton[chipcard="true"] {{
    border: 1px solid {BORDER};
    background: {SURFACE_2};
    border-radius: 12px;
    padding: 7px 14px;
    font-size: 13px;
    color: {TEXT_DIM};
}}
QPushButton[chipcard="true"]:hover {{ color: {ACCENT_BRIGHT}; }}
QPushButton[chipcard="true"]:checked {{
    background: {ACCENT_DIM};
    border: 1px solid {ACCENT};
    color: {ACCENT_BRIGHT};
}}

QPushButton[template="true"] {{
    border: 1.5px solid {BORDER};
    background: {SURFACE_2};
    border-radius: 12px;
    padding: 0;
    color: {TEXT};
}}
QPushButton[template="true"]:checked {{
    border: 1.5px solid {ACCENT};
    background: {hex_alpha(ACCENT, 22)};
}}

QPushButton[qty="true"] {{
    border: 1.5px solid {BORDER};
    background: {SURFACE_2};
    border-radius: 12px;
    padding: 12px 8px;
    color: {TEXT};
}}
QPushButton[qty="true"]:checked {{
    border: 1.5px solid {ACCENT};
    background: {ACCENT_DIM};
}}

/* ---------- 标签 ---------- */
QLabel[class="section"] {{
    font-size: 15px; font-weight: 700; color: {TEXT};
}}
QLabel[class="muted"] {{
    color: {TEXT_DIM}; font-size: 13px;
}}
QLabel[class="faint"] {{
    color: {TEXT_FAINT}; font-size: 12px;
}}
QLabel[class="title"] {{
    font-size: 27px; font-weight: 800;
}}
QLabel[class="h2"] {{
    font-size: 22px; font-weight: 800;
}}
QLabel[class="money"] {{
    font-size: 40px; font-weight: 800; color: {ACCENT_BRIGHT};
}}
QLabel[class="accent"] {{ color: {ACCENT_BRIGHT}; }}
QLabel[class="ok"] {{ color: {OK}; font-size: 12px; }}
QLabel[class="danger"] {{ color: {DANGER}; font-size: 12px; }}
QLabel[class="brand"] {{
    font-size: 16px; font-weight: 700; color: {TEXT};
}}
QLabel[class="hero"] {{
    font-size: 27px; font-weight: 800; color: {TEXT};
}}
QLabel[class="hero-note"] {{
    color: {TEXT_DIM}; font-size: 14px;
}}
QLabel[badge="true"] {{
    border-radius: 999px;
    padding: 3px 10px;
    background: {SURFACE_2};
    font-size: 11px;
    color: {TEXT_DIM};
}}
QLabel[badge="ok"] {{
    border-radius: 999px;
    padding: 3px 10px;
    font-size: 11px;
    color: {OK};
    background: {hex_alpha("#7cc07c", 20)};
}}
QLabel[badge="danger"] {{
    border-radius: 999px;
    padding: 3px 10px;
    font-size: 11px;
    color: {DANGER};
    background: {hex_alpha("#e06a6a", 22)};
}}
QLabel[badge="gold"] {{
    border-radius: 999px;
    padding: 3px 10px;
    font-size: 11px;
    color: {ACCENT_BRIGHT};
    background: {ACCENT_DIM};
    border: 1px solid {ACCENT_DIM};
}}

/* ---------- 列表行 / 历史项 ---------- */
QFrame[listrow="true"] {{
    background: {SURFACE_2};
    border: 1px solid {BORDER};
    border-radius: 12px;
}}
QLabel[class="step-no"] {{
    color: {ACCENT}; font-size: 14px; font-weight: 800;
}}
QLabel[class="step-t"] {{
    font-weight: 600; font-size: 14px;
}}

/* ---------- 弹窗 ---------- */
QDialog {{
    background-color: {SURFACE};
    border: 1px solid {BORDER};
}}
QFrame[dialog="true"] {{
    background-color: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 20px;
}}

/* ---------- 分隔线 ---------- */
QFrame[hr="true"] {{
    background-color: {BORDER};
    border: none;
    max-height: 1px;
}}

/* ---------- 顶栏 ---------- */
QFrame[topbar="true"] {{
    background-color: {hex_alpha(BG, 235)};
    border-bottom: 1px solid {BORDER};
}}
QFrame[sidebar="true"] {{
    background-color: {BG_SOFT};
    border-right: 1px solid {BORDER};
}}
QFrame[statusbar="true"] {{
    background-color: {SURFACE};
    border-radius: 999px;
    padding: 5px 12px;
}}
"""


def apply_theme(app: QApplication) -> None:
    app.setStyleSheet(QSS)