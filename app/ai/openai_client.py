"""OpenAIClient：封装 OpenAI 兼容 Chat/Image API（对话 / 视觉 / 文生图）。

来源：从共享库 `../BookerGptTool/BookerGptTool/openai.py` 引入的 `OpenAIClient`，
按桌面客户端需要裁剪（去除工具调用循环与对外部 `util.py`/重型库的依赖），
保留 `call_llm` / `call_llm_retry` / `call_vlm_retry` / `call_tti` / `call_tti_retry`
等调用方法与配置语义，可对接任意 OpenAI 兼容底座（如 gpt-image-1、Qwen、DeepSeek 等）。

本项目所有 LLM / AIGC 调用一律通过本类（见 `app/services/aigc.py`）。
"""
from __future__ import annotations

import base64
import json
import logging
import re
import traceback
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple

import openai
import requests

logger = logging.getLogger(__name__)

logging.getLogger("openai._base_client").setLevel(logging.CRITICAL)
logging.getLogger("httpx").setLevel(logging.CRITICAL)

NO_THINK_EXTRA_BODY = {
    "reasoning_effort": "none",
    "chat_template_kwargs": {
        "enable_thinking": False,
        "thinking_mode": "off",
        "reasoning_effort": "none",
        "reasoning_strength": "none",
    },
}


def request_retry(method, url, retry=10, check_status=False, **kw):
    kw.setdefault("timeout", 10)
    for i in range(retry):
        try:
            r = requests.request(method, url, **kw)
            if check_status:
                r.raise_for_status()
            return r
        except KeyboardInterrupt:
            raise
        except Exception as e:  # noqa: BLE001
            logger.debug("%s retry %s", url, i)
            if i == retry - 1:
                raise e


def json_dump_model(obj: Any) -> str:
    """将对象（含 pydantic 模型）序列化为紧凑 JSON 文本。"""
    if hasattr(obj, "model_dump"):
        obj = obj.model_dump()
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))


def get_msgs_text(msgs) -> str:
    for m in msgs[::-1]:
        cont = m.get("content")
        if isinstance(cont, str):
            return m["content"]
        elif isinstance(cont, list):
            for it in cont:
                if it.get("type") == "text":
                    return it["text"]
    return ""


def repl_ins_token(msgs):
    """改变指令符号的形式（<|x|> → </x/>），避免模型理解出错；返回时还原。"""
    repl = lambda s: re.sub(r"<\|([\w\-\.]+)\|>", r"</\1/>", s)
    for m in msgs:
        cont = m.get("content")
        if isinstance(cont, str):
            m["content"] = repl(cont)
        elif isinstance(cont, list):
            for it in cont:
                tp = it.get("type")
                if tp == "text":
                    it["text"] = repl(it["text"])
    return msgs


def ensure_utf8(text: str) -> str:
    return text.encode("utf8", "ignore").decode("utf8", "ignore")


class OpenAIClient:
    """封装 OpenAI 兼容 API 调用（对话 / 视觉 / 文生图），配置保存在实例上。"""

    def __init__(
        self,
        api_key=None,
        base_url=None,
        user_agent="claude-cli/2.1.41 (external, cli)",
        stream=False,
        timeout=None,
        rpre="",
        no_think=False,
    ):
        self.api_key = api_key
        self.base_url = base_url
        self.user_agent = user_agent
        self.stream = stream
        self.timeout = timeout
        self.rpre = rpre
        self.no_think = no_think

    def _build_client(self) -> openai.OpenAI:
        return openai.OpenAI(
            base_url=self.base_url,
            api_key=self.api_key,
            default_headers={"User-Agent": self.user_agent},
            timeout=self.timeout,
        )

    # ── 对话 ──────────────────────────────────────────
    def call_llm(
        self,
        msgs,
        model_name,
        *,
        temp=None,
        top_p=None,
        frequency_penalty=None,
        presence_penalty=None,
        max_tokens=None,
        extra_body=None,
    ):
        if isinstance(msgs, str):
            msgs = [{"role": "user", "content": msgs}]
        msgs = repl_ins_token(msgs)  # type: ignore[arg-type]
        extra_body = extra_body or {}
        if isinstance(extra_body, str):
            extra_body = json.loads(extra_body)
        if self.no_think:
            extra_body.update(NO_THINK_EXTRA_BODY)
        logger.debug("ques: %s", json_dump_model(get_msgs_text(msgs)))
        sdk = self._build_client()
        res = sdk.chat.completions.create(
            messages=msgs,
            model=model_name,
            temperature=temp,
            top_p=top_p,
            frequency_penalty=frequency_penalty,
            presence_penalty=presence_penalty,
            max_tokens=max_tokens,
            extra_body=extra_body,
            stream=self.stream,
        )
        if self.stream:
            ans, rc = self.collect_stream_content(res)
        else:
            ans = res.choices[0].message.content.strip()
            rc = getattr(res.choices[0].message, "reasoning_content", "").strip()
            self.check_model_repetition(ans)
        if not ans:
            raise ValueError(f"回复为空：{res}")

        ans = re.sub(r"</([\w\-\.]+)/>", r"<|\1|>", ans)
        ans = re.sub(r" thinking[\s\S]+? response", "", ans)
        logger.debug("ans: %s", json_dump_model(ans))
        return ans

    def call_llm_retry(
        self,
        msgs,
        model_name,
        *,
        retry=10,
        temp=None,
        top_p=None,
        frequency_penalty=None,
        presence_penalty=None,
        max_tokens=None,
        extra_body=None,
        parse_output=None,
    ):
        for i in range(retry):
            try:
                res = self.call_llm(
                    msgs,
                    model_name,
                    temp=temp,
                    top_p=top_p,
                    frequency_penalty=frequency_penalty,
                    presence_penalty=presence_penalty,
                    max_tokens=max_tokens,
                    extra_body=extra_body,
                )
                return parse_output(res) if parse_output else res
            except KeyboardInterrupt:
                raise
            except Exception as ex:  # noqa: BLE001
                logger.debug("OpenAI retry %s", i + 1)
                logger.debug(traceback.format_exc())
                if i == retry - 1:
                    raise ex

    def call_vlm_retry(
        self,
        img: bytes,
        ques: str,
        model_name,
        args,
        parse_output=None,
    ):
        """视觉模型：图片（png）base64 + 文本问题。args 须含 retry/temp/top_p 等属性。"""
        img_base64 = base64.b64encode(img).decode("ascii")
        msgs = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": ques},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_base64}"}},
                ],
            }
        ]
        return self.call_llm_retry(
            msgs,
            model_name,
            retry=args.retry,
            temp=args.temp,
            top_p=args.top_p,
            frequency_penalty=args.frequency_penalty,
            presence_penalty=args.presence_penalty,
            max_tokens=args.max_tokens,
            extra_body=args.extra_body,
            parse_output=parse_output,
        )

    # ── 文生图 ────────────────────────────────────────
    def call_tti(
        self,
        text,
        model_name,
        size="1024x1024",
        ref_img: Optional[bytes] = None,
    ):
        logger.debug("tti: %s", json_dump_model(text))
        sdk = self._build_client()
        extra_body: dict = {}
        if "gpt-image" in model_name and ref_img:
            ref_img_b64 = base64.b64encode(ref_img).decode("ascii")
            extra_body = {"image": f"data:image/png;base64,{ref_img_b64}"}
        img_data = sdk.images.generate(
            model=model_name,
            size=size,
            prompt=text,
            response_format="b64_json",
            n=1,
            extra_body=extra_body,
        ).data[0]
        if getattr(img_data, "b64_json", None):
            return base64.b64decode(img_data.b64_json)
        elif getattr(img_data, "url", None):
            return request_retry("GET", img_data.url).content
        else:
            raise ValueError("API 未返回数据")

    def call_tti_retry(
        self,
        text,
        model_name,
        size="1024x1024",
        ref_img: Optional[bytes] = None,
        retry=10,
        nothrow=True,
    ):
        for i in range(retry):
            try:
                return self.call_tti(text, model_name, size, ref_img)
            except KeyboardInterrupt:
                raise
            except Exception as ex:  # noqa: BLE001
                logger.debug("OpenAI retry %s: %s", i + 1, ex)
                if i == retry - 1 and not nothrow:
                    raise ex

    # ── 流式 / 重复检测 ───────────────────────────────
    def collect_stream_content(self, resp: Iterable) -> Tuple[str, str]:
        content: List[str] = []
        rc: List[str] = []
        for chunk in resp:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            delta_content = delta.content
            delta_rc = getattr(delta, "reasoning_content", "")
            if delta_content:
                content.append(delta_content)
                self.check_model_repetition("".join(content))
            if delta_rc:
                rc.append(delta_rc)
                self.check_model_repetition("".join(rc))
        return "".join(content), "".join(rc)

    def check_model_repetition(self, text: str) -> None:
        if self.rpre and re.search(self.rpre, text):
            raise ValueError("检测到模型复读")