# handlers/about.py
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import Config
from services.premium_emoji import PremiumEmoji

router = Router()


# ===== СПИСОК БОТОВ =====
SERVICE_BOTS = [
    ("🤖 AI Generator", "DigiServisVoice_bot"),
    ("📈 SMM Bot", "your_smm_bot_username"),
    ("🎮 Game Bot", "your_game_bot_username"),
]
# ========================


# ===== СТРАНИЦЫ ABOUT =====
ABOUT_PAGE_1 = (
    "ℹ️ <b>Экосистема DigiBot</b>\n\n"
    "🤖 <b>Что такое DigiBot</b> ❓\n\n"
    "🚀 <b>DigiBot</b> — это рекламная платформа, экосистема сервисов и инструмент для заработка <b>USDT</b> с единым балансом.\n\n"
    "📢 <b>Рекламная платформа</b>\n"
    "Создавайте задания и продвигайте каналы, группы, ботов и посты внутри системы.\n\n"
    "💵 <b>Заработок USDT</b>\n"
    "<b>4 USDT</b> за каждого реферала <b>+ 2 USDT</b>, если ваш реферал пригласит ещё одного пользователя.\n"
    "Со статусом <b>«Лидер»</b> вы получите конвертацию <b>DIGI в USDT.</b>\n\n"
    "❓ <b>Почему нужен статус «Активный»</b>\n"
    "Чтобы система заработка работала стабильно, в неё должны поступать средства. "
    "Полностью бесплатный доступ сделал бы сервис убыточным. "
    "Статус <b>«Активный»</b> подтверждает участие пользователя в системе и открывает доступ к заработку и сервисам.\n\n"
    "⛏️ <b>Майнинг</b>\n"
    "Прокачивайте майнер, фармите <b>DIGI</b> и атакуйте других пользователей!\n\n"
    "🪙 <b>Валюта DIGI</b>\n"
    "Зарабатывайте DIGI, выполняя задания.\n\n"
    "🔄 <b>Конвертация</b>\n"
    "<b>5000 DIGI = 1 USDT</b>\n"
    "<b>1 USDT = 5000 DIGI</b>\n\n"
    "💚 <b>Статус «Активный» даёт:</b>\n"
    "• Доход с рефералов\n"
    "• Вывод USDT\n"
    "• Конвертацию\n"
    "• Доступ к сервисам\n\n"
    "💜 <b>Статус «Лидер» даёт:</b>\n"
    "• +10 USDT на баланс\n"
    "• Конвертацию DIGI в USDT\n\n"
    "#️⃣ <b>Мы понимаем, что в 2026 году много скама, и людям сложно доверять новым проектам.\n"
    "Поэтому мы создаём прозрачную и устойчивую систему с реальной пользой как для пользователей, так и для сервиса.</b>\n\n"
    "🪙 <b>DigiBot — простой и эффективный инструмент.\n"
    "При желании вы можете пользоваться им бесплатно: продвигать каналы, группы, ботов и зарабатывать DIGI без вложений.</b>\n\n"
    "👨‍💻 <b>Администратор:</b> @illy228\n\n"
    "⚠️ <b>Больше информации жми</b> «▶️»"
)

ABOUT_PAGE_2 = (
    "❓ <b>Как пользоваться DigiBot</b>\n\n"
    "💸 <b>Раздел «Заработать»</b>\n"
    "Выполняйте задания других пользователей и получайте монеты <b>DIGI</b> на баланс. Также вы можете создавать собственные задания и продвигать свои проекты.\n\n"
    "⛏ <b>Раздел «Майнинг и Игры»</b>\n"
    "Открывайте боксы на удачу 🎁 Прокачивайте своего майнера <b>DIGI</b>🪙 Атакуйте других пользователей и усиливайте свою эффективность.\n\n"
    "👥 <b>Раздел «Реферал»</b>\n"
    "Приглашайте друзей и получайте:\n"
    "<b>• 4 USDT</b> за каждого приглашённого пользователя\n"
    "<b>• +2 USDT</b>, если ваш реферал пригласит ещё одного пользователя\n\n"
    "👤 <b>Раздел «Кабинет»</b>\n"
    "В кабинете вы можете:\n"
    "• Выводить <b>USDT</b>\n"
    "• Конвертировать <b>USDT ↔️ DIGI</b>\n"
    "• Пользоваться сервисами экосистемы\n\n"
    "🏷 <b>Как получить статус</b>\n\n"
    "💚 <b>Статус «Активный»</b>\n"
    "Чтобы получить статус, необходимо:\n"
    "• Выполнить 7 заданий\n"
    "• Создать 7 заданий\n"
    "• Пополнить баланс на <b>10 USDT</b>\n\n"
    "💜 <b>Статус «Лидер»</b>\n"
    "Для получения статуса необходимо:\n"
    "• Заработать <b>100 USDT</b>\n"
    "• Иметь статус <b>«Активный»</b>\n\n"
    "💳 <b>Как пополнить USDT</b>\n"
    "1. Введите сумму пополнения.\n"
    "2. Получите счёт и нажмите <b>«Оплатить».</b>\n"
    "3. Перейдите в <b>CryptoBot.</b>\n"
    "4. Скопируйте адрес кошелька удобной сети.\n"
    "5. Переведите указанную сумму.\n\n"
    "💸 <b>Как вывести USDT</b>\n"
    "1. Введите сумму вывода.\n"
    "2. Подтвердите операцию.\n"
    "3. Получите чек в <b>CryptoBot.</b>\n\n"
    "👛 Все операции пополнения и вывода проходят официально через @CryptoBot."
)
# ===========================


def about_kb(cfg: Config, page: int):
    kb = InlineKeyboardBuilder()

    # --- Стрелки ---
    if page == 1:
        kb.button(text="▶️", callback_data="about_page:2")
    else:
        kb.button(text="◀️", callback_data="about_page:1")


    kb.adjust(2)

    # --- Основные кнопки ---
    if cfg.WEBSITE_URL:
        kb.button(text="🌐 Сайт", url=cfg.WEBSITE_URL)
        kb.button(text="🧰 Сервис Digi", callback_data="go_service")

    kb.button(text="🏠 В меню", callback_data="go_menu")
    kb.adjust(1)

    return kb


# ===== ПЕРВАЯ СТРАНИЦА =====
@router.message(F.text == "ℹ️ О экосистеме DigiBot")
async def about(message: Message, cfg: Config, premium: PremiumEmoji):
    await premium.answer_html(
        message,
        ABOUT_PAGE_1,
        reply_markup=about_kb(cfg, 1).as_markup()
    )


# ===== ПЕРЕКЛЮЧЕНИЕ СТРАНИЦ =====
@router.callback_query(F.data.startswith("about_page:"))
async def about_page(call: CallbackQuery, cfg: Config, premium: PremiumEmoji):
    page = int(call.data.split(":")[1])

    text = ABOUT_PAGE_1 if page == 1 else ABOUT_PAGE_2

    await premium.edit_html(
        call.message,
        text,
        reply_markup=about_kb(cfg, page).as_markup()
    )

    await call.answer()


@router.callback_query(F.data == "noop")
async def noop(call: CallbackQuery):
    await call.answer()


# ===== ОБРАБОТЧИК СЕРВИСОВ =====
@router.callback_query(F.data == "go_service")
async def go_service(call: CallbackQuery, premium: PremiumEmoji):
    kb = InlineKeyboardBuilder()

    for title, username in SERVICE_BOTS:
        kb.button(text=title, url=f"https://t.me/{username}")

    kb.button(text="⬅️ Назад", callback_data="go_menu")
    kb.adjust(1)

    text = (
        "🧰 <b>Наши сервисы</b>\n\n"
        "🎁 <b>24 часа полного бесплатного доступа. "
        "Далее потребуется активировать статус «Активный» в DigiBot "
        "для продолжения использования сервисов.</b>\n\n"
        "🚀 <b>Используйте наш сервис для решения разных задач. "
        "Мы постоянно добавляем новых ботов, которые упрощают работу "
        "и экономят ваше время.</b>\n\n"
        "Выберите нужного бота 👇"
    )

    await premium.edit_html(
        call.message,
        text,
        reply_markup=kb.as_markup()
    )

    await call.answer()
