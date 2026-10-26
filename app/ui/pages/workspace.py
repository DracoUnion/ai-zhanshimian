"""生成工作台：上传自拍 → 选风格 → 提示词 → 张数 → 生成。"""

from __future__ import annotations

import uuid

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from app.services import facade as svc

from app.ui.components.upload_card import UploadCard
from app.ui.template_picker import TemplatePicker
from app.ui.worker import call_error_message, run_in_worker
from app.ui.pages.base import ScrollPage

PROMPT_PRESETS = ["日系", "商务", "运动", "文艺", "都市"]
QTY_OPTIONS = [(1, "单张"), (6, "成组"), (12, "系列出图")]


class WorkspacePage(ScrollPage):
    def __init__(self, ctx, parent=None):
        super().__init__(parent)
        self.ctx = ctx
        self.selfie_key: str | None = None
        self.reference_key: str | None = None
        self.template_id: int | None = None
        self.prompt = ""
        self.quantity = 1
        self._submitting = False

        # 1. 上传自拍
        card, card_lay, _ = self._section("1. 上传自拍", "正面清晰、五官可见")

        row = QHBoxLayout()
        row.setSpacing(10)
        self.selfie_card = UploadCard("自拍原图", "点此上传", "selfie", ctx)
        self.selfie_card.changed.connect(self._on_selfie)
        self.reference_card = UploadCard("风格参考（选填）", "喜欢的穿搭/场景照", "reference", ctx)
        self.reference_card.changed.connect(self._on_reference)
        row.addWidget(self.selfie_card)
        row.addWidget(self.reference_card)
        row.addStretch(1)
        card_lay.addLayout(row)
        self.body.addWidget(card)

        # 2. 风格模板
        self.template_card, self.template_lay, _ = self._section("选择风格", "先选氛围，再看提示词")
        self._template_loading = QLabel("加载模板中…")
        self._template_loading.setProperty("class", "muted")
        self.template_lay.addWidget(self._template_loading)
        self.body.addWidget(self.template_card)
        self.template_picker: TemplatePicker | None = None

        # 3. 提示词
        prompt_card, prompt_lay, _ = self._section("提示词", "越具体越接近你想要的氛围")
        chips = QHBoxLayout()
        chips.setSpacing(8)
        chips.setContentsMargins(0, 0, 0, 0)
        self.prompt_chips: dict[str, QPushButton] = {}
        for p in PROMPT_PRESETS:
            b = QPushButton(p)
            b.setProperty("chipcard", True)
            b.clicked.connect(lambda _=False, kw=p: self._chip(kw))
            self.prompt_chips[p] = b
            chips.addWidget(b)
        chips.addStretch(1)
        prompt_lay.addLayout(chips)
        self.prompt_edit = QTextEdit()
        self.prompt_edit.setPlaceholderText("补充穿搭、光线、场景细节…")
        self.prompt_edit.setFixedHeight(96)
        self.prompt_edit.textChanged.connect(self._on_prompt_change)
        prompt_lay.addWidget(self.prompt_edit)
        self.count_label = QLabel("0/120")
        self.count_label.setProperty("class", "faint")
        self.count_label.setAlignment(Qt.AlignRight)
        prompt_lay.addWidget(self.count_label)
        self.body.addWidget(prompt_card)

        # 4. 张数
        qty_card, qty_lay, _ = self._section("生成张数", "免费无限次，每次可生成一组")
        qrow = QHBoxLayout()
        qrow.setSpacing(10)
        self.qty_buttons: dict[int, QPushButton] = {}
        for n, note in QTY_OPTIONS:
            b = QPushButton(f"{n} 张\n{note}")
            b.setProperty("qty", True)
            b.setCheckable(True)
            b.setFixedSize(150, 64)
            b.clicked.connect(lambda _=False, qn=n: self._set_qty(qn))
            self.qty_buttons[n] = b
            qrow.addWidget(b)
        self.qty_buttons[1].setChecked(True)
        qrow.addStretch(1)
        qty_lay.addLayout(qrow)
        self.body.addWidget(qty_card)

        # 5. 生成条
        bar = QFrame()
        bar.setStyleSheet("background:transparent;")
        bly = QVBoxLayout(bar)
        bly.setContentsMargins(0, 6, 0, 0)
        bly.setSpacing(8)
        self.go_btn = QPushButton("免费生成")
        self.go_btn.setProperty("class", "gold")
        self.go_btn.setProperty("block", True)
        self.go_btn.clicked.connect(self._submit)
        bly.addWidget(self.go_btn)
        self.status_note = QLabel("")
        self.status_note.setProperty("class", "muted")
        self.status_note.setAlignment(Qt.AlignCenter)
        bly.addWidget(self.status_note)
        self.body.addWidget(bar)

        self._load_templates()

    # ---------- 构建辅助 ----------
    def _section(self, title: str, sub: str = ""):
        card = QFrame()
        card.setProperty("card", True)
        lay = QVBoxLayout(card)
        lay.setContentsMargins(16, 16, 16, 16)
        lay.setSpacing(10)
        row = QHBoxLayout()
        row.setSpacing(8)
        t = QLabel(title)
        t.setProperty("class", "section")
        row.addWidget(t)
        if sub:
            s = QLabel(sub)
            s.setProperty("class", "muted")
            row.addWidget(s)
        row.addStretch(1)
        lay.addLayout(row)
        return card, lay, t

    # ---------- 模板 ----------
    def _load_templates(self) -> None:
        run_in_worker(
            svc.templates,
            lambda items: self._render_templates(items),
            lambda e: self._template_loading.setText(call_error_message(e)),
        )

    def _render_templates(self, items: list[dict]) -> None:
        self._template_loading.hide()
        from app.schemas.template import TemplateOut

        templates = [TemplateOut(**it) for it in items]
        self.template_picker = TemplatePicker(templates)
        self.template_picker.selected.connect(self._pick_template)
        self.template_lay.addWidget(self.template_picker)
        self._update_ready()

    def _pick_template(self, template_id: int) -> None:
        if self.template_picker is None:
            return
        if self.template_picker.value() == template_id:
            self.template_id = None
            self.template_picker.select(None)
        else:
            self.template_id = template_id
            self.template_picker.select(template_id)
            for t in self.template_picker.templates:
                if t.id == template_id:
                    self.prompt_edit.setPlainText(t.prompt_template)
                    break
        self._update_ready()

    def _chip(self, keyword: str) -> None:
        cur = self.prompt.strip()
        if cur:
            new = f"{cur}，{keyword}风格"
        else:
            new = f"{keyword}风格，自然不做作"
        self.prompt_edit.setPlainText(new)

    def _on_prompt_change(self) -> None:
        self.prompt = self.prompt_edit.toPlainText()
        self.count_label.setText(f"{len(self.prompt)}/120")
        self._update_ready()
        if self.template_picker and self.prompt and self.prompt != next(
            (t.prompt_template for t in self.template_picker.templates if t.id == self.template_id), ""
        ):
            self.template_picker.select(None)

    def _set_qty(self, n: int) -> None:
        self.quantity = n
        for k, b in self.qty_buttons.items():
            b.setChecked(k == n)

    def _on_selfie(self, key: str, _view: str) -> None:
        self.selfie_key = key
        self._update_ready()

    def _on_reference(self, key: str, _view: str) -> None:
        self.reference_key = key

    def _ready(self) -> bool:
        return bool(self.selfie_key) and (self.template_id is not None or bool(self.prompt.strip()))

    def _update_ready(self) -> None:
        self.go_btn.setEnabled(self._ready() and not self._submitting)
        self.status_note.setText("免费无限次生成 · 成功才出图，失败请重试")

    # ---------- 提交 ----------
    def _submit(self) -> None:
        if self._submitting:
            return
        if not self.selfie_key:
            self.ctx.toast.show("先上传一张自拍", "error")
            return
        self._do_create()

    def _do_create(self) -> None:
        self._submitting = True
        self.go_btn.setEnabled(False)
        self.go_btn.setText("提交中…")

        def _done(result: dict) -> None:
            self._submitting = False
            self.ctx.navigate("result", int(result["generation_id"]))

        def _fail(err) -> None:
            self._submitting = False
            self.go_btn.setEnabled(self._ready())
            self.ctx.toast.show(call_error_message(err), "error")
            self._update_ready()

        run_in_worker(
            svc.create_generation,
            _done,
            _fail,
            selfie_key=self.selfie_key,
            reference_key=self.reference_key,
            template_id=self.template_id,
            prompt=self.prompt,
            quantity=self.quantity,
            idempotency_key=uuid.uuid4().hex,
        )