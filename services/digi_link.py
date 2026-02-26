# services/digi_link.py
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time


def _b64url_encode(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).decode("utf-8").rstrip("=")


def make_payload(secret: str, target_user_id: int, amount_digi: int, ttl_sec: int) -> str:
    """
    Возвращает payload вида: <body>.<sig>
    body = base64url(json)
    sig  = hex(hmac_sha256(secret, body))

    Внутри json:
      v   - версия
      uid - target user id (в другом боте)
      amt - сумма DIGI
      exp - unix time expiry
      n   - nonce (одноразовость)
    """
    now = int(time.time())
    data = {
        "v": 1,
        "uid": int(target_user_id),
        "amt": int(amount_digi),
        "exp": now + int(ttl_sec),
        "n": secrets.token_urlsafe(10),
    }

    body = _b64url_encode(json.dumps(data, separators=(",", ":"), ensure_ascii=False).encode("utf-8"))
    sig = hmac.new(secret.encode("utf-8"), body.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{body}.{sig}"


def make_tg_link(partner_username: str, payload: str) -> str:
    """
    Ссылка, которую пользователь вставит в другой бот.
    """
    u = (partner_username or "").strip().lstrip("@")
    return f"https://t.me/{u}?start=digi_{payload}"
