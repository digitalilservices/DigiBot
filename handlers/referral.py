# handlers/referral.py
from __future__ import annotations

from urllib.parse import quote

from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

from services.premium_emoji import PremiumEmoji
from config import Config
from database import Database

router = Router()


def _rget(row, key: str, default=None):
    """Безопасно достаём поле из sqlite3.Row / dict."""
    if row is None:
        return default
    try:
        if isinstance(row, dict):
            return row.get(key, default)
        if hasattr(row, "keys") and key in row.keys():
            v = row[key]
            return default if v is None else v
    except Exception:
        pass
    return default


@router.message(F.text == "👥 Реферал")
async def referral(message: Message, cfg: Config, db: Database, premium: PremiumEmoji):
    tg_id = message.from_user.id
    username = message.from_user.username or "NoUsername"

    # ensure user exists
    user = db.get_user(tg_id)
    if not user:
        try:
            db.create_user(
                tg_id=tg_id,
                username=username,
                referrer_id=None,
                first_name=message.from_user.first_name
            )
        except TypeError:
            # если твой create_user не принимает first_name
            db.create_user(tg_id=tg_id, username=username, referrer_id=None)
        user = db.get_user(tg_id)

    # update username if changed
    try:
        if user and (_rget(user, "username", "") or "") != (username or ""):
            db.update_username(tg_id, username)
            user = db.get_user(tg_id)
    except Exception:
        pass

    # status
    status = "newbie"
    try:
        status = db.get_status(tg_id)
    except Exception:
        status = str(_rget(user, "status", "newbie") or "newbie")

    # ✅ рефералка доступна для Active/Leader
    if status not in ("active", "leader"):
        text = (
            "👥 <b>Реферальная система</b>\n\n"
            "⛔️ Доступ закрыт. Ваш статус: <b>Новичок</b>\n\n"
            "✅ Чтобы открыть рефералку и начать зарабатывать, получите статус <b>💚 Активный</b>:\n\n"
            "<b>• Пополнить 10 USDT</b>\n"
            "<b>• Выполнить 7 заданий</b>\n"
            "<b>• Создать 7 заданий</b>\n\n"
            "💵 Награда <b>4 USDT</b> за каждого реферала <b>+ 2 USDT</b>, если ваш реферал пригласит ещё одного пользователя.\n\n"
            "📌 Реферал засчитывается, когда приглашённый пополнит <b>10 USDT</b>."

        )
        await premium.answer_html(message, text)
        return

    # Active/Leader: показываем ссылку и статистику
    me = await message.bot.get_me()
    bot_username = getattr(me, "username", None) or ""
    ref_link = f"https://t.me/{bot_username}?start=ref_{tg_id}" if bot_username else "—"

    referrals = int(_rget(user, "referrals_count", 0) or 0)
    try:
        joined = int(db.get_referrals_joined_count(tg_id) or 0)
    except Exception:
        joined = 0

    status_title = "💜 Лидер" if status == "leader" else "💚 Активный"

    text = (
        "👥 <b>Реферальная система</b>\n\n"
        f"🏷 Ваш статус: <b>{status_title}</b>\n\n"
        f"👤 <b>Рефералов зачислено:</b> <b>{referrals}</b>\n"
        f"👥 <b>Присоединилось по ссылке:</b> <b>{joined}</b>\n\n"
        "💵 Награда <b>4 USDT</b> за каждого реферала <b>+ 2 USDT</b>, если ваш реферал пригласит ещё одного пользователя.\n\n"
        "📌 Реферал засчитывается, когда приглашённый пополнит <b>10 USDT</b>\n\n"
        "🔗 <b>Ваша реферальная ссылка:</b>\n"
        f"<code>{ref_link}</code>\n\n"
        "✅ Отправьте ссылку друзьям — начисление произойдет автоматически после пополнения."
    )

    # ✅ Кнопка "Поделиться"
    share_text = (
        "🚀 Присоединяйся к DigiBot и зарабатывай USDT!\n\n"
        "💵 Награда: 4 USDT за приглашённого друга"
    )
    share_url = f"https://t.me/share/url?url={quote(ref_link)}&text={quote(share_text)}"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📤 Поделиться ссылкой", url=share_url)]
    ])

    await premium.answer_html(message, text, reply_markup=kb)