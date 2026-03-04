# handlers/cabinet.py
from __future__ import annotations

from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from services.premium_emoji import PremiumEmoji
from aiogram.types import CallbackQuery
from config import Config
from database import Database

router = Router()


def cabinet_actions_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🟢 Активация статуса", callback_data="activation_menu")],
        [InlineKeyboardButton(text="🔄 Конвертация", callback_data="convert_menu")],
        [InlineKeyboardButton(text="🧰 Сервис DGR", callback_data="go_service")],
        [InlineKeyboardButton(text="💸 Вывод", callback_data="withdraw_menu")],
    ])


def rget(row, key: str, default=None):
    """Безопасно достаём поле из sqlite3.Row / dict."""
    if row is None:
        return default
    try:
        if isinstance(row, dict):
            return row.get(key, default)
        keys = row.keys()
        if key in keys:
            val = row[key]
            return default if val is None else val
    except Exception:
        pass
    return default

@router.callback_query(F.data == "cabinet")
async def cabinet_cb(call: CallbackQuery, db: Database, cfg: Config, premium: PremiumEmoji):
    # переиспользуем ту же логику
    await cabinet(call.message, db, cfg, premium)
    await call.answer()

@router.message(F.text == "👤 Кабинет")
async def cabinet(message: Message, db: Database, cfg: Config, premium: PremiumEmoji):
    tg_id = message.from_user.id
    username = message.from_user.username or "NoUsername"

    user = db.get_user(tg_id)
    if not user:
        db.create_user(tg_id=tg_id, username=username, referrer_id=None)
        user = db.get_user(tg_id)

    # обновим username если поменялся
    old_username = rget(user, "username", "NoUsername")
    if old_username != username:
        try:
            db.update_username(tg_id, username)
            user = db.get_user(tg_id)
        except Exception:
            pass

    digi_balance = int(rget(user, "balance_digi", 0) or 0)
    usdt_balance = float(rget(user, "usdt_balance", 0.0) or 0.0)

    total_topup = float(rget(user, "total_topup_usdt", 0.0) or 0.0)

    # NEW: статус + реф баланс + прогресс
    try:
        status = db.get_status(tg_id)
    except Exception:
        status = str(rget(user, "status", "newbie") or "newbie")


    tasks_completed_total = int(rget(user, "tasks_completed_total", 0) or 0)
    tasks_created_total = int(rget(user, "tasks_created_total", 0) or 0)

    # лимит заданий
    tasks_limit = 10 if status == "active" else 7

    # условия активации
    need_topup = 10.0
    need_done = 7
    need_created = 7

    done_done = min(tasks_completed_total, need_done)
    done_created = min(tasks_created_total, need_created)
    done_topup = min(total_topup, need_topup)

    is_active = status in ("active", "leader")

    if status == "leader":
        status_title = "💜 Лидер"
    elif status == "active":
        status_title = "💚 Активный"
    else:
        status_title = "💙 Новичок"

    withdraw_txt = "✅ доступен" if is_active else "❌ заблокирован"
    ref_txt = "✅ доступна" if is_active else "❌ закрыта"
    # Конвертация меню можно показывать всем, но доступы ниже — уже в purchase.py
    convert_txt = "✅ доступна" if is_active else "❌ закрыта"

    digi_per_1_usdt = int(getattr(cfg, "DIGI_PER_1_USDT", 5000))

    progress_block = ""
    if status != "active":
        progress_block = (
            "\n\n <b></b>\n"
            f"<b></b>\n"
            f"<b></b>\n"
            f"<b></b>"
        )
    text = (
        "👤 <b>Ваш кабинет</b>\n\n"
        f"📱 <b>Аккаунт:</b> @{rget(user, 'username', username)}\n\n"
        f"💵 <b>Баланс USDT:</b> <b>{usdt_balance:.2f}</b>\n"
        f"🪙 <b>Баланс DGR:</b> <b>{digi_balance:,}</b>\n\n"
        f"🏷 <b>Статус:</b> <b>{status_title}</b>\n\n"
        f"🔄 <b>Конвертация:</b> <b>{convert_txt}</b>\n"
        f"💸 <b>Вывод:</b> <b>{withdraw_txt}</b>"
        f"{progress_block}"
    )

    await premium.answer_html(message, text, reply_markup=cabinet_actions_kb())
