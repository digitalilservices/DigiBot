# services/webapp_server.py
from __future__ import annotations

import hmac
import hashlib
import json
import random
import time
import logging
from pathlib import Path
from urllib.parse import parse_qsl

from aiohttp import web

from database import Database


def _check_telegram_init_data(init_data: str, bot_token: str, max_age_sec: int = 24 * 3600) -> dict | None:
    if not init_data:
        return None

    try:
        # Мягкий парсинг (на iOS/Telegram иногда strict ломается)
        pairs = dict(parse_qsl(init_data, strict_parsing=False, keep_blank_values=True))
    except Exception:
        return None

    hash_received = pairs.pop("hash", None)
    if not hash_received:
        return None

    try:
        auth_date = int(pairs.get("auth_date", "0"))
        if auth_date <= 0:
            return None
        if int(time.time()) - auth_date > int(max_age_sec):
            return None
    except Exception:
        return None

    data_check_string = "\n".join(f"{k}={pairs[k]}" for k in sorted(pairs.keys()))
    secret_key = hmac.new(b"WebAppData", bot_token.encode("utf-8"), hashlib.sha256).digest()
    hash_calc = hmac.new(secret_key, data_check_string.encode("utf-8"), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(hash_calc, hash_received):
        return None

    try:
        user_obj = json.loads(pairs.get("user", "{}"))
    except Exception:
        user_obj = {}

    return {"pairs": pairs, "user": user_obj}


def _weighted_choice(values: list[float], probs: list[float]) -> float:
    r = random.random()
    acc = 0.0
    for v, p in zip(values, probs):
        acc += float(p)
        if r <= acc:
            return float(v)
    return float(values[-1])


# ---------------- Game settings ----------------
WHEEL_COST = 1.0
WHEEL_VALUES = [100, 250, 50, 25, 10, 5, 2, 1, 1.2, 0.5, 0.7]
WHEEL_PROBS = [0.00005, 0.00002, 0.00010, 0.00020, 0.00100, 0.00500, 0.04000, 0.12000, 0.06000, 0.49363, 0.28000]

BOX_TIERS = {
    2: {"price": 2.0, "max_win": 20.0},
    7: {"price": 7.0, "max_win": 50.0},
    20: {"price": 20.0, "max_win": 150.0},
    50: {"price": 50.0, "max_win": 300.0},
    100: {"price": 100.0, "max_win": 500.0},
    250: {"price": 250.0, "max_win": 1000.0},
}

BOX_MULTS = [0.00, 0.25, 0.50, 0.70, 1.00, 1.30, 2.00, 5.00]
BOX_PROBS = [0.08, 0.22, 0.28, 0.22, 0.14, 0.05, 0.009, 0.001]


class MiniAppServer:
    def __init__(self, db: Database, bot_token: str, static_dir: Path, internal_api_key: str):
        self.db = db
        self.bot_token = bot_token
        self.static_dir = static_dir
        self.internal_api_key = (internal_api_key or "").strip()

    async def _get_init_data(self, request: web.Request) -> str:
        # 1) Header
        init_data = (request.headers.get("X-Tg-InitData") or "").strip()
        if init_data:
            return init_data

        # 2) Authorization: tma <initData>
        auth = (request.headers.get("Authorization") or "").strip()
        if auth.lower().startswith("tma "):
            return auth[4:].strip()

        # 3) Query ?initData=...
        q = (request.query.get("initData") or "").strip()
        if q:
            return q

        # 4) JSON body {initData:"..."} (POST)
        if request.method in ("POST", "PUT", "PATCH"):
            try:
                data = await request.json()
                body_init = (data.get("initData") or "").strip()
                if body_init:
                    return body_init
            except Exception:
                pass

        return ""

    async def _auth_user_id(self, request: web.Request) -> int | None:
        init_data = await self._get_init_data(request)

        # полезно для отладки: увидишь, приходит ли initData вообще
        logging.info(f"[miniapp] initData len={len(init_data)} path={request.path}")

        parsed = _check_telegram_init_data(init_data, self.bot_token)
        if not parsed:
            return None
        user = parsed.get("user") or {}
        try:
            return int(user.get("id"))
        except Exception:
            return None

    async def handle_index(self, request: web.Request) -> web.Response:
        p = self.static_dir / "index.html"
        if not p.exists():
            return web.Response(text=f"index.html not found: {p}", status=500)
        return web.FileResponse(path=p)

    async def handle_me(self, request: web.Request) -> web.Response:
        uid = await self._auth_user_id(request)
        if not uid:
            return web.json_response({"ok": False, "error": "unauthorized"}, status=401)

        # ✅ теперь есть только основной баланс
        usdt = float(self.db.get_usdt_balance(uid) or 0.0)
        return web.json_response({"ok": True, "usdt_balance": usdt})

    async def handle_wheel_spin(self, request: web.Request) -> web.Response:
        uid = await self._auth_user_id(request)
        if not uid:
            return web.json_response({"ok": False, "error": "unauthorized"}, status=401)

        win = float(_weighted_choice(WHEEL_VALUES, WHEEL_PROBS))

        # ✅ play_game_usdt должен:
        # списать bet из usdt_balance и добавить win туда же
        ok, new_bal, msg = self.db.play_game_usdt(
            tg_id=uid,
            bet_usdt=float(WHEEL_COST),
            win_usdt=float(win),
            game="wheel",
            meta=""
        )
        if not ok:
            return web.json_response({"ok": False, "error": msg, "usdt_balance": float(new_bal)})

        return web.json_response({
            "ok": True,
            "bet": float(WHEEL_COST),
            "win": float(win),
            "usdt_balance": float(new_bal),
            "wheel_values": WHEEL_VALUES
        })

    async def handle_box_open(self, request: web.Request) -> web.Response:
        uid = await self._auth_user_id(request)
        if not uid:
            return web.json_response({"ok": False, "error": "unauthorized"}, status=401)

        try:
            data = await request.json()
        except Exception:
            data = {}

        tier = int(data.get("tier", 0) or 0)
        if tier not in BOX_TIERS:
            return web.json_response({"ok": False, "error": "bad_tier"}, status=400)

        price = float(BOX_TIERS[tier]["price"])
        max_win = float(BOX_TIERS[tier]["max_win"])

        mult = float(_weighted_choice(BOX_MULTS, BOX_PROBS))
        win = min(price * mult, max_win)

        ok, new_bal, msg = self.db.play_game_usdt(
            tg_id=uid,
            bet_usdt=float(price),
            win_usdt=float(win),
            game="box",
            meta=f"tier={tier}"
        )
        if not ok:
            return web.json_response({"ok": False, "error": msg, "usdt_balance": float(new_bal)})

        return web.json_response({
            "ok": True,
            "tier": tier,
            "bet": float(price),
            "mult": float(mult),
            "win": float(win),
            "usdt_balance": float(new_bal),
        })

    async def handle_internal_status(self, request: web.Request) -> web.Response:
        """
        Закрытый эндпоинт для других ботов (НЕ для пользователей).
        Авторизация: заголовок X-API-Key == INTERNAL_STATUS_API_KEY
        Body: { "tg_id": 123 }
        """
        api_key = (request.headers.get("X-API-Key") or "").strip()
        if not self.internal_api_key or api_key != self.internal_api_key:
            return web.json_response({"ok": False, "error": "unauthorized"}, status=401)

        try:
            data = await request.json()
        except Exception:
            data = {}

        try:
            tg_id = int(data.get("tg_id") or 0)
        except Exception:
            tg_id = 0

        if tg_id <= 0:
            return web.json_response({"ok": False, "error": "bad_tg_id"}, status=400)

        try:
            status = self.db.get_status(tg_id)
        except Exception:
            status = "newbie"

        is_active = status in ("active", "leader")

        return web.json_response({
            "ok": True,
            "tg_id": tg_id,
            "status": status,
            "is_active": bool(is_active),
        })


def create_app(db: Database, bot_token: str, internal_api_key: str) -> web.Application:
    static_dir = Path(__file__).resolve().parents[1] / "miniapp"
    srv = MiniAppServer(db=db, bot_token=bot_token, static_dir=static_dir, internal_api_key=internal_api_key)

    app = web.Application()

    app.router.add_get("/miniapp/", srv.handle_index)
    app.router.add_get("/miniapp", srv.handle_index)

    app.router.add_static("/miniapp/static/", path=(static_dir / "static"), name="miniapp_static")

    # ✅ Делаем и GET и POST, чтобы refreshMe работал через POST
    app.router.add_get("/api/me", srv.handle_me)
    app.router.add_post("/api/me", srv.handle_me)

    app.router.add_post("/api/wheel/spin", srv.handle_wheel_spin)
    app.router.add_post("/api/box/open", srv.handle_box_open)

    # ✅ Внутренний эндпоинт для других ботов
    app.router.add_post("/internal/status", srv.handle_internal_status)

    return app