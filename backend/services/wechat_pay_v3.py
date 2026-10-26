"""微信支付 API v3 客户端（下单 + 回调验签/解密）。

生产使用方式：
  PAYMENT_MODE=wechat
  WECHAT_APPID / WECHAT_MCHID / WECHAT_API_V3_KEY / WECHAT_PRIVATE_KEY_PATH / WECHAT_SERIAL_NO / WECHAT_NOTIFY_URL
  （可选 WECHAT_PLATFORM_CERT_PATH 开启回调响应验签）

未配置真实商户时默认走 mock（见 payment.py）。
"""
from __future__ import annotations

import base64
import json
import time
import uuid

import httpx
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

BASE_URL = "https://api.mch.weixin.qq.com"


class WechatPayV3Error(RuntimeError):
    pass


class WechatPayV3Client:
    def __init__(self, settings):
        self.mchid = settings.wechat_mchid
        self.appid = settings.wechat_appid
        self.api_v3_key = settings.wechat_api_v3_key
        self.notify_url = settings.wechat_notify_url
        self.serial_no = settings.wechat_serial_no
        with open(settings.wechat_private_key_path, "rb") as f:
            self._private_key = serialization.load_pem_private_key(f.read(), password=None)
        self._platform_cert_path = settings.wechat_platform_cert_path

    # ---------- 请求签名与下单 ----------
    def _auth_header(self, method: str, path: str, body: str):
        timestamp = str(int(time.time()))
        nonce = uuid.uuid4().hex
        message = f"{method}\n{path}\n{timestamp}\n{nonce}\n{body}\n".encode()
        signature = self._private_key.sign(message, padding.PKCS1v15(), hashes.SHA256())
        b64 = base64.b64encode(signature).decode()
        return (
            f'WECHATPAY2-SHA256-RSA2048 mchid="{self.mchid}",nonce_str="{nonce}",'
            f'timestamp="{timestamp}",serial_no="{self.serial_no}",signature="{b64}"'
        )

    def _post(self, path: str, payload: dict) -> dict:
        body = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        auth = self._auth_header("POST", path, body)
        resp = httpx.post(
            BASE_URL + path,
            data=body.encode("utf-8"),
            headers={"Authorization": auth, "Content-Type": "application/json", "Accept": "application/json"},
            timeout=10,
        )
        if resp.status_code >= 300:
            raise WechatPayV3Error(f"微信支付下单失败 {resp.status_code}: {resp.text}")
        return resp.json()

    def create_native(self, order_no: str, amount_fen: int, description: str) -> str:
        data = self._post(
            "/v3/pay/transactions/native",
            {
                "appid": self.appid,
                "mchid": self.mchid,
                "description": description,
                "out_trade_no": order_no,
                "notify_url": self.notify_url,
                "amount": {"total": amount_fen, "currency": "CNY"},
            },
        )
        return data.get("code_url", "")

    def create_h5(self, order_no: str, amount_fen: int, description: str, client_ip: str = "127.0.0.1") -> str:
        data = self._post(
            "/v3/pay/transactions/h5",
            {
                "appid": self.appid,
                "mchid": self.mchid,
                "description": description,
                "out_trade_no": order_no,
                "notify_url": self.notify_url,
                "amount": {"total": amount_fen, "currency": "CNY"},
                "scene_info": {"payer_client_ip": client_ip, "h5_info": {"type": "Wap"}},
            },
        )
        return data.get("h5_url", "")

    # ---------- 回调验签/解密 ----------
    def verify_and_decrypt(self, headers: dict, body: bytes) -> dict:
        if self._platform_cert_path:
            self._verify_notify_signature(headers, body)
        payload = json.loads(body)
        resource = payload.get("resource", {})
        key = self.api_v3_key.encode("utf-8")
        nonce = resource.get("nonce", "").encode("utf-8")
        ciphertext = base64.b64decode(resource.get("ciphertext", ""))
        associated = (resource.get("associated_data") or "").encode("utf-8")
        plain = AESGCM(key).decrypt(nonce, ciphertext, associated)
        return json.loads(plain)

    def _verify_notify_signature(self, headers: dict, body: bytes) -> None:
        from cryptography import x509

        with open(self._platform_cert_path, "rb") as f:
            cert = x509.load_pem_x509_certificate(f.read())
        signature = base64.b64decode(headers.get("Wechatpay-Signature", ""))
        message = f"{headers.get('Wechatpay-Timestamp', '')}\n{headers.get('Wechatpay-Nonce', '')}\n{body.decode('utf-8')}\n".encode()
        public_key = cert.public_key()
        try:
            public_key.verify(signature, message, padding.PKCS1v15(), hashes.SHA256())
        except Exception:
            raise WechatPayV3Error("微信回调验签失败")