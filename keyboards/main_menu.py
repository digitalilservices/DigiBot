# keyboards/main_menu.py
from __future__ import annotations

from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    WebAppInfo,
)


def _normalize_webapp_url(url: str) -> str:
    """
    Приводим URL к нормальному виду для Telegram WebApp.
    - убираем пробелы
    - добавляем https:// если забыли
    - гарантируем окончание на /miniapp/
    """
    u = (url or "").strip()
    if not u:
        return ""

    if not (u.startswith("https://") or u.startswith("http://")):
        u = "https://" + u

    if u.endswith("/miniapp"):
        u += "/"
    elif "/miniapp/" not in u:
        if u.endswith("/"):
            u += "miniapp/"
        else:
            u += "/miniapp/"

    return u


def main_menu_kb(is_admin: bool = False, miniapp_url: str = "") -> ReplyKeyboardMarkup:
    """
    Главное меню (ReplyKeyboard).

    ВАЖНО:
    На iOS Reply-кнопка web_app иногда открывает MiniApp без initData (initData=0).
    Поэтому здесь мы делаем "🎰 Игры" обычной кнопкой, а открытие MiniApp
    делаем через inline кнопку (см. open_games_inline_kb / games_inline_webapp).
    """
    # URL оставляем на будущее (может пригодиться), но в reply кнопку не вставляем
    _ = _normalize_webapp_url(miniapp_url)

    games_btn = KeyboardButton(text="🎰 Игры")  # <-- ВАЖНО: без web_app

    keyboard = [
        [KeyboardButton(text="👤 Кабинет"), KeyboardButton(text="💰 Пополнить")],
        [KeyboardButton(text="🚀 Продвижение")],
        [KeyboardButton(text="💸 Заработать"), KeyboardButton(text="👥 Реферал")],
        [KeyboardButton(text="👨‍💻 Администратор")],
    ]

    last_row = [
        KeyboardButton(text="📊 Статистика"),
        KeyboardButton(text="ℹ️ О экосистеме DigaroBot"),
    ]
    if is_admin:
        last_row.append(KeyboardButton(text="🔐 Админ Панель"))
    keyboard.append(last_row)

    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        one_time_keyboard=False,
        input_field_placeholder="Выбери раздел 👇",
    )


def games_inline_webapp(miniapp_url: str) -> InlineKeyboardMarkup:
    """
    Inline WebApp кнопка (работает стабильнее, initData приходит нормально).
    """
    webapp_url = _normalize_webapp_url(miniapp_url)
    if not webapp_url.startswith("https://"):
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🎰 Игры", url=miniapp_url or "https://example.com")]
        ])

    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎰 Открыть MiniApp", web_app=WebAppInfo(url=webapp_url))]
    ])


def open_games_inline_kb(miniapp_url: str) -> InlineKeyboardMarkup:
    """
    Клавиатура, которую надо отправлять при нажатии пользователем "🎰 Игры" в меню.
    """
    return games_inline_webapp(miniapp_url)


def back_to_menu_inline() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🏠 В меню", callback_data="go_menu")]
        ]
    )


def admin_contact_inline(support_username: str) -> InlineKeyboardMarkup:
    if not support_username.startswith("@"):
        support_username = "@" + support_username

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="👨‍💻 Написать админу", url=f"https://t.me/{support_username[1:]}")],
            [InlineKeyboardButton(text="🏠 В меню", callback_data="go_menu")],
        ]
    )

def promotion_platforms_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🌟 Telegram Premium", callback_data="promo_tg_premium"),
                InlineKeyboardButton(text="✈️ Telegram", callback_data="promo_telegram"),
            ],
            [
                InlineKeyboardButton(text="📸 Instagram", callback_data="promo_instagram"),
                InlineKeyboardButton(text="🎵 TikTok", callback_data="promo_tiktok"),
            ],
            [
                InlineKeyboardButton(text="📺 YouTube", callback_data="promo_youtube"),
                InlineKeyboardButton(text="🌎 Сайты", callback_data="promo_site"),
            ],
            [
                InlineKeyboardButton(text="🏠 В меню", callback_data="go_menu"),
            ]
        ]
    )

def site_services_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="👥 Web Трафик", callback_data="site_subs")],
            [InlineKeyboardButton(text="🇷🇺 Web Трафик (Россия)", callback_data="site_shorts_views")],
            [InlineKeyboardButton(text="🇺🇸 Web Трафик (США)", callback_data="site_shorts_likes")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="promo_back_platforms")],
        ]
    )

def youtube_services_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="👥 YouTube подписчики", callback_data="yt_subs")],
            [InlineKeyboardButton(text="🎬 YouTube Shorts просмотры", callback_data="yt_shorts_views")],
            [InlineKeyboardButton(text="❤️ YouTube Shorts лайки", callback_data="yt_shorts_likes")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="promo_back_platforms")],
        ]
    )

def tiktok_services_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔴 TikTok Прямой эфир", callback_data="tt_live")],
            [InlineKeyboardButton(text="👥 TikTok подписчики provider", callback_data="tt_provider_subs")],
            [InlineKeyboardButton(text="❤️ TikTok лайки", callback_data="tt_likes")],
            [InlineKeyboardButton(text="👁 TikTok просмотры", callback_data="tt_views")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="promo_back_platforms")],
        ]
    )

def instagram_services_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📖 Instagram Истории", callback_data="ig_stories")],
            [InlineKeyboardButton(text="💬 Instagram Комментарии", callback_data="ig_comments")],
            [InlineKeyboardButton(text="❤️ Instagram лайки provider", callback_data="ig_provider_likes")],
            [InlineKeyboardButton(text="🎯 Instagram подписчики таргет", callback_data="ig_target_subs")],
            [InlineKeyboardButton(text="👥 Instagram подписчики provider", callback_data="ig_provider_subs")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="promo_back_platforms")],
        ]
    )

def tg_premium_services_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📝 TG Онлайн премиум подписчики", callback_data="tp_online_subs")],
            [InlineKeyboardButton(text="💬 Telegram Премиум комментарии", callback_data="tp_comments")],
            [InlineKeyboardButton(text="🎯 Telegram Премиум таргет. подписчики", callback_data="tp_target_subs")],
            [InlineKeyboardButton(text="👁 Telegram Премиум таргет. просмотры", callback_data="tp_target_views")],
            [InlineKeyboardButton(text="🇷🇺 Telegram Русские Премиум онлайн подписчики", callback_data="tp_ru_online_subs")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="promo_back_platforms")],
        ]
    )

def telegram_services_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💬 Telegram комментарии", callback_data="tg_comments_polls")],
            [InlineKeyboardButton(text="🇷🇺 Telegram русские подписчики", callback_data="tg_ru_subs")],
            [InlineKeyboardButton(text="👥 Telegram подписчики provider", callback_data="tg_provider_subs")],
            [InlineKeyboardButton(text="👁 Telegram просмотры provider", callback_data="tg_provider_views")],
            [InlineKeyboardButton(text="❤️ Telegram реакции provider", callback_data="tg_provider_reactions")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="promo_back_platforms")],
        ]
    )


def tp_online_subs_info_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Заказать", callback_data="tp_online_subs_order")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="promo_tg_premium")],
        ]
    )


def tp_confirm_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Подтвердить", callback_data="tp_online_subs_confirm")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="tp_cancel_order")],
        ]
    )


def promo_order_admin_kb(order_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Выполнено", callback_data=f"promo_done:{order_id}"),
                InlineKeyboardButton(text="❌ Отклонить", callback_data=f"promo_reject:{order_id}"),
            ]
        ]
    )

def tp_comments_info_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Заказать", callback_data="tp_comments_order")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="promo_tg_premium")],
        ]
    )

def tp_comments_confirm_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Подтвердить", callback_data="tp_comments_confirm")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="tp_cancel_order")],
        ]
    )

def tp_target_subs_info_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Заказать", callback_data="tp_target_subs_order")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="promo_tg_premium")],
        ]
    )


def tp_target_subs_confirm_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Подтвердить", callback_data="tp_target_subs_confirm")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="tp_cancel_order")],
        ]
    )

def tp_target_views_info_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Заказать", callback_data="tp_target_views_order")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="promo_tg_premium")],
        ]
    )


def tp_target_views_confirm_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Подтвердить", callback_data="tp_target_views_confirm")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="tp_cancel_order")],
        ]
    )

def tp_ru_online_subs_info_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Заказать", callback_data="tp_ru_online_subs_order")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="promo_tg_premium")],
        ]
    )


def tp_ru_online_subs_confirm_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Подтвердить", callback_data="tp_ru_online_subs_confirm")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="tp_cancel_order")],
        ]
    )

def tg_comments_info_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Заказать", callback_data="tg_comments_order")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="promo_telegram")],
        ]
    )


def tg_comments_confirm_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Подтвердить", callback_data="tg_comments_confirm")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="tp_cancel_order")],
        ]
    )

def tg_ru_subs_info_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Заказать", callback_data="tg_ru_subs_order")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="promo_telegram")],
        ]
    )


def tg_ru_subs_confirm_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Подтвердить", callback_data="tg_ru_subs_confirm")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="tp_cancel_order")],
        ]
    )

def tg_provider_subs_info_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Заказать", callback_data="tg_provider_subs_order")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="promo_telegram")],
        ]
    )


def tg_provider_subs_confirm_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Подтвердить", callback_data="tg_provider_subs_confirm")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="tp_cancel_order")],
        ]
    )

def tg_provider_views_info_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Заказать", callback_data="tg_provider_views_order")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="promo_telegram")],
        ]
    )


def tg_provider_views_confirm_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Подтвердить", callback_data="tg_provider_views_confirm")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="tp_cancel_order")],
        ]
    )

def tg_provider_reactions_info_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Заказать", callback_data="tg_provider_reactions_order")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="promo_telegram")],
        ]
    )


def tg_provider_reactions_confirm_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Подтвердить", callback_data="tg_provider_reactions_confirm")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="tp_cancel_order")],
        ]
    )

def ig_stories_info_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Заказать", callback_data="ig_stories_order")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="promo_instagram")],
        ]
    )


def ig_stories_confirm_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Подтвердить", callback_data="ig_stories_confirm")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="tp_cancel_order")],
        ]
    )

def ig_comments_info_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Заказать", callback_data="ig_comments_order")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="promo_instagram")],
        ]
    )


def ig_comments_confirm_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Подтвердить", callback_data="ig_comments_confirm")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="tp_cancel_order")],
        ]
    )

def ig_provider_likes_info_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Заказать", callback_data="ig_provider_likes_order")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="promo_instagram")],
        ]
    )


def ig_provider_likes_confirm_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Подтвердить", callback_data="ig_provider_likes_confirm")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="tp_cancel_order")],
        ]
    )

def ig_target_subs_info_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Заказать", callback_data="ig_target_subs_order")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="promo_instagram")],
        ]
    )


def ig_target_subs_confirm_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Подтвердить", callback_data="ig_target_subs_confirm")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="tp_cancel_order")],
        ]
    )

def ig_provider_subs_info_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Заказать", callback_data="ig_provider_subs_order")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="promo_instagram")],
        ]
    )


def ig_provider_subs_confirm_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Подтвердить", callback_data="ig_provider_subs_confirm")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="tp_cancel_order")],
        ]
    )

def tt_live_info_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Заказать", callback_data="tt_live_order")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="promo_tiktok")],
        ]
    )


def tt_live_confirm_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Подтвердить", callback_data="tt_live_confirm")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="tp_cancel_order")],
        ]
    )

def tt_provider_subs_info_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Заказать", callback_data="tt_provider_subs_order")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="promo_tiktok")],
        ]
    )


def tt_provider_subs_confirm_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Подтвердить", callback_data="tt_provider_subs_confirm")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="tp_cancel_order")],
        ]
    )

def tt_likes_info_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Заказать", callback_data="tt_likes_order")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="promo_tiktok")],
        ]
    )


def tt_likes_confirm_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Подтвердить", callback_data="tt_likes_confirm")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="tp_cancel_order")],
        ]
    )

def tt_views_info_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Заказать", callback_data="tt_views_order")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="promo_tiktok")],
        ]
    )


def tt_views_confirm_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Подтвердить", callback_data="tt_views_confirm")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="tp_cancel_order")],
        ]
    )

