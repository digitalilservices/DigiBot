from aiogram import Router, F
from aiogram.types import Message
from config import Config
from keyboards.main_menu import games_inline_webapp
from services.premium_emoji import PremiumEmoji

router = Router()

@router.message(F.text == "🎰 Игры")
async def games_menu(message: Message, cfg: Config, premium: PremiumEmoji):
    await premium.answer_html(
        message,
        "🎰 <b>Открой MiniApp по кнопке ниже:</b>",
        reply_markup=games_inline_webapp(cfg.WEBAPP_URL)
    )
