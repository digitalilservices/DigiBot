# handlers/about.py
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import Config

# ✅ Premium Emoji formatter (DI dependency)
from services.premium_emoji import PremiumEmoji

router = Router()


def _fmt(premium: PremiumEmoji, text: str) -> str:
    """Форматируем текст премиум-эмодзи (если есть)."""
    try:
        return premium.format(text)
    except Exception:
        return text


# ===== СПИСОК БОТОВ =====
SERVICE_BOTS = [
    ("🤖 AI Generator", "DigiServisVoice_bot"),
    ("📈 SMM Bot", "your_smm_bot_username"),
    ("🎮 Game Bot", "your_game_bot_username"),
]
# ========================


@router.message(F.text == "ℹ️ О экосистеме DigiBot")
async def about(message: Message, cfg: Config, premium: PremiumEmoji):
    kb = InlineKeyboardBuilder()

    if cfg.WEBSITE_URL:
        kb.button(text="🌐 Сайт", url=cfg.WEBSITE_URL)

    kb.button(text="🏠 В меню", callback_data="go_menu")
    kb.adjust(1)

    text = (
        "ℹ️ <b>Экосистема DigiBot</b>\n\n"
        "🤖 <b>Что умеет этот бот</b>❓\n\n"
        "🚀 <b>DigiBot</b> — это рекламная платформа, экосистема сервисов и инструмент для заработка <b>USDT</b> с единым балансом.\n\n"
        "📢 <b>Рекламная платформа</b>\n"
        "Создавайте задания и продвигайте каналы, группы, ботов и посты внутри системы.\n\n"
        "💵 <b>Заработок USDT</b>\n"
        "Получите статус <b>«Активный»</b>, приглашайте пользователей и получайте <b>2.5 USDT</b> за каждого активного реферала.\n"
        "Начисление происходит автоматически. Вывод — без лимитов.\n\n"
        "❓ <b>Почему нужен статус «Активный»</b>\n"
        "Чтобы система реферальных выплат работала стабильно, в неё должны поступать средства.\n"
        "Полностью бесплатный доступ сделал бы сервис убыточным.\n"
        "Статус <b>«Активный»</b> подтверждает участие пользователя в системе и открывает доступ к заработку.\n"
        "Получить его максимально просто.\n\n"
        "🎰 <b>Мини-игры</b>\n"
        "Для тех, кто хочет испытать удачу — участие полностью по желанию.\n"
        "Выигранные <b>USDT</b> доступны к выводу.\n\n"
        "🪙 <b>Валюта DIGI</b>\n"
        "Зарабатывайте DIGI, выполняя задания.\n\n"
        "🔄 <b>Конвертация</b>\n"
        "<b>5000 DIGI = 1 USDT</b>\n"
        "<b>1 USDT = 5000 DIGI</b>\n\n"
        "🟢 <b>Статус «Активный» даёт:</b>\n"
        "• Доход с рефералов\n"
        "• Вывод USDT\n"
        "• Конвертацию\n\n"
        "#️⃣ <b>Мы понимаем, что в 2026 году много скама, и людям сложно доверять новым проектам.\n"
        "Поэтому мы создаём прозрачную и устойчивую систему с реальной пользой как для пользователей, так и для сервиса.</b>\n\n"
        "🪙 <b>DigiBot — простой и эффективный инструмент.\n"
        "При желании вы можете пользоваться им бесплатно: продвигать каналы, группы, ботов и зарабатывать DIGI без вложений.</b>\n\n"
        "👨‍💻 <b>Администратор:</b> @illy228\n\n"
        "🌐 Подробности — на нашем сайте 👇"
    )

    await premium.answer_html(
        message,
        text,
        reply_markup=kb.as_markup()
    )


# ===== ОБЩИЙ ОБРАБОТЧИК СЕРВИСА =====
@router.callback_query(F.data == "go_service")
async def go_service(call: CallbackQuery, premium: PremiumEmoji):
    kb = InlineKeyboardBuilder()

    for title, username in SERVICE_BOTS:
        kb.button(text=title, url=f"https://t.me/{username}")

    kb.button(text="⬅️ Назад", callback_data="go_menu")
    kb.adjust(1)

    text = (
        "🧰 <b>Наши сервисы</b>\n\n"
        "Выберите нужного бота 👇"
    )

    await premium.edit_html(
        call.message,
        text,
        reply_markup=kb.as_markup()
    )
    await call.answer()
