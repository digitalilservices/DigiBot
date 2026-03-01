# handlers/statistics.py
from __future__ import annotations

from aiogram import Router, F
from aiogram.types import Message

from database import Database
from services.premium_emoji import PremiumEmoji

router = Router()


@router.message(F.text == "📊 Статистика")
async def app_statistics(message: Message, db: Database, premium: PremiumEmoji):
    st = db.get_app_stats()

    text = (
        "📊 <b>Статистика приложения DigiBot за все время</b>\n\n"
        f"💵 <b>Оборот: ${st['turnover_usdt']:.2f}</b>\n"
        f"🧾 <b>Количество созданных счетов: {st['invoices_created']}</b>\n"
        f"✅ <b>Количество оплат: {st['payments_count']}</b>\n\n"
        f"📈 <b>Конверсия: {st['conversion_pct']}%</b>\n"
    )

    # если premium.format у тебя где-то может падать — можно не форматировать
    try:
        text = premium.format(text)
    except Exception:
        pass

    await message.answer(text, parse_mode="HTML")