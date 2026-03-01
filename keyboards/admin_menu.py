# keyboards/admin_menu.py
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def admin_panel_inline() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")],
            [InlineKeyboardButton(text="📈 Статистика приложения", callback_data="admin_appstats")],
            [InlineKeyboardButton(text="🧾 Пополнения", callback_data="admin_topups")],
            [InlineKeyboardButton(text="💸 Заявки на вывод", callback_data="admin_withdrawals")],
            [InlineKeyboardButton(text="➕ Нарахувати DIGI", callback_data="admin_give_digi")],
            [InlineKeyboardButton(text="💵 Нарахувати USDT", callback_data="admin_give_usdt")],
            [InlineKeyboardButton(text="🏠 В меню", callback_data="go_menu")],
        ]
    )


def admin_tasks_inline() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➕ Добавить задание", callback_data="admin_task_add")],
            [InlineKeyboardButton(text="🗑 Удалить задание", callback_data="admin_task_delete")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_back")],
        ]
    )


def admin_ads_inline() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📢 Список рекламы", callback_data="admin_ads_list")],
            [InlineKeyboardButton(text="🗑 Удалить рекламу", callback_data="admin_ads_delete")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_back")],
        ]
    )



