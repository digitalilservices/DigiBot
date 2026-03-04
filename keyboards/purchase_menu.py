# keyboards/purchase_menu.py
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def purchase_root_inline() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📢 Реклама", callback_data="buy_ads")],
            [InlineKeyboardButton(text="🔄 Конвертация", callback_data="convert_menu")],
            [InlineKeyboardButton(text="🏠 В меню", callback_data="go_menu")],
        ]
    )


def convert_menu_inline() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🪙 DGR → 💵 USDT", callback_data="convert_digi_to_usdt")],
            [InlineKeyboardButton(text="💵 USDT → 🪙 DGR", callback_data="convert_usdt_to_digi")],
            [InlineKeyboardButton(text="🏠 В меню", callback_data="go_menu")],
        ]
    )


def services_list_inline() -> InlineKeyboardMarkup:
    """
    Список услуг
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🤖 Создание Telegram-ботов", callback_data="svc:tgbot")],
            [InlineKeyboardButton(text="🌐 Создание сайтов", callback_data="svc:website")],
            [InlineKeyboardButton(text="📈 SMM-продвижение", callback_data="svc:smm")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="buy_root")],
        ]
    )


def service_actions_inline(support_username: str, service_code: str) -> InlineKeyboardMarkup:
    """
    Действия по услуге: написать / оплатить
    service_code: tgbot / website / smm
    """
    if not support_username.startswith("@"):
        support_username = "@" + support_username

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="👨‍💻 Написать", url=f"https://t.me/{support_username[1:]}")],
            [InlineKeyboardButton(text="💳 Оплатить DGR", callback_data=f"svc_pay:{service_code}")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="buy_services")],
        ]
    )


def bots_list_inline() -> InlineKeyboardMarkup:
    """
    Раздел "Боты" (пока шаблон: ссылки можно менять/добавлять).
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⭐️ Digital Music Bot", url="https://t.me/")],
            [InlineKeyboardButton(text="⭐️ Subscriber Bot", url="https://t.me/")],
            [InlineKeyboardButton(text="⭐️ WarmUp SaaS Bot", url="https://t.me/")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="buy_root")],
        ]
    )


def ads_actions_inline() -> InlineKeyboardMarkup:
    """
    Реклама: начать создание
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➕ Разместить рекламу", callback_data="ads_create")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="buy_root")],
        ]
    )


def service_pay_back_inline(service_code: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад", callback_data=f"svc_back:{service_code}")],
        ]
    )
