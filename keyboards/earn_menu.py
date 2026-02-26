# keyboards/earn_menu.py
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def earn_categories_inline(counts: dict) -> InlineKeyboardMarkup:
    """
    counts keys:
      channel, group, views, bot, react
    """
    c = lambda k: int(counts.get(k, 0) or 0)

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=f"📣 Подписка на канал", callback_data="earn_cat:channel")],
            [InlineKeyboardButton(text=f"👥 Вступить в группу", callback_data="earn_cat:group")],
            [InlineKeyboardButton(text=f"👁 Просмотр постов", callback_data="earn_cat:views")],
            [InlineKeyboardButton(text=f"🤖 Перейти в бота", callback_data="earn_cat:bot")],
            [InlineKeyboardButton(text=f"🔥 Реакции", callback_data="earn_cat:react")],
            [InlineKeyboardButton(text="➕ Добавить задание", callback_data="earn_add_root")],
            [InlineKeyboardButton(text="📦 Мои задания", callback_data="earn_my_tasks")],
            [InlineKeyboardButton(text="🏠 В меню", callback_data="go_menu")],
        ]
    )


def earn_task_row_inline(url: str, task_id: int, reward_digi: int, left_title: str = "Перейти") -> InlineKeyboardMarkup:
    """
    Две кнопки в ряд как на скрине:
    [+2000 💰 | Перейти]   [🔄 Проверить]
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=f"+{int(reward_digi):,} 💰 | {left_title}", url=url),
                InlineKeyboardButton(text="🔄 Проверить", callback_data=f"earn_check:{task_id}"),
            ],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="earn_back")],
        ]
    )



def earn_add_root_inline() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📣 Канал", callback_data="earn_add:channel")],
            [InlineKeyboardButton(text="👥 Группа", callback_data="earn_add:group")],
            [InlineKeyboardButton(text="👁 Пост", callback_data="earn_add:views")],
            [InlineKeyboardButton(text="🤖 Бот", callback_data="earn_add:bot")],
            [InlineKeyboardButton(text="🔥 Реакции", callback_data="earn_add:react")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="earn_back")],
        ]
    )


def my_tasks_list_inline(task_ids: list[int]) -> InlineKeyboardMarkup:
    kb = []
    for tid in task_ids[:20]:
        kb.append([InlineKeyboardButton(text=f"🗑 Отменить #{tid}", callback_data=f"earn_cancel_task:{tid}")])
    kb.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="earn_back")])
    return InlineKeyboardMarkup(inline_keyboard=kb)

def earn_add_back_inline() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="earn_add_root")]
        ]
    )