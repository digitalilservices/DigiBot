# handlers/send_digi.py
from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta

from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

from services.premium_emoji import PremiumEmoji
from config import Config
from database import Database

router = Router()


def _hash_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def _menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🧰 Сервис DGR", callback_data="go_service")],
        [InlineKeyboardButton(text="🏠 В меню", callback_data="go_menu")]
    ])


def _table_columns(db: Database, table: str) -> set[str]:
    conn = db._connect()
    cur = conn.cursor()
    cur.execute(f"PRAGMA table_info({table})")
    rows = cur.fetchall()
    conn.close()
    cols = set()
    for r in rows:
        try:
            cols.add(r["name"])
        except Exception:
            # fallback tuple
            cols.add(r[1])
    return cols


def _ensure_link_keys_table(db: Database):
    # создаём таблицу, если её нет (но если есть — НЕ ТРОГАЕМ структуру)
    conn = db._connect()
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS link_keys (
        key_hash TEXT PRIMARY KEY,
        user_id INTEGER NOT NULL,
        expires_at TEXT NOT NULL,
        used_at TEXT,
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_link_keys_user ON link_keys(user_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_link_keys_exp ON link_keys(expires_at)")
    conn.commit()
    conn.close()


def _cleanup_old_keys(db: Database):
    _ensure_link_keys_table(db)
    conn = db._connect()
    cur = conn.cursor()
    # чистим использованные и истёкшие
    cur.execute("""
        DELETE FROM link_keys
        WHERE used_at IS NOT NULL
           OR expires_at <= datetime('now')
    """)
    conn.commit()
    conn.close()


def _create_one_time_key(db: Database, user_id: int, ttl_sec: int) -> tuple[str, datetime]:
    _ensure_link_keys_table(db)
    _cleanup_old_keys(db)

    raw_key = secrets.token_urlsafe(18)
    key_hash = _hash_key(raw_key)

    expires_dt = datetime.utcnow() + timedelta(seconds=int(ttl_sec))
    # ✅ формат под sqlite datetime('now')
    expires_str = expires_dt.strftime("%Y-%m-%d %H:%M:%S")

    cols = _table_columns(db, "link_keys")

    conn = db._connect()
    cur = conn.cursor()

    if "created_at" in cols:
        cur.execute("""
            INSERT OR REPLACE INTO link_keys (key_hash, user_id, expires_at, used_at, created_at)
            VALUES (?, ?, ?, NULL, datetime('now'))
        """, (key_hash, int(user_id), expires_str))
    else:
        cur.execute("""
            INSERT OR REPLACE INTO link_keys (key_hash, user_id, expires_at, used_at)
            VALUES (?, ?, ?, NULL)
        """, (key_hash, int(user_id), expires_str))

    conn.commit()
    conn.close()

    return raw_key, expires_dt

@router.message(F.text == "🔑 Получить ключ")
async def get_link_key(message: Message, db: Database, cfg: Config, premium: PremiumEmoji):
    tg_id = message.from_user.id
    u = db.get_user(tg_id)
    if not u:
        db.create_user(tg_id=tg_id, username=message.from_user.username or "NoUsername", referrer_id=None)

    ttl = int(getattr(cfg, "WALLET_LINK_KEY_TTL_SEC", 300))
    raw_key, expires_at = _create_one_time_key(db, tg_id, ttl_sec=ttl)

    text = (
        "🔑 <b>Ключ подключения</b>\n\n"
        "Используйте экосистему <b>DigiBot</b> 🪙 Нажмите <b>«🧰 Сервис Digi»</b>, выберите нужного бота и подключите баланс <b>USDT</b> через специальный ключ.\n\n"
        f"📎 <b>Ваш ключ:</b>\n<code>{raw_key}</code>\n\n"
        f"⏳ <b>Действует 5 минут</b>\n"
        f"<b>До:</b> <b>{expires_at.strftime('%Y-%m-%d %H:%M:%S')}</b>\n\n"
        "⚠️ <b>Важно:</b> ключ одноразовый. После использования станет недействительным.\n\n"
        "❗️Не передавайте его другим людям."
    )
    await premium.answer_html(message, text, reply_markup=_menu_kb())




