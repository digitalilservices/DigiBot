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

    html = (
        "📊 <b>Статистика приложения DigiBot за всё время:</b>\n\n"
        f"💵 <b>Оборот:</b> <b>${st['turnover_usdt']:.2f}</b>\n\n"
        f"🧾 <b>Cозданных счетов:</b> <b>{st['invoices_created']}</b>\n"
        f"✅ <b>Количество оплат:</b> <b>{st['payments_count']}</b>\n\n"
        f"📈 <b>Конверсия:</b> <b>{st['conversion_pct']}%</b>\n"
    )

    # ВАЖНО: отправляем через PremiumEmoji.answer_html (entities + custom_emoji)
    await premium.answer_html(message, html)