# handlers/start.py
from __future__ import annotations

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart

from config import Config
from database import Database
from keyboards.main_menu import main_menu_kb
from services.premium_emoji import PremiumEmoji

router = Router()

SIGNUP_BONUS_DIGI = 8000  # стартовый бонус


def _parse_referrer_id(text: str) -> int | None:
    """
    Ожидаем /start ref_<id>
    Пример: "/start ref_123456789"
    """
    parts = (text or "").strip().split(maxsplit=1)
    if len(parts) < 2:
        return None

    payload = parts[1].strip()
    if not payload.startswith("ref_"):
        return None

    raw = payload.replace("ref_", "", 1)
    try:
        return int(raw)
    except ValueError:
        return None


@router.message(CommandStart())
async def cmd_start(message: Message, db: Database, cfg: Config, premium: PremiumEmoji):
    tg_id = message.from_user.id
    username = message.from_user.username or "NoUsername"
    first_name = message.from_user.first_name or ""

    user = db.get_user(tg_id)
    is_new_user = False

    if user:
        # обновляем профиль (логика та же)
        db.update_profile(tg_id=tg_id, username=username, first_name=first_name)
    else:
        is_new_user = True

        referrer_id = _parse_referrer_id(message.text)

        # защита от саморефа
        if referrer_id == tg_id:
            referrer_id = None

        db.create_user(
            tg_id=tg_id,
            username=username,
            referrer_id=referrer_id,
            first_name=first_name,
        )

    # 1) Приветствие (текст не меняю)
    text = (
        "✨ <b>Добро пожаловать в DigaroBot!</b> экосистему сервисов заработка и рекламы!\n\n"
        "🪙 <b>Зарабатывай DGR на заданиях</b>\n"
        "👥 <b>Получай 4 💵 за реферала</b>\n"
        "📢 <b>Продвигай свои проекты</b>\n"
        "🎰 <b>Играй в мини игры</b>\n\n"
        "🔄 <b>Конвертация</b>\n"
        "<b>5000 DGR = 1 USDT</b>\n\n"
        "🚀 <b>Как это работает?</b>\n"
        "📝 Выполняй задания\n"
        "🪙 Получай <b>DGR</b>\n"
        "🔄 Конвертируй в <b>USDT</b>\n"
        "💚 Выводи со статусом <b>«Активный»</b>\n\n"
        "👛 <b>Интеграция с</b> @CryptoBot.\n\n"
        "<b>Выбери раздел в меню ниже</b> 👇"
    )

    await premium.answer_html(
        message,
        text,
        reply_markup=main_menu_kb(
            is_admin=(tg_id == cfg.ADMIN_ID),
            miniapp_url=cfg.WEBAPP_URL,
        ),
    )

    # отметили активность
    db.touch_user(tg_id, username, first_name)

    # 2) Бонус новому пользователю (логика та же)
    if is_new_user:
        try:
            given = db.give_signup_bonus_once(tg_id, SIGNUP_BONUS_DIGI)
            if given:
                await premium.answer_html(
                    message,
                    "🎁 <b>Стартовый бонус !</b>\n\n"
                    f"🪙 Вам начислено: <b>+{SIGNUP_BONUS_DIGI:,} DGR</b>\n\n"
                    "Используйте их для заданий, рекламы или заработка 🚀",
                )
                db.touch_user(tg_id, username, first_name)
        except Exception:
            # специально молчим (как у тебя было), чтобы не ломать старт
            pass


@router.callback_query(F.data == "go_menu")
async def go_menu(call: CallbackQuery, cfg: Config, premium: PremiumEmoji):
    # лучше отвечать тем же способом (html), чтобы формат/эмодзи были единые
    await premium.answer_html(
        call.message,
        "🏠 Главное меню 👇",
        reply_markup=main_menu_kb(
            is_admin=(call.from_user.id == cfg.ADMIN_ID),
            miniapp_url=cfg.WEBAPP_URL,
        ),
    )
    await call.answer()

