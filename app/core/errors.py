"""业务错误码与统一业务异常（与 doc/design-detail.md 错误码表一致）。"""
from __future__ import annotations


class ErrCode:
    # 认证
    UNAUTHORIZED = 1001
    TOKEN_EXPIRED = 1002
    FORBIDDEN = 1003
    # 短信 / 登录
    SMS_TOO_FREQUENT = 1101
    SMS_CODE_INVALID = 1102
    # 生成
    BALANCE_INSUFFICIENT = 1201
    GENERATION_NOT_FOUND = 1202
    GENERATION_STATUS_INVALID = 1203
    UPLOAD_INVALID = 1204
    QUANTITY_INVALID = 1205
    FEATURE_LOCKED = 1206
    # 支付
    ORDER_NOT_FOUND = 1301
    ORDER_STATUS_INVALID = 1302
    # 通用
    PARAM_INVALID = 1400


class BizError(Exception):
    """业务异常：携带业务码 + HTTP 状态码，统一由异常处理器转 JSON。"""

    def __init__(self, code: int, message: str, *, data=None, status_code: int = 400):
        self.code = code
        self.message = message
        self.data = data
        self.status_code = status_code
        super().__init__(message)