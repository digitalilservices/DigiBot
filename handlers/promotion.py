import re

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

from database import Database
from services.premium_emoji import PremiumEmoji
from keyboards.main_menu import (
    promotion_platforms_kb,
    tg_premium_services_kb,
    tp_online_subs_info_kb,
    tp_comments_info_kb,
    tp_confirm_kb,
    tp_comments_confirm_kb,
    promo_order_admin_kb,
    tp_target_subs_info_kb,
    tp_target_subs_confirm_kb,
    tp_target_views_info_kb,
    tp_target_views_confirm_kb,
    tp_ru_online_subs_info_kb,
    tp_ru_online_subs_confirm_kb,
    telegram_services_kb,
    tg_comments_info_kb,
    tg_comments_confirm_kb,
    tg_ru_subs_info_kb,
    tg_ru_subs_confirm_kb,
    tg_provider_subs_info_kb,
    tg_provider_subs_confirm_kb,
    tg_provider_views_info_kb,
    tg_provider_views_confirm_kb,
    tg_provider_reactions_info_kb,
    tg_provider_reactions_confirm_kb,
    instagram_services_kb,
    ig_stories_info_kb,
    ig_stories_confirm_kb,
    ig_comments_info_kb,
    ig_comments_confirm_kb,
    ig_provider_likes_info_kb,
    ig_provider_likes_confirm_kb,
    ig_target_subs_info_kb,
    ig_target_subs_confirm_kb,
    ig_provider_subs_info_kb,
    ig_provider_subs_confirm_kb,
    tiktok_services_kb,
    tt_live_info_kb,
    tt_live_confirm_kb,
    tt_provider_subs_info_kb,
    tt_provider_subs_confirm_kb,
    tt_likes_info_kb,
    tt_likes_confirm_kb,
    tt_views_info_kb,
    tt_views_confirm_kb,
    youtube_services_kb,
    site_services_kb,
)

router = Router()

TP_ONLINE_SUBS_PRICE_PER_1000 = 50.0
TP_ONLINE_SUBS_MIN = 10
TP_ONLINE_SUBS_MAX = 30000

TP_COMMENTS_PRICE_PER_1000 = 300.0
TP_COMMENTS_MIN = 5
TP_COMMENTS_MAX = 2500

TP_TARGET_SUBS_PRICE_PER_1000 = 35.0
TP_TARGET_SUBS_MIN = 10
TP_TARGET_SUBS_MAX = 100000

TP_TARGET_VIEWS_PRICE_PER_1000 = 6.0
TP_TARGET_VIEWS_MIN = 10
TP_TARGET_VIEWS_MAX = 50000

TP_RU_ONLINE_SUBS_PRICE_PER_1000 = 25.0
TP_RU_ONLINE_SUBS_MIN = 10
TP_RU_ONLINE_SUBS_MAX = 20000

TG_COMMENTS_PRICE_PER_1000 = 10.0
TG_COMMENTS_MIN = 10
TG_COMMENTS_MAX = 200000

TG_RU_SUBS_PRICE_PER_1000 = 11.0
TG_RU_SUBS_MIN = 10
TG_RU_SUBS_MAX = 100000

TG_PROVIDER_SUBS_PRICE_PER_1000 = 6.0
TG_PROVIDER_SUBS_MIN = 10
TG_PROVIDER_SUBS_MAX = 240000

TG_PROVIDER_VIEWS_PRICE_PER_1000 = 0.20
TG_PROVIDER_VIEWS_MIN = 10
TG_PROVIDER_VIEWS_MAX = 25000

TG_PROVIDER_REACTIONS_PRICE_PER_1000 = 0.15
TG_PROVIDER_REACTIONS_MIN = 10
TG_PROVIDER_REACTIONS_MAX = 100000

IG_STORIES_PRICE_PER_1000 = 1.0
IG_STORIES_MIN = 50
IG_STORIES_MAX = 10000

IG_COMMENTS_PRICE_PER_1000 = 35.0
IG_COMMENTS_MIN = 5
IG_COMMENTS_MAX = 1000

IG_PROVIDER_LIKES_PRICE_PER_1000 = 15.0
IG_PROVIDER_LIKES_MIN = 10
IG_PROVIDER_LIKES_MAX = 10000

IG_TARGET_SUBS_PRICE_PER_1000 = 60.0
IG_TARGET_SUBS_MIN = 5
IG_TARGET_SUBS_MAX = 10000

IG_PROVIDER_SUBS_PRICE_PER_1000 = 26000.0
IG_PROVIDER_SUBS_MIN = 1
IG_PROVIDER_SUBS_MAX = 16

TT_LIVE_PRICE_PER_1000 = 45.0
TT_LIVE_MIN = 50
TT_LIVE_MAX = 50000

TT_PROVIDER_SUBS_PRICE_PER_1000 = 28.0
TT_PROVIDER_SUBS_MIN = 10
TT_PROVIDER_SUBS_MAX = 50000

TT_LIKES_PRICE_PER_1000 = 13.0
TT_LIKES_MIN = 10
TT_LIKES_MAX = 20000

TT_VIEWS_PRICE_PER_1000 = 0.66
TT_VIEWS_MIN = 100
TT_VIEWS_MAX = 100000000


class PromotionStates(StatesGroup):
    tp_online_subs_link = State()
    tp_online_subs_quantity = State()

    tp_comments_link = State()
    tp_comments_quantity = State()

    tp_target_subs_link = State()
    tp_target_subs_quantity = State()

    tp_target_views_link = State()
    tp_target_views_quantity = State()

    tp_ru_online_subs_link = State()
    tp_ru_online_subs_quantity = State()

    tg_comments_link = State()
    tg_comments_quantity = State()

    tg_ru_subs_link = State()
    tg_ru_subs_quantity = State()

    tg_provider_subs_link = State()
    tg_provider_subs_quantity = State()

    tg_provider_views_link = State()
    tg_provider_views_quantity = State()

    tg_provider_reactions_link = State()
    tg_provider_reactions_quantity = State()

    ig_stories_username = State()
    ig_stories_quantity = State()

    ig_comments_link = State()
    ig_comments_quantity = State()

    ig_provider_likes_link = State()
    ig_provider_likes_quantity = State()

    ig_target_subs_link = State()
    ig_target_subs_quantity = State()

    ig_provider_subs_link = State()
    ig_provider_subs_quantity = State()

    tt_live_link = State()
    tt_live_quantity = State()

    tt_provider_subs_link = State()
    tt_provider_subs_quantity = State()

    tt_likes_link = State()
    tt_likes_quantity = State()

    tt_views_link = State()
    tt_views_quantity = State()

def _is_valid_tg_link(link: str) -> bool:
    link = (link or "").strip()
    if link.startswith("https://t.me/") or link.startswith("http://t.me/"):
        return True
    if re.match(r"^t\.me\/[A-Za-z0-9_/\-+]+$", link):
        return True
    return False


def _normalize_link(link: str) -> str:
    link = (link or "").strip()
    if link.startswith("t.me/"):
        return "https://" + link
    return link

def _is_valid_inst_username(username: str) -> bool:
    username = (username or "").strip()
    if username.startswith("@"):
        return False
    return bool(re.match(r"^[A-Za-z0-9._]{1,30}$", username))


def _calc_ig_stories_price(quantity: int) -> float:
    return round((quantity / 1000) * IG_STORIES_PRICE_PER_1000, 2)

def _calc_price(quantity: int) -> float:
    return round((quantity / 1000) * TP_ONLINE_SUBS_PRICE_PER_1000, 2)

def _calc_comments_price(quantity: int) -> float:
    return round((quantity / 1000) * TP_COMMENTS_PRICE_PER_1000, 2)

def _calc_target_subs_price(quantity: int) -> float:
    return round((quantity / 1000) * TP_TARGET_SUBS_PRICE_PER_1000, 2)

def _calc_target_views_price(quantity: int) -> float:
    return round((quantity / 1000) * TP_TARGET_VIEWS_PRICE_PER_1000, 2)

def _calc_ru_online_subs_price(quantity: int) -> float:
    return round((quantity / 1000) * TP_RU_ONLINE_SUBS_PRICE_PER_1000, 2)

def _calc_tg_comments_price(quantity: int) -> float:
    return round((quantity / 1000) * TG_COMMENTS_PRICE_PER_1000, 2)

def _calc_tg_ru_subs_price(quantity: int) -> float:
    return round((quantity / 1000) * TG_RU_SUBS_PRICE_PER_1000, 2)

def _calc_tg_provider_subs_price(quantity: int) -> float:
    return round((quantity / 1000) * TG_PROVIDER_SUBS_PRICE_PER_1000, 2)

def _calc_tg_provider_views_price(quantity: int) -> float:
    return round((quantity / 1000) * TG_PROVIDER_VIEWS_PRICE_PER_1000, 2)

def _calc_tg_provider_reactions_price(quantity: int) -> float:
    return round((quantity / 1000) * TG_PROVIDER_REACTIONS_PRICE_PER_1000, 2)

def _calc_ig_comments_price(quantity: int) -> float:
    return round((quantity / 1000) * IG_COMMENTS_PRICE_PER_1000, 2)

def _calc_ig_provider_likes_price(quantity: int) -> float:
    return round((quantity / 1000) * IG_PROVIDER_LIKES_PRICE_PER_1000, 2)

def _calc_ig_target_subs_price(quantity: int) -> float:
    return round((quantity / 1000) * IG_TARGET_SUBS_PRICE_PER_1000, 2)

def _calc_ig_provider_subs_price(quantity: int) -> float:
    return round((quantity / 1000) * IG_PROVIDER_SUBS_PRICE_PER_1000, 2)

def _calc_tt_live_price(quantity: int) -> float:
    return round((quantity / 1000) * TT_LIVE_PRICE_PER_1000, 2)

def _calc_tt_provider_subs_price(quantity: int) -> float:
    return round((quantity / 1000) * TT_PROVIDER_SUBS_PRICE_PER_1000, 2)

def _calc_tt_likes_price(quantity: int) -> float:
    return round((quantity / 1000) * TT_LIKES_PRICE_PER_1000, 2)

def _calc_tt_views_price(quantity: int) -> float:
    return round((quantity / 1000) * TT_VIEWS_PRICE_PER_1000, 2)

@router.message(F.text == "🚀 Продвижение")
async def open_promotion(message: Message, premium: PremiumEmoji):
    await premium.answer_html(
        message,
        "📂 <b>Выберите платформу для продвижения</b>",
        reply_markup=promotion_platforms_kb(),
    )


@router.callback_query(F.data == "promo_back_platforms")
async def promo_back_platforms(call: CallbackQuery, premium: PremiumEmoji):
    await premium.answer_html(
        call.message,
        "📂 <b>Выберите платформу для продвижения</b>",
        reply_markup=promotion_platforms_kb(),
    )
    await call.answer()


@router.callback_query(F.data == "promo_tg_premium")
async def promo_tg_premium(call: CallbackQuery, premium: PremiumEmoji):
    await premium.answer_html(
        call.message,
        "🌟 <b>Telegram Premium</b>\n\nВыберите нужную услугу:",
        reply_markup=tg_premium_services_kb(),
    )
    await call.answer()

@router.callback_query(F.data == "promo_telegram")
async def promo_telegram(call: CallbackQuery, premium: PremiumEmoji):
    await premium.answer_html(
        call.message,
        "✈️ <b>Telegram</b>\n\nВыберите нужную услугу:",
        reply_markup=telegram_services_kb(),
    )
    await call.answer()

@router.callback_query(F.data == "promo_instagram")
async def promo_instagram(call: CallbackQuery, premium: PremiumEmoji):
    await premium.answer_html(
        call.message,
        "📸 <b>Instagram</b>\n\nВыберите нужную услугу:",
        reply_markup=instagram_services_kb(),
    )
    await call.answer()

@router.callback_query(F.data == "promo_tiktok")
async def promo_tiktok(call: CallbackQuery, premium: PremiumEmoji):
    await premium.answer_html(
        call.message,
        "🎵 <b>TikTok</b>\n\nВыберите нужную услугу:",
        reply_markup=tiktok_services_kb(),
    )
    await call.answer()

@router.callback_query(F.data == "promo_youtube")
async def promo_youtube(call: CallbackQuery, premium: PremiumEmoji):
    await premium.answer_html(
        call.message,
        "📺 <b>YouTube</b>\n\nВыберите нужную услугу:",
        reply_markup=youtube_services_kb(),
    )
    await call.answer()

@router.callback_query(F.data == "promo_site")
async def promo_site(call: CallbackQuery, premium: PremiumEmoji):
    await premium.answer_html(
        call.message,
        "🌎 <b>Сайты</b>\n\nВыберите нужную услугу:",
        reply_markup=site_services_kb(),
    )
    await call.answer()


@router.callback_query(F.data == "tp_online_subs")
async def tp_online_subs_info(call: CallbackQuery, premium: PremiumEmoji):
    text = (
        "ℹ️ <b>Информация об услуге</b>\n\n"
        "📝 <b>TG Онлайн премиум подписчики</b>\n\n"
        "Быстрый старт.\n\n"
        "Скорость до 10k в сутки.\n\n"
        "Высокий онлайн 50-90% всегда.\n\n"
        "Гарантия 30 дней от списаний.\n\n"
        "⏱ <b>Среднее время завершения:</b> 6 мин.\n\n"
        f"💰 <b>Цена за 1000:</b> {TP_ONLINE_SUBS_PRICE_PER_1000:.0f} USDT\n\n"
        f"📉 <b>Минимальное количество:</b> {TP_ONLINE_SUBS_MIN}\n"
        f"📈 <b>Максимальное количество:</b> {TP_ONLINE_SUBS_MAX}"
    )
    await premium.answer_html(
        call.message,
        text,
        reply_markup=tp_online_subs_info_kb(),
    )
    await call.answer()

@router.callback_query(F.data == "site_subs")
async def site_subs_stub(call: CallbackQuery, premium: PremiumEmoji):
    await premium.answer_html(
        call.message,
        "👥 <b>Web Трафик</b>\n\nСкоро",
        reply_markup=site_services_kb(),
    )
    await call.answer()


@router.callback_query(F.data == "site_shorts_views")
async def site_shorts_views_stub(call: CallbackQuery, premium: PremiumEmoji):
    await premium.answer_html(
        call.message,
        "🇷🇺 <b>Web Трафик (Россия)</b>\n\nСкоро",
        reply_markup=site_services_kb(),
    )
    await call.answer()


@router.callback_query(F.data == "site_shorts_likes")
async def site_shorts_likes_stub(call: CallbackQuery, premium: PremiumEmoji):
    await premium.answer_html(
        call.message,
        "️🇺🇸 <b>Web Трафик (США)</b>\n\nСкоро",
        reply_markup=site_services_kb(),
    )
    await call.answer()

@router.callback_query(F.data == "tt_live")
async def tt_live_info(call: CallbackQuery, premium: PremiumEmoji):

    text = (
        "ℹ️ <b>Информация об услуге</b>\n\n"
        "📝 <b>TT Зрители в Прямой эфир (90 мин.)</b>\n\n"
        "Старт 0-5 мин.\n"
        "Стабильные.\n"
        "Вводить ссылку на аккаунт или на сам эфир.\n\n"
        "⏱ <b>Среднее время завершения:</b> 24 ч. 53 мин.\n\n"
        f"💸 <b>Цена за 1000:</b> {TT_LIVE_PRICE_PER_1000:.0f} USDT\n\n"
        f"📉 <b>Минимальное количество:</b> {TT_LIVE_MIN}\n"
        f"📈 <b>Максимальное количество:</b> {TT_LIVE_MAX}"
    )

    await premium.answer_html(
        call.message,
        text,
        reply_markup=tt_live_info_kb()
    )
    await call.answer()

@router.callback_query(F.data == "tt_likes")
async def tt_likes_info(call: CallbackQuery, premium: PremiumEmoji):
    text = (
        "ℹ️ <b>Информация об услуге</b>\n\n"
        "📝 <b>TT ⭐ ♻️ Лайки живые (Ru)</b>\n\n"
        "Быстрый старт. Лайки от живых пользователей из России и СНГ.\n\n"
        "⏱ <b>Среднее время завершения:</b> 1 ч. 50 мин.\n\n"
        f"💸 <b>Цена за 1000:</b> {TT_LIKES_PRICE_PER_1000:.0f} USDT\n\n"
        f"📉 <b>Минимальное количество:</b> {TT_LIKES_MIN}\n"
        f"📈 <b>Максимальное количество:</b> {TT_LIKES_MAX}"
    )
    await premium.answer_html(
        call.message,
        text,
        reply_markup=tt_likes_info_kb(),
    )
    await call.answer()

@router.callback_query(F.data == "tt_provider_subs")
async def tt_provider_subs_info(call: CallbackQuery, premium: PremiumEmoji):
    text = (
        "ℹ️ <b>Информация об услуге</b>\n\n"
        "📝 <b>TT ♻️ Живые подписчики (RU)</b>\n\n"
        "Старт в течение 10 мин, высокая скорость.\n\n"
        "Гарантия 30 дней.\n\n"
        "Все профили живые, российские, с аватаром и постами.\n\n"
        "Аккаунт должен иметь хотя бы 1 пост.\n\n"
        "⏱ <b>Среднее время завершения:</b> 25 ч. 32 мин.\n\n"
        f"💸 <b>Цена за 1000:</b> {TT_PROVIDER_SUBS_PRICE_PER_1000:.0f} USDT\n\n"
        f"📉 <b>Минимальное количество:</b> {TT_PROVIDER_SUBS_MIN}\n"
        f"📈 <b>Максимальное количество:</b> {TT_PROVIDER_SUBS_MAX}"
    )
    await premium.answer_html(
        call.message,
        text,
        reply_markup=tt_provider_subs_info_kb(),
    )
    await call.answer()

@router.callback_query(F.data == "ig_provider_subs")
async def ig_provider_subs_info(call: CallbackQuery, premium: PremiumEmoji):
    text = (
        "ℹ️ <b>Информация об услуге</b>\n\n"
        "📝 <b>IG ⬜ Верифицированные подписчики</b>\n\n"
        "Быстрый старт.\n\n"
        "Скорость до 10 в сутки.\n\n"
        "Верифицированные профили с галочкой.\n\n"
        "У вас есть эксклюзивная возможность получить верифицированных пользователей Instagram. "
        "Услуга значительно повысит вовлечённость вашего аккаунта.\n\n"
        "⏱ <b>Среднее время завершения:</b> 9 ч. 8 мин.\n\n"
        f"💸 <b>Цена за 1000:</b> {IG_PROVIDER_SUBS_PRICE_PER_1000:.0f} USDT\n\n"
        f"📉 <b>Минимальное количество:</b> {IG_PROVIDER_SUBS_MIN}\n"
        f"📈 <b>Максимальное количество:</b> {IG_PROVIDER_SUBS_MAX}"
    )
    await premium.answer_html(
        call.message,
        text,
        reply_markup=ig_provider_subs_info_kb(),
    )
    await call.answer()

@router.callback_query(F.data == "ig_provider_likes")
async def ig_provider_likes_info(call: CallbackQuery, premium: PremiumEmoji):
    text = (
        "ℹ️ <b>Информация об услуге</b>\n\n"
        "📝 <b>IG ⭐ Лайки плавные (живые с охватом)</b>\n\n"
        "Старт 1-30 мин.\n\n"
        "Скорость до 1000 в сутки\n\n"
        "Лучшая услуга на данный момент. Супер-высокое качество!\n\n"
        "Высокий шанс попадания в ТОП.\n\n"
        "Лайки на фото/видео от живых пользователей.\n\n"
        "С лайками так же добавляется охват и прочая статистика.\n\n"
        "Работают всегда!\n\n"
        "⏱ <b>Среднее время завершения:</b> 2 ч. 50 мин.\n\n"
        f"💸 <b>Цена за 1000:</b> {IG_PROVIDER_LIKES_PRICE_PER_1000:.0f} USDT\n\n"
        f"📉 <b>Минимальное количество:</b> {IG_PROVIDER_LIKES_MIN}\n"
        f"📈 <b>Максимальное количество:</b> {IG_PROVIDER_LIKES_MAX}"
    )
    await premium.answer_html(
        call.message,
        text,
        reply_markup=ig_provider_likes_info_kb(),
    )
    await call.answer()

@router.callback_query(F.data == "ig_target_subs")
async def ig_target_subs_info(call: CallbackQuery, premium: PremiumEmoji):
    text = (
        "ℹ️ <b>Информация об услуге</b>\n\n"
        "📝 <b>IG 🇷🇺 Живые RU (плавные)</b>\n\n"
        "Быстрый старт.\n"
        "Скорость до 1 тыс. в сутки.\n"
        "Живые, реальные пользователи. Русскоязычные. Все с аватаром и публикациями.\n"
        "Плавное добавление.\n"
        "Работают всегда!\n"
        "Возможны отписки, т.к. пользователи живые.\n"
        "♻️ Гарантия и восстановление 30 дней.\n"
        "С аудиторией добавляется статистика (посещения и пр.)\n"
        "Подписчики с приложений.\n\n"
        "Тематики порно/ставки/заработок/наркотики/накрутка - запрещены. Заказы будут отменяться.\n\n"
        "⏱ <b>Среднее время завершения:</b> 8 ч. 53 мин.\n\n"
        f"💸 <b>Цена за 1000:</b> {IG_TARGET_SUBS_PRICE_PER_1000:.0f} USDT\n\n"
        f"📉 <b>Минимальное количество:</b> {IG_TARGET_SUBS_MIN}\n"
        f"📈 <b>Максимальное количество:</b> {IG_TARGET_SUBS_MAX}"
    )
    await premium.answer_html(
        call.message,
        text,
        reply_markup=ig_target_subs_info_kb(),
    )
    await call.answer()

@router.callback_query(F.data == "ig_comments")
async def ig_comments_info(call: CallbackQuery, premium: PremiumEmoji):
    text = (
        "ℹ️ <b>Информация об услуге</b>\n\n"
        "📝 <b>IG Комментарии живые (суперкачественные)</b>\n\n"
        "⏱ <b>Среднее время завершения:</b> 27 ч. 20 мин.\n\n"
        f"💸 <b>Цена за 1000:</b> {IG_COMMENTS_PRICE_PER_1000:.0f} USDT\n\n"
        f"📉 <b>Минимальное количество:</b> {IG_COMMENTS_MIN}\n"
        f"📈 <b>Максимальное количество:</b> {IG_COMMENTS_MAX}"
    )
    await premium.answer_html(
        call.message,
        text,
        reply_markup=ig_comments_info_kb(),
    )
    await call.answer()

@router.callback_query(F.data == "ig_stories")
async def ig_stories_info(call: CallbackQuery, premium: PremiumEmoji):
    text = (
        "ℹ️ <b>Информация об услуге</b>\n\n"
        "📝 <b>IG Просмотры историй</b>\n\n"
        "Указывать только Username (без @)\n"
        "Быстрый старт.\n"
        "Скорость до 5k в сутки.\n"
        "Реальные пользователи.\n\n"
        "⏱ <b>Среднее время завершения:</b> 3 ч. 25 мин.\n\n"
        f"💸 <b>Цена за 1000:</b> {IG_STORIES_PRICE_PER_1000:.0f} USDT\n\n"
        f"📉 <b>Минимальное количество:</b> {IG_STORIES_MIN}\n"
        f"📈 <b>Максимальное количество:</b> {IG_STORIES_MAX}"
    )
    await premium.answer_html(
        call.message,
        text,
        reply_markup=ig_stories_info_kb(),
    )
    await call.answer()

@router.callback_query(F.data == "tg_provider_reactions")
async def tg_provider_reactions_info(call: CallbackQuery, premium: PremiumEmoji):
    text = (
        "ℹ️ <b>Информация об услуге</b>\n\n"
        "📝 <b>TG Кастомные реакции под постом</b>\n\n"
        "Прежде чем оформить заказ, убедитесь, что на вашем посте уже есть кастомные реакции. "
        "Если уже реакций под постом нет, вы получите только просмотры.\n\n"
        "Нужна ссылка на пост, например <code>https://t.me/PremiumRussia/646</code>\n\n"
        "⏱ <b>Среднее время завершения:</b> 29 мин.\n\n"
        f"💸 <b>Цена за 1000:</b> {TG_PROVIDER_REACTIONS_PRICE_PER_1000:.2f} USDT\n\n"
        f"📉 <b>Минимальное количество:</b> {TG_PROVIDER_REACTIONS_MIN}\n"
        f"📈 <b>Максимальное количество:</b> {TG_PROVIDER_REACTIONS_MAX}"
    )
    await premium.answer_html(
        call.message,
        text,
        reply_markup=tg_provider_reactions_info_kb(),
    )
    await call.answer()

@router.callback_query(F.data == "tg_provider_views")
async def tg_provider_views_info(call: CallbackQuery, premium: PremiumEmoji):
    text = (
        "ℹ️ <b>Информация об услуге</b>\n\n"
        "📝 <b>TG 🔥 Моментальные просмотры</b>\n\n"
        "Быстрый старт.\n\n"
        "Скорость до 20k в час.\n\n"
        "Просмотры из разных стран от реальных аккаунтов.\n\n"
        "Нужна ссылка на пост, например <code>https://t.me/PremiumRussia/646</code>\n\n"
        "⏱ <b>Среднее время завершения:</b> 5 мин.\n\n"
        f"💸 <b>Цена за 1000:</b> {TG_PROVIDER_VIEWS_PRICE_PER_1000:.2f} USDT\n\n"
        f"📉 <b>Минимальное количество:</b> {TG_PROVIDER_VIEWS_MIN}\n"
        f"📈 <b>Максимальное количество:</b> {TG_PROVIDER_VIEWS_MAX}"
    )
    await premium.answer_html(
        call.message,
        text,
        reply_markup=tg_provider_views_info_kb(),
    )
    await call.answer()

@router.callback_query(F.data == "tg_ru_subs")
async def tg_ru_subs_info(call: CallbackQuery, premium: PremiumEmoji):
    text = (
        "ℹ️ <b>Информация об услуге</b>\n\n"
        "📝 <b>TG ⭐ 🇷🇺 Русские подписчики</b>\n\n"
        "Моментальный старт.\n\n"
        "Скорость до 20k в сутки.\n\n"
        "Подписчики из России.\n\n"
        "Личная база.\n\n"
        "Гарантия без списаний 90 дней.\n\n"
        "⏱ <b>Среднее время завершения:</b> 3 мин.\n\n"
        f"💸 <b>Цена за 1000:</b> {TG_RU_SUBS_PRICE_PER_1000:.0f} USDT\n\n"
        f"📉 <b>Минимальное количество:</b> {TG_RU_SUBS_MIN}\n"
        f"📈 <b>Максимальное количество:</b> {TG_RU_SUBS_MAX}"
    )
    await premium.answer_html(
        call.message,
        text,
        reply_markup=tg_ru_subs_info_kb(),
    )
    await call.answer()

@router.callback_query(F.data == "tg_provider_subs")
async def tg_provider_subs_info(call: CallbackQuery, premium: PremiumEmoji):
    text = (
        "ℹ️ <b>Информация об услуге</b>\n\n"
        "📝 <b>TG Быстрые подписчики без списаний</b>\n\n"
        "Старт 0-1 час.\n\n"
        "Скорость до 30k в сутки.\n\n"
        "Для любых каналов и групп.\n\n"
        "Без списаний 180 дней.\n\n"
        "⏱ <b>Среднее время завершения:</b> 15 мин.\n\n"
        f"💸 <b>Цена за 1000:</b> {TG_PROVIDER_SUBS_PRICE_PER_1000:.0f} USDT\n\n"
        f"📉 <b>Минимальное количество:</b> {TG_PROVIDER_SUBS_MIN}\n"
        f"📈 <b>Максимальное количество:</b> {TG_PROVIDER_SUBS_MAX}"
    )
    await premium.answer_html(
        call.message,
        text,
        reply_markup=tg_provider_subs_info_kb(),
    )
    await call.answer()

@router.callback_query(F.data == "tg_comments_polls")
async def tg_comments_info(call: CallbackQuery, premium: PremiumEmoji):
    text = (
        "ℹ️ <b>Информация об услуге</b>\n\n"
        "📝 <b>TG 🇷🇺 Русские комментарии</b>\n\n"
        "Быстрый старт.\n"
        "Указывать ссылку на пост.\n"
        "Рандомные комментарии от пользователей с русскими именами\n\n"
        "⏱ <b>Среднее время завершения:</b> 8 мин.\n\n"
        f"💸 <b>Цена за 1000:</b> {TG_COMMENTS_PRICE_PER_1000:.0f} USDT\n\n"
        f"📉 <b>Минимальное количество:</b> {TG_COMMENTS_MIN}\n"
        f"📈 <b>Максимальное количество:</b> {TG_COMMENTS_MAX}"
    )
    await premium.answer_html(
        call.message,
        text,
        reply_markup=tg_comments_info_kb(),
    )
    await call.answer()


@router.callback_query(F.data == "tp_ru_online_subs")
async def tp_ru_online_subs_info(call: CallbackQuery, premium: PremiumEmoji):
    text = (
        "ℹ️ <b>Информация об услуге</b>\n\n"
        "📝 <b>TG 🇷🇺 Русские премиум подписчики</b>\n\n"
        "Моментальный старт.\n\n"
        "Скорость до 10k в сутки.\n\n"
        "Русские подписчики с премиум подпиской на ру сим.\n\n"
        "Аккаунты всегда онлайн.\n\n"
        "Без списаний 15 дней.\n\n"
        "⏱ <b>Среднее время завершения:</b> 3 мин.\n\n"
        f"💸 <b>Цена за 1000:</b> {TP_RU_ONLINE_SUBS_PRICE_PER_1000:.0f} USDT\n\n"
        f"📉 <b>Минимальное количество:</b> {TP_RU_ONLINE_SUBS_MIN}\n"
        f"📈 <b>Максимальное количество:</b> {TP_RU_ONLINE_SUBS_MAX}"
    )
    await premium.answer_html(
        call.message,
        text,
        reply_markup=tp_ru_online_subs_info_kb(),
    )
    await call.answer()

@router.callback_query(F.data == "tt_views")
async def tt_views_info(call: CallbackQuery, premium: PremiumEmoji):
    text = (
        "ℹ️ <b>Информация об услуге</b>\n\n"
        "📝 <b>TT ⭐ Реальные просмотры</b>\n\n"
        "Старт 0-10 мин.\n"
        "Скорость до 1 миллиона в сутки.\n"
        "Реальные просмотры.\n\n"
        "⏱ <b>Среднее время завершения:</b> 3 ч. 19 мин.\n\n"
        f"💸 <b>Цена за 1000:</b> {TT_VIEWS_PRICE_PER_1000:.2f} USDT\n\n"
        f"📉 <b>Минимальное количество:</b> {TT_VIEWS_MIN}\n"
        f"📈 <b>Максимальное количество:</b> {TT_VIEWS_MAX}"
    )
    await premium.answer_html(
        call.message,
        text,
        reply_markup=tt_views_info_kb(),
    )
    await call.answer()

@router.callback_query(F.data == "tp_comments")
async def tp_comments_info(call: CallbackQuery, premium: PremiumEmoji):
    text = (
        "ℹ️ <b>Информация об услуге</b>\n\n"
        "📝 <b>TG Премиум комментарии</b>\n\n"
        "Быстрый старт.\n\n"
        "Скорость до 1000 в сутки.\n\n"
        "Комментарии на пост от премиум пользователей.\n\n"
        "Высокое качество.\n\n"
        "Помогает увеличению вовлечённости и рейтинга канала в поиске.\n\n"
        "⏱ <b>Среднее время завершения:</b> Новая услуга\n\n"
        f"💰 <b>Цена за 1000:</b> {TP_COMMENTS_PRICE_PER_1000:.0f} USDT\n\n"
        f"📉 <b>Минимальное количество:</b> {TP_COMMENTS_MIN}\n"
        f"📈 <b>Максимальное количество:</b> {TP_COMMENTS_MAX}"
    )
    await premium.answer_html(
        call.message,
        text,
        reply_markup=tp_comments_info_kb(),
    )
    await call.answer()

@router.callback_query(F.data == "tp_target_subs")
async def tp_target_subs_info(call: CallbackQuery, premium: PremiumEmoji):
    text = (
        "ℹ️ <b>Информация об услуге</b>\n\n"
        "📝 <b>TG 🇷🇺 Премиум подписчики (СНГ)</b>\n\n"
        "Старт 0-6 часов.\n\n"
        "Скорость до 5000 в сутки.\n\n"
        "Премиум аккаунты с русскими именами.\n\n"
        "Гео микс.\n\n"
        "Запрещённые тематики и пустые каналы не поддерживаются.\n\n"
        "Гарантия 14 дней без отписок.\n\n"
        "Премиум сохраняется 8-14 дней.\n\n"
        "Нужна ссылка на пост, например <code>https://t.me/PremiumRussia/646</code>\n\n"
        "⏱ <b>Среднее время завершения:</b> 3 ч. 26 мин.\n\n"
        f"💸 <b>Цена за 1000:</b> {TP_TARGET_SUBS_PRICE_PER_1000:.0f} USDT\n\n"
        f"📉 <b>Минимальное количество:</b> {TP_TARGET_SUBS_MIN}\n"
        f"📈 <b>Максимальное количество:</b> {TP_TARGET_SUBS_MAX}"
    )
    await premium.answer_html(
        call.message,
        text,
        reply_markup=tp_target_subs_info_kb(),
    )
    await call.answer()

@router.callback_query(F.data == "tp_target_views")
async def tp_target_views_info(call: CallbackQuery, premium: PremiumEmoji):
    text = (
        "ℹ️ <b>Информация об услуге</b>\n\n"
        "📝 <b>TG 🇷🇺 Премиум просмотры со статистикой для любых тематик</b>\n\n"
        "Нужна ссылка на пост, например <code>https://t.me/PremiumRussia/646</code>\n\n"
        "⏱ <b>Среднее время завершения:</b> 2 мин.\n\n"
        f"💸 <b>Цена за 1000:</b> {TP_TARGET_VIEWS_PRICE_PER_1000:.0f} USDT\n\n"
        f"📉 <b>Минимальное количество:</b> {TP_TARGET_VIEWS_MIN}\n"
        f"📈 <b>Максимальное количество:</b> {TP_TARGET_VIEWS_MAX}"
    )
    await premium.answer_html(
        call.message,
        text,
        reply_markup=tp_target_views_info_kb(),
    )
    await call.answer()

@router.callback_query(F.data == "tp_online_subs_order")
async def tp_online_subs_order(call: CallbackQuery, state: FSMContext, premium: PremiumEmoji):
    await state.clear()
    await state.set_state(PromotionStates.tp_online_subs_link)

    await premium.answer_html(
        call.message,
        "🔗 <b>Отправьте ссылку</b> на Telegram канал/группу/пост для продвижения.\n\n"
        "Пример:\n"
        "<code>https://t.me/your_channel</code>",
    )
    await call.answer()

@router.callback_query(F.data == "tt_live_order")
async def tt_live_order(call: CallbackQuery, state: FSMContext, premium: PremiumEmoji):
    await state.clear()
    await state.set_state(PromotionStates.tt_live_link)

    await premium.answer_html(
        call.message,
        "🔗 <b>Отправьте ссылку на TikTok аккаунт или эфир</b>\n\n"
        "Пример:\n"
        "<code>https://www.tiktok.com/@username</code>"
    )

    await call.answer()

@router.callback_query(F.data == "tt_provider_subs_order")
async def tt_provider_subs_order(call: CallbackQuery, state: FSMContext, premium: PremiumEmoji):
    await state.clear()
    await state.set_state(PromotionStates.tt_provider_subs_link)

    await premium.answer_html(
        call.message,
        "🔗 <b>Отправьте ссылку на TikTok аккаунт</b>\n\n"
        "Пример:\n"
        "<code>https://www.tiktok.com/@username</code>",
    )
    await call.answer()

@router.callback_query(F.data == "tt_likes_order")
async def tt_likes_order(call: CallbackQuery, state: FSMContext, premium: PremiumEmoji):
    await state.clear()
    await state.set_state(PromotionStates.tt_likes_link)

    await premium.answer_html(
        call.message,
        "🔗 <b>Отправьте ссылку на TikTok видео</b>\n\n"
        "Пример:\n"
        "<code>https://www.tiktok.com/@username/video/123456789</code>",
    )
    await call.answer()

@router.callback_query(F.data == "ig_target_subs_order")
async def ig_target_subs_order(call: CallbackQuery, state: FSMContext, premium: PremiumEmoji):
    await state.clear()
    await state.set_state(PromotionStates.ig_target_subs_link)

    await premium.answer_html(
        call.message,
        "🔗 <b>Отправьте ссылку на Instagram профиль</b>\n\n"
        "Пример:\n"
        "<code>https://www.instagram.com/username/</code>",
    )
    await call.answer()

@router.callback_query(F.data == "ig_provider_subs_order")
async def ig_provider_subs_order(call: CallbackQuery, state: FSMContext, premium: PremiumEmoji):
    await state.clear()
    await state.set_state(PromotionStates.ig_provider_subs_link)

    await premium.answer_html(
        call.message,
        "🔗 <b>Отправьте ссылку на Instagram профиль</b>\n\n"
        "Пример:\n"
        "<code>https://www.instagram.com/username/</code>",
    )
    await call.answer()

@router.callback_query(F.data == "ig_provider_likes_order")
async def ig_provider_likes_order(call: CallbackQuery, state: FSMContext, premium: PremiumEmoji):
    await state.clear()
    await state.set_state(PromotionStates.ig_provider_likes_link)

    await premium.answer_html(
        call.message,
        "🔗 <b>Отправьте ссылку на Instagram пост</b>\n\n"
        "Пример:\n"
        "<code>https://www.instagram.com/p/XXXXXXXX/</code>",
    )
    await call.answer()

@router.callback_query(F.data == "ig_stories_order")
async def ig_stories_order(call: CallbackQuery, state: FSMContext, premium: PremiumEmoji):
    await state.clear()
    await state.set_state(PromotionStates.ig_stories_username)

    await premium.answer_html(
        call.message,
        "👤 <b>Отправьте username Instagram</b> без символа @\n\n"
        "Пример:\n"
        "<code>example_user</code>",
    )
    await call.answer()

@router.callback_query(F.data == "tg_provider_reactions_order")
async def tg_provider_reactions_order(call: CallbackQuery, state: FSMContext, premium: PremiumEmoji):
    await state.clear()
    await state.set_state(PromotionStates.tg_provider_reactions_link)

    await premium.answer_html(
        call.message,
        "🔗 <b>Отправьте ссылку на пост</b> для реакций.\n\n"
        "Пример:\n"
        "<code>https://t.me/channel/123</code>",
    )
    await call.answer()


@router.callback_query(F.data == "ig_comments_order")
async def ig_comments_order(call: CallbackQuery, state: FSMContext, premium: PremiumEmoji):
    await state.clear()
    await state.set_state(PromotionStates.ig_comments_link)

    await premium.answer_html(
        call.message,
        "🔗 <b>Отправьте ссылку на Instagram пост</b>\n\n"
        "Пример:\n"
        "<code>https://www.instagram.com/p/XXXXXXXX/</code>",
    )
    await call.answer()

@router.callback_query(F.data == "tg_provider_views_order")
async def tg_provider_views_order(call: CallbackQuery, state: FSMContext, premium: PremiumEmoji):
    await state.clear()
    await state.set_state(PromotionStates.tg_provider_views_link)

    await premium.answer_html(
        call.message,
        "🔗 <b>Отправьте ссылку на пост</b> для просмотров.\n\n"
        "Пример:\n"
        "<code>https://t.me/channel/123</code>",
    )
    await call.answer()

@router.callback_query(F.data == "tg_provider_subs_order")
async def tg_provider_subs_order(call: CallbackQuery, state: FSMContext, premium: PremiumEmoji):
    await state.clear()
    await state.set_state(PromotionStates.tg_provider_subs_link)

    await premium.answer_html(
        call.message,
        "🔗 <b>Отправьте ссылку</b> на Telegram канал/группу для продвижения.\n\n"
        "Пример:\n"
        "<code>https://t.me/your_channel</code>",
    )
    await call.answer()

@router.callback_query(F.data == "tg_ru_subs_order")
async def tg_ru_subs_order(call: CallbackQuery, state: FSMContext, premium: PremiumEmoji):
    await state.clear()
    await state.set_state(PromotionStates.tg_ru_subs_link)

    await premium.answer_html(
        call.message,
        "🔗 <b>Отправьте ссылку</b> на Telegram канал/группу для продвижения.\n\n"
        "Пример:\n"
        "<code>https://t.me/your_channel</code>",
    )
    await call.answer()

@router.callback_query(F.data == "tg_comments_order")
async def tg_comments_order(call: CallbackQuery, state: FSMContext, premium: PremiumEmoji):
    await state.clear()
    await state.set_state(PromotionStates.tg_comments_link)

    await premium.answer_html(
        call.message,
        "🔗 <b>Отправьте ссылку на пост</b> для комментариев.\n\n"
        "Пример:\n"
        "<code>https://t.me/channel/123</code>",
    )
    await call.answer()

@router.callback_query(F.data == "tp_ru_online_subs_order")
async def tp_ru_online_subs_order(call: CallbackQuery, state: FSMContext, premium: PremiumEmoji):
    await state.clear()
    await state.set_state(PromotionStates.tp_ru_online_subs_link)

    await premium.answer_html(
        call.message,
        "🔗 <b>Отправьте ссылку</b> на Telegram канал/группу для продвижения.\n\n"
        "Пример:\n"
        "<code>https://t.me/your_channel</code>",
    )
    await call.answer()

@router.callback_query(F.data == "tp_comments_order")
async def tp_comments_order(call: CallbackQuery, state: FSMContext, premium: PremiumEmoji):
    await state.clear()
    await state.set_state(PromotionStates.tp_comments_link)

    await premium.answer_html(
        call.message,
        "🔗 <b>Отправьте ссылку</b> на Telegram пост для комментариев.\n\n"
        "Пример:\n"
        "<code>https://t.me/your_channel/123</code>",
    )
    await call.answer()


@router.callback_query(F.data == "tp_target_subs_order")
async def tp_target_subs_order(call: CallbackQuery, state: FSMContext, premium: PremiumEmoji):
    await state.clear()
    await state.set_state(PromotionStates.tp_target_subs_link)

    await premium.answer_html(
        call.message,
        "🔗 <b>Отправьте ссылку на пост</b> для продвижения.\n\n"
        "Пример:\n"
        "<code>https://t.me/PremiumRussia/646</code>",
    )
    await call.answer()

@router.callback_query(F.data == "tp_target_views_order")
async def tp_target_views_order(call: CallbackQuery, state: FSMContext, premium: PremiumEmoji):
    await state.clear()
    await state.set_state(PromotionStates.tp_target_views_link)

    await premium.answer_html(
        call.message,
        "🔗 <b>Отправьте ссылку на пост</b> для продвижения просмотров.\n\n"
        "Пример:\n"
        "<code>https://t.me/PremiumRussia/646</code>",
    )
    await call.answer()

@router.callback_query(F.data == "tt_views_order")
async def tt_views_order(call: CallbackQuery, state: FSMContext, premium: PremiumEmoji):
    await state.clear()
    await state.set_state(PromotionStates.tt_views_link)

    await premium.answer_html(
        call.message,
        "🔗 <b>Отправьте ссылку на TikTok видео</b>\n\n"
        "Пример:\n"
        "<code>https://www.tiktok.com/@username/video/123456789</code>",
    )
    await call.answer()

@router.message(PromotionStates.tp_online_subs_link)
async def tp_online_subs_get_link(message: Message, state: FSMContext, premium: PremiumEmoji):
    link = (message.text or "").strip()

    if not _is_valid_tg_link(link):
        await premium.answer_html(
            message,
            "❌ <b>Ссылка некорректна.</b>\n\n"
            "Отправьте ссылку в формате:\n"
            "<code>https://t.me/your_channel</code>",
        )
        return

    link = _normalize_link(link)
    await state.update_data(link=link)
    await state.set_state(PromotionStates.tp_online_subs_quantity)

    await premium.answer_html(
        message,
        f"📥 <b>Теперь введите количество подписчиков</b>\n\n"
        f"Минимум: <b>{TP_ONLINE_SUBS_MIN}</b>\n"
        f"Максимум: <b>{TP_ONLINE_SUBS_MAX}</b>",
    )

@router.message(PromotionStates.tt_provider_subs_link)
async def tt_provider_subs_get_link(message: Message, state: FSMContext, premium: PremiumEmoji):
    link = (message.text or "").strip()

    if not link.startswith("http"):
        await premium.answer_html(
            message,
            "❌ <b>Ссылка некорректна.</b>\n\n"
            "Отправьте ссылку на TikTok аккаунт.",
        )
        return

    await state.update_data(link=link)
    await state.set_state(PromotionStates.tt_provider_subs_quantity)

    await premium.answer_html(
        message,
        f"📥 <b>Теперь введите количество подписчиков</b>\n\n"
        f"Минимум: <b>{TT_PROVIDER_SUBS_MIN}</b>\n"
        f"Максимум: <b>{TT_PROVIDER_SUBS_MAX}</b>",
    )

@router.message(PromotionStates.tt_live_link)
async def tt_live_get_link(message: Message, state: FSMContext, premium: PremiumEmoji):
    link = (message.text or "").strip()

    if not link.startswith("http"):
        await premium.answer_html(
            message,
            "❌ <b>Ссылка некорректна</b>\n\n"
            "Отправьте ссылку на TikTok аккаунт или эфир."
        )
        return

    await state.update_data(link=link)
    await state.set_state(PromotionStates.tt_live_quantity)

    await premium.answer_html(
        message,
        f"📥 <b>Введите количество зрителей</b>\n\n"
        f"Минимум: <b>{TT_LIVE_MIN}</b>\n"
        f"Максимум: <b>{TT_LIVE_MAX}</b>"
    )


@router.message(PromotionStates.ig_provider_subs_link)
async def ig_provider_subs_get_link(message: Message, state: FSMContext, premium: PremiumEmoji):
    link = (message.text or "").strip()

    if not link.startswith("http"):
        await premium.answer_html(
            message,
            "❌ <b>Ссылка некорректна.</b>\n\n"
            "Отправьте ссылку на Instagram профиль.",
        )
        return

    await state.update_data(link=link)
    await state.set_state(PromotionStates.ig_provider_subs_quantity)

    await premium.answer_html(
        message,
        f"📥 <b>Теперь введите количество подписчиков</b>\n\n"
        f"Минимум: <b>{IG_PROVIDER_SUBS_MIN}</b>\n"
        f"Максимум: <b>{IG_PROVIDER_SUBS_MAX}</b>",
    )

@router.message(PromotionStates.ig_target_subs_link)
async def ig_target_subs_get_link(message: Message, state: FSMContext, premium: PremiumEmoji):
    link = (message.text or "").strip()

    if not link.startswith("http"):
        await premium.answer_html(
            message,
            "❌ <b>Ссылка некорректна.</b>\n\n"
            "Отправьте ссылку на Instagram профиль.",
        )
        return

    await state.update_data(link=link)
    await state.set_state(PromotionStates.ig_target_subs_quantity)

    await premium.answer_html(
        message,
        f"📥 <b>Теперь введите количество подписчиков</b>\n\n"
        f"Минимум: <b>{IG_TARGET_SUBS_MIN}</b>\n"
        f"Максимум: <b>{IG_TARGET_SUBS_MAX}</b>",
    )

@router.message(PromotionStates.ig_provider_likes_link)
async def ig_provider_likes_get_link(message: Message, state: FSMContext, premium: PremiumEmoji):
    link = (message.text or "").strip()

    if not link.startswith("http"):
        await premium.answer_html(
            message,
            "❌ <b>Ссылка некорректна.</b>\n\n"
            "Отправьте ссылку на Instagram пост.",
        )
        return

    await state.update_data(link=link)
    await state.set_state(PromotionStates.ig_provider_likes_quantity)

    await premium.answer_html(
        message,
        f"📥 <b>Теперь введите количество лайков</b>\n\n"
        f"Минимум: <b>{IG_PROVIDER_LIKES_MIN}</b>\n"
        f"Максимум: <b>{IG_PROVIDER_LIKES_MAX}</b>",
    )

@router.message(PromotionStates.ig_comments_link)
async def ig_comments_get_link(message: Message, state: FSMContext, premium: PremiumEmoji):
    link = (message.text or "").strip()

    if not link.startswith("http"):
        await premium.answer_html(
            message,
            "❌ <b>Ссылка некорректна.</b>\n\n"
            "Отправьте ссылку на Instagram пост.",
        )
        return

    await state.update_data(link=link)
    await state.set_state(PromotionStates.ig_comments_quantity)

    await premium.answer_html(
        message,
        f"📥 <b>Теперь введите количество комментариев</b>\n\n"
        f"Минимум: <b>{IG_COMMENTS_MIN}</b>\n"
        f"Максимум: <b>{IG_COMMENTS_MAX}</b>",
    )

@router.message(PromotionStates.ig_stories_username)
async def ig_stories_get_username(message: Message, state: FSMContext, premium: PremiumEmoji):
    username = (message.text or "").strip()

    if not _is_valid_inst_username(username):
        await premium.answer_html(
            message,
            "❌ <b>Username некорректный.</b>\n\n"
            "Отправьте только username без @\n"
            "Пример: <code>example_user</code>",
        )
        return

    await state.update_data(username=username)
    await state.set_state(PromotionStates.ig_stories_quantity)

    await premium.answer_html(
        message,
        f"📥 <b>Теперь введите количество просмотров историй</b>\n\n"
        f"Минимум: <b>{IG_STORIES_MIN}</b>\n"
        f"Максимум: <b>{IG_STORIES_MAX}</b>",
    )

@router.message(PromotionStates.tg_provider_reactions_link)
async def tg_provider_reactions_get_link(message: Message, state: FSMContext, premium: PremiumEmoji):
    link = (message.text or "").strip()

    if not _is_valid_tg_link(link):
        await premium.answer_html(
            message,
            "❌ <b>Ссылка некорректна.</b>\n\n"
            "Отправьте ссылку в формате:\n"
            "<code>https://t.me/channel/123</code>",
        )
        return

    link = _normalize_link(link)
    await state.update_data(link=link)
    await state.set_state(PromotionStates.tg_provider_reactions_quantity)

    await premium.answer_html(
        message,
        f"📥 <b>Теперь введите количество реакций</b>\n\n"
        f"Минимум: <b>{TG_PROVIDER_REACTIONS_MIN}</b>\n"
        f"Максимум: <b>{TG_PROVIDER_REACTIONS_MAX}</b>",
    )

@router.message(PromotionStates.tg_provider_views_link)
async def tg_provider_views_get_link(message: Message, state: FSMContext, premium: PremiumEmoji):
    link = (message.text or "").strip()

    if not _is_valid_tg_link(link):
        await premium.answer_html(
            message,
            "❌ <b>Ссылка некорректна.</b>\n\n"
            "Отправьте ссылку в формате:\n"
            "<code>https://t.me/channel/123</code>",
        )
        return

    link = _normalize_link(link)
    await state.update_data(link=link)
    await state.set_state(PromotionStates.tg_provider_views_quantity)

    await premium.answer_html(
        message,
        f"📥 <b>Теперь введите количество просмотров</b>\n\n"
        f"Минимум: <b>{TG_PROVIDER_VIEWS_MIN}</b>\n"
        f"Максимум: <b>{TG_PROVIDER_VIEWS_MAX}</b>",
    )

@router.message(PromotionStates.tg_comments_link)
async def tg_comments_get_link(message: Message, state: FSMContext, premium: PremiumEmoji):
    link = (message.text or "").strip()

    if not _is_valid_tg_link(link):
        await premium.answer_html(
            message,
            "❌ <b>Ссылка некорректна.</b>\n\n"
            "Отправьте ссылку в формате:\n"
            "<code>https://t.me/channel/123</code>",
        )
        return

    link = _normalize_link(link)
    await state.update_data(link=link)
    await state.set_state(PromotionStates.tg_comments_quantity)

    await premium.answer_html(
        message,
        f"📥 <b>Теперь введите количество комментариев</b>\n\n"
        f"Минимум: <b>{TG_COMMENTS_MIN}</b>\n"
        f"Максимум: <b>{TG_COMMENTS_MAX}</b>",
    )

@router.message(PromotionStates.tg_provider_subs_link)
async def tg_provider_subs_get_link(message: Message, state: FSMContext, premium: PremiumEmoji):
    link = (message.text or "").strip()

    if not _is_valid_tg_link(link):
        await premium.answer_html(
            message,
            "❌ <b>Ссылка некорректна.</b>\n\n"
            "Отправьте ссылку в формате:\n"
            "<code>https://t.me/your_channel</code>",
        )
        return

    link = _normalize_link(link)
    await state.update_data(link=link)
    await state.set_state(PromotionStates.tg_provider_subs_quantity)

    await premium.answer_html(
        message,
        f"📥 <b>Теперь введите количество подписчиков</b>\n\n"
        f"Минимум: <b>{TG_PROVIDER_SUBS_MIN}</b>\n"
        f"Максимум: <b>{TG_PROVIDER_SUBS_MAX}</b>",
    )

@router.message(PromotionStates.tg_ru_subs_link)
async def tg_ru_subs_get_link(message: Message, state: FSMContext, premium: PremiumEmoji):
    link = (message.text or "").strip()

    if not _is_valid_tg_link(link):
        await premium.answer_html(
            message,
            "❌ <b>Ссылка некорректна.</b>\n\n"
            "Отправьте ссылку в формате:\n"
            "<code>https://t.me/your_channel</code>",
        )
        return

    link = _normalize_link(link)
    await state.update_data(link=link)
    await state.set_state(PromotionStates.tg_ru_subs_quantity)

    await premium.answer_html(
        message,
        f"📥 <b>Теперь введите количество подписчиков</b>\n\n"
        f"Минимум: <b>{TG_RU_SUBS_MIN}</b>\n"
        f"Максимум: <b>{TG_RU_SUBS_MAX}</b>",
    )

@router.message(PromotionStates.tp_target_views_link)
async def tp_target_views_get_link(message: Message, state: FSMContext, premium: PremiumEmoji):
    link = (message.text or "").strip()

    if not _is_valid_tg_link(link):
        await premium.answer_html(
            message,
            "❌ <b>Ссылка некорректна.</b>\n\n"
            "Отправьте ссылку в формате:\n"
            "<code>https://t.me/channel/123</code>",
        )
        return

    link = _normalize_link(link)
    await state.update_data(link=link)
    await state.set_state(PromotionStates.tp_target_views_quantity)

    await premium.answer_html(
        message,
        f"📥 <b>Теперь введите количество просмотров</b>\n\n"
        f"Минимум: <b>{TP_TARGET_VIEWS_MIN}</b>\n"
        f"Максимум: <b>{TP_TARGET_VIEWS_MAX}</b>",
    )

@router.message(PromotionStates.tp_ru_online_subs_link)
async def tp_ru_online_subs_get_link(message: Message, state: FSMContext, premium: PremiumEmoji):
    link = (message.text or "").strip()

    if not _is_valid_tg_link(link):
        await premium.answer_html(
            message,
            "❌ <b>Ссылка некорректна.</b>\n\n"
            "Отправьте ссылку в формате:\n"
            "<code>https://t.me/your_channel</code>",
        )
        return

    link = _normalize_link(link)
    await state.update_data(link=link)
    await state.set_state(PromotionStates.tp_ru_online_subs_quantity)

    await premium.answer_html(
        message,
        f"📥 <b>Теперь введите количество подписчиков</b>\n\n"
        f"Минимум: <b>{TP_RU_ONLINE_SUBS_MIN}</b>\n"
        f"Максимум: <b>{TP_RU_ONLINE_SUBS_MAX}</b>",
    )

@router.message(PromotionStates.tp_comments_link)
async def tp_comments_get_link(message: Message, state: FSMContext, premium: PremiumEmoji):
    link = (message.text or "").strip()

    if not _is_valid_tg_link(link):
        await premium.answer_html(
            message,
            "❌ <b>Ссылка некорректна.</b>\n\n"
            "Отправьте ссылку в формате:\n"
            "<code>https://t.me/your_channel/123</code>",
        )
        return

    link = _normalize_link(link)
    await state.update_data(link=link)
    await state.set_state(PromotionStates.tp_comments_quantity)

    await premium.answer_html(
        message,
        f"📥 <b>Теперь введите количество комментариев</b>\n\n"
        f"Минимум: <b>{TP_COMMENTS_MIN}</b>\n"
        f"Максимум: <b>{TP_COMMENTS_MAX}</b>",
    )

@router.message(PromotionStates.tp_target_subs_link)
async def tp_target_subs_get_link(message: Message, state: FSMContext, premium: PremiumEmoji):
    link = (message.text or "").strip()

    if not _is_valid_tg_link(link):
        await premium.answer_html(
            message,
            "❌ <b>Ссылка некорректна.</b>\n\n"
            "Отправьте ссылку в формате:\n"
            "<code>https://t.me/channel/123</code>",
        )
        return

    link = _normalize_link(link)
    await state.update_data(link=link)
    await state.set_state(PromotionStates.tp_target_subs_quantity)

    await premium.answer_html(
        message,
        f"📥 <b>Теперь введите количество подписчиков</b>\n\n"
        f"Минимум: <b>{TP_TARGET_SUBS_MIN}</b>\n"
        f"Максимум: <b>{TP_TARGET_SUBS_MAX}</b>",
    )

@router.message(PromotionStates.tt_views_link)
async def tt_views_get_link(message: Message, state: FSMContext, premium: PremiumEmoji):
    link = (message.text or "").strip()

    if not link.startswith("http"):
        await premium.answer_html(
            message,
            "❌ <b>Ссылка некорректна.</b>\n\n"
            "Отправьте ссылку на TikTok видео.",
        )
        return

    await state.update_data(link=link)
    await state.set_state(PromotionStates.tt_views_quantity)

    await premium.answer_html(
        message,
        f"📥 <b>Теперь введите количество просмотров</b>\n\n"
        f"Минимум: <b>{TT_VIEWS_MIN}</b>\n"
        f"Максимум: <b>{TT_VIEWS_MAX}</b>",
    )

@router.message(PromotionStates.tt_likes_link)
async def tt_likes_get_link(message: Message, state: FSMContext, premium: PremiumEmoji):
    link = (message.text or "").strip()

    if not link.startswith("http"):
        await premium.answer_html(
            message,
            "❌ <b>Ссылка некорректна.</b>\n\n"
            "Отправьте ссылку на TikTok видео.",
        )
        return

    await state.update_data(link=link)
    await state.set_state(PromotionStates.tt_likes_quantity)

    await premium.answer_html(
        message,
        f"📥 <b>Теперь введите количество лайков</b>\n\n"
        f"Минимум: <b>{TT_LIKES_MIN}</b>\n"
        f"Максимум: <b>{TT_LIKES_MAX}</b>",
    )

@router.message(PromotionStates.tp_target_views_quantity)
async def tp_target_views_get_quantity(
    message: Message,
    state: FSMContext,
    db: Database,
    premium: PremiumEmoji,
):
    raw = (message.text or "").strip()

    if not raw.isdigit():
        await premium.answer_html(message, "❌ Введите количество цифрами.")
        return

    quantity = int(raw)

    if quantity < TP_TARGET_VIEWS_MIN:
        await premium.answer_html(
            message,
            f"❌ Минимальное количество: <b>{TP_TARGET_VIEWS_MIN}</b>",
        )
        return

    if quantity > TP_TARGET_VIEWS_MAX:
        await premium.answer_html(
            message,
            f"❌ Максимальное количество: <b>{TP_TARGET_VIEWS_MAX}</b>",
        )
        return

    data = await state.get_data()
    link = data["link"]
    price = _calc_target_views_price(quantity)

    user = db.get_user(message.from_user.id)
    balance = float(user["usdt_balance"] or 0.0) if user else 0.0

    await state.update_data(quantity=quantity, price=price)

    text = (
        "📦 <b>Подтверждение заказа</b>\n\n"
        "Услуга: <b>TG 🇷🇺 Премиум просмотры со статистикой</b>\n"
        f"🔗 Ссылка на пост: <code>{link}</code>\n"
        f"👁 Количество: <b>{quantity}</b>\n"
        f"💸 Сумма: <b>{price:.2f} USDT</b>\n"
        f"💰 Ваш баланс: <b>{balance:.2f} USDT</b>"
    )

    await premium.answer_html(
        message,
        text,
        reply_markup=tp_target_views_confirm_kb(),
    )

@router.message(PromotionStates.ig_provider_subs_quantity)
async def ig_provider_subs_get_quantity(
    message: Message,
    state: FSMContext,
    db: Database,
    premium: PremiumEmoji,
):
    raw = (message.text or "").strip()

    if not raw.isdigit():
        await premium.answer_html(message, "❌ Введите количество цифрами.")
        return

    quantity = int(raw)

    if quantity < IG_PROVIDER_SUBS_MIN:
        await premium.answer_html(
            message,
            f"❌ Минимальное количество: <b>{IG_PROVIDER_SUBS_MIN}</b>",
        )
        return

    if quantity > IG_PROVIDER_SUBS_MAX:
        await premium.answer_html(
            message,
            f"❌ Максимальное количество: <b>{IG_PROVIDER_SUBS_MAX}</b>",
        )
        return

    data = await state.get_data()
    link = data["link"]
    price = _calc_ig_provider_subs_price(quantity)

    user = db.get_user(message.from_user.id)
    balance = float(user["usdt_balance"] or 0.0) if user else 0.0

    await state.update_data(quantity=quantity, price=price)

    text = (
        "📦 <b>Подтверждение заказа</b>\n\n"
        "Услуга: <b>IG Верифицированные подписчики</b>\n"
        f"🔗 Ссылка: <code>{link}</code>\n"
        f"👥 Количество: <b>{quantity}</b>\n"
        f"💸 Сумма: <b>{price:.2f} USDT</b>\n"
        f"💰 Ваш баланс: <b>{balance:.2f} USDT</b>"
    )

    await premium.answer_html(
        message,
        text,
        reply_markup=ig_provider_subs_confirm_kb(),
    )

@router.message(PromotionStates.ig_target_subs_quantity)
async def ig_target_subs_get_quantity(
    message: Message,
    state: FSMContext,
    db: Database,
    premium: PremiumEmoji,
):
    raw = (message.text or "").strip()

    if not raw.isdigit():
        await premium.answer_html(message, "❌ Введите количество цифрами.")
        return

    quantity = int(raw)

    if quantity < IG_TARGET_SUBS_MIN:
        await premium.answer_html(
            message,
            f"❌ Минимальное количество: <b>{IG_TARGET_SUBS_MIN}</b>",
        )
        return

    if quantity > IG_TARGET_SUBS_MAX:
        await premium.answer_html(
            message,
            f"❌ Максимальное количество: <b>{IG_TARGET_SUBS_MAX}</b>",
        )
        return

    data = await state.get_data()
    link = data["link"]
    price = _calc_ig_target_subs_price(quantity)

    user = db.get_user(message.from_user.id)
    balance = float(user["usdt_balance"] or 0.0) if user else 0.0

    await state.update_data(quantity=quantity, price=price)

    text = (
        "📦 <b>Подтверждение заказа</b>\n\n"
        "Услуга: <b>IG Живые RU (плавные)</b>\n"
        f"🔗 Ссылка: <code>{link}</code>\n"
        f"👥 Количество: <b>{quantity}</b>\n"
        f"💸 Сумма: <b>{price:.2f} USDT</b>\n"
        f"💰 Ваш баланс: <b>{balance:.2f} USDT</b>"
    )

    await premium.answer_html(
        message,
        text,
        reply_markup=ig_target_subs_confirm_kb(),
    )

@router.message(PromotionStates.ig_provider_likes_quantity)
async def ig_provider_likes_get_quantity(
    message: Message,
    state: FSMContext,
    db: Database,
    premium: PremiumEmoji,
):
    raw = (message.text or "").strip()

    if not raw.isdigit():
        await premium.answer_html(message, "❌ Введите количество цифрами.")
        return

    quantity = int(raw)

    if quantity < IG_PROVIDER_LIKES_MIN:
        await premium.answer_html(
            message,
            f"❌ Минимальное количество: <b>{IG_PROVIDER_LIKES_MIN}</b>",
        )
        return

    if quantity > IG_PROVIDER_LIKES_MAX:
        await premium.answer_html(
            message,
            f"❌ Максимальное количество: <b>{IG_PROVIDER_LIKES_MAX}</b>",
        )
        return

    data = await state.get_data()
    link = data["link"]
    price = _calc_ig_provider_likes_price(quantity)

    user = db.get_user(message.from_user.id)
    balance = float(user["usdt_balance"] or 0.0) if user else 0.0

    await state.update_data(quantity=quantity, price=price)

    text = (
        "📦 <b>Подтверждение заказа</b>\n\n"
        "Услуга: <b>IG Лайки плавные</b>\n"
        f"🔗 Ссылка: <code>{link}</code>\n"
        f"❤️ Количество: <b>{quantity}</b>\n"
        f"💸 Сумма: <b>{price:.2f} USDT</b>\n"
        f"💰 Ваш баланс: <b>{balance:.2f} USDT</b>"
    )

    await premium.answer_html(
        message,
        text,
        reply_markup=ig_provider_likes_confirm_kb(),
    )

@router.message(PromotionStates.ig_comments_quantity)
async def ig_comments_get_quantity(
    message: Message,
    state: FSMContext,
    db: Database,
    premium: PremiumEmoji,
):
    raw = (message.text or "").strip()

    if not raw.isdigit():
        await premium.answer_html(message, "❌ Введите количество цифрами.")
        return

    quantity = int(raw)

    if quantity < IG_COMMENTS_MIN:
        await premium.answer_html(
            message,
            f"❌ Минимальное количество: <b>{IG_COMMENTS_MIN}</b>",
        )
        return

    if quantity > IG_COMMENTS_MAX:
        await premium.answer_html(
            message,
            f"❌ Максимальное количество: <b>{IG_COMMENTS_MAX}</b>",
        )
        return

    data = await state.get_data()
    link = data["link"]
    price = _calc_ig_comments_price(quantity)

    user = db.get_user(message.from_user.id)
    balance = float(user["usdt_balance"] or 0.0) if user else 0.0

    await state.update_data(quantity=quantity, price=price)

    text = (
        "📦 <b>Подтверждение заказа</b>\n\n"
        "Услуга: <b>IG Комментарии живые</b>\n"
        f"🔗 Ссылка: <code>{link}</code>\n"
        f"💬 Количество: <b>{quantity}</b>\n"
        f"💸 Сумма: <b>{price:.2f} USDT</b>\n"
        f"💰 Ваш баланс: <b>{balance:.2f} USDT</b>"
    )

    await premium.answer_html(
        message,
        text,
        reply_markup=ig_comments_confirm_kb(),
    )

@router.message(PromotionStates.ig_stories_quantity)
async def ig_stories_get_quantity(
    message: Message,
    state: FSMContext,
    db: Database,
    premium: PremiumEmoji,
):
    raw = (message.text or "").strip()

    if not raw.isdigit():
        await premium.answer_html(message, "❌ Введите количество цифрами.")
        return

    quantity = int(raw)

    if quantity < IG_STORIES_MIN:
        await premium.answer_html(
            message,
            f"❌ Минимальное количество: <b>{IG_STORIES_MIN}</b>",
        )
        return

    if quantity > IG_STORIES_MAX:
        await premium.answer_html(
            message,
            f"❌ Максимальное количество: <b>{IG_STORIES_MAX}</b>",
        )
        return

    data = await state.get_data()
    username = data["username"]
    price = _calc_ig_stories_price(quantity)

    user = db.get_user(message.from_user.id)
    balance = float(user["usdt_balance"] or 0.0) if user else 0.0

    await state.update_data(quantity=quantity, price=price)

    text = (
        "📦 <b>Подтверждение заказа</b>\n\n"
        "Услуга: <b>IG Просмотры историй</b>\n"
        f"👤 Username: <code>{username}</code>\n"
        f"👁 Количество: <b>{quantity}</b>\n"
        f"💸 Сумма: <b>{price:.2f} USDT</b>\n"
        f"💰 Ваш баланс: <b>{balance:.2f} USDT</b>"
    )

    await premium.answer_html(
        message,
        text,
        reply_markup=ig_stories_confirm_kb(),
    )

@router.message(PromotionStates.tg_provider_reactions_quantity)
async def tg_provider_reactions_get_quantity(
    message: Message,
    state: FSMContext,
    db: Database,
    premium: PremiumEmoji,
):
    raw = (message.text or "").strip()

    if not raw.isdigit():
        await premium.answer_html(message, "❌ Введите количество цифрами.")
        return

    quantity = int(raw)

    if quantity < TG_PROVIDER_REACTIONS_MIN:
        await premium.answer_html(
            message,
            f"❌ Минимальное количество: <b>{TG_PROVIDER_REACTIONS_MIN}</b>",
        )
        return

    if quantity > TG_PROVIDER_REACTIONS_MAX:
        await premium.answer_html(
            message,
            f"❌ Максимальное количество: <b>{TG_PROVIDER_REACTIONS_MAX}</b>",
        )
        return

    data = await state.get_data()
    link = data["link"]
    price = _calc_tg_provider_reactions_price(quantity)

    user = db.get_user(message.from_user.id)
    balance = float(user["usdt_balance"] or 0.0) if user else 0.0

    await state.update_data(quantity=quantity, price=price)

    text = (
        "📦 <b>Подтверждение заказа</b>\n\n"
        "Услуга: <b>TG Кастомные реакции под постом</b>\n"
        f"🔗 Ссылка на пост: <code>{link}</code>\n"
        f"❤️ Количество: <b>{quantity}</b>\n"
        f"💸 Сумма: <b>{price:.2f} USDT</b>\n"
        f"💰 Ваш баланс: <b>{balance:.2f} USDT</b>"
    )

    await premium.answer_html(
        message,
        text,
        reply_markup=tg_provider_reactions_confirm_kb(),
    )

@router.message(PromotionStates.tg_provider_views_quantity)
async def tg_provider_views_get_quantity(
    message: Message,
    state: FSMContext,
    db: Database,
    premium: PremiumEmoji,
):
    raw = (message.text or "").strip()

    if not raw.isdigit():
        await premium.answer_html(message, "❌ Введите количество цифрами.")
        return

    quantity = int(raw)

    if quantity < TG_PROVIDER_VIEWS_MIN:
        await premium.answer_html(
            message,
            f"❌ Минимальное количество: <b>{TG_PROVIDER_VIEWS_MIN}</b>",
        )
        return

    if quantity > TG_PROVIDER_VIEWS_MAX:
        await premium.answer_html(
            message,
            f"❌ Максимальное количество: <b>{TG_PROVIDER_VIEWS_MAX}</b>",
        )
        return

    data = await state.get_data()
    link = data["link"]
    price = _calc_tg_provider_views_price(quantity)

    user = db.get_user(message.from_user.id)
    balance = float(user["usdt_balance"] or 0.0) if user else 0.0

    await state.update_data(quantity=quantity, price=price)

    text = (
        "📦 <b>Подтверждение заказа</b>\n\n"
        "Услуга: <b>TG Моментальные просмотры</b>\n"
        f"🔗 Ссылка на пост: <code>{link}</code>\n"
        f"👁 Количество: <b>{quantity}</b>\n"
        f"💸 Сумма: <b>{price:.2f} USDT</b>\n"
        f"💰 Ваш баланс: <b>{balance:.2f} USDT</b>"
    )

    await premium.answer_html(
        message,
        text,
        reply_markup=tg_provider_views_confirm_kb(),
    )

@router.message(PromotionStates.tg_provider_subs_quantity)
async def tg_provider_subs_get_quantity(
    message: Message,
    state: FSMContext,
    db: Database,
    premium: PremiumEmoji,
):
    raw = (message.text or "").strip()

    if not raw.isdigit():
        await premium.answer_html(message, "❌ Введите количество цифрами.")
        return

    quantity = int(raw)

    if quantity < TG_PROVIDER_SUBS_MIN:
        await premium.answer_html(
            message,
            f"❌ Минимальное количество: <b>{TG_PROVIDER_SUBS_MIN}</b>",
        )
        return

    if quantity > TG_PROVIDER_SUBS_MAX:
        await premium.answer_html(
            message,
            f"❌ Максимальное количество: <b>{TG_PROVIDER_SUBS_MAX}</b>",
        )
        return

    data = await state.get_data()
    link = data["link"]
    price = _calc_tg_provider_subs_price(quantity)

    user = db.get_user(message.from_user.id)
    balance = float(user["usdt_balance"] or 0.0) if user else 0.0

    await state.update_data(quantity=quantity, price=price)

    text = (
        "📦 <b>Подтверждение заказа</b>\n\n"
        "Услуга: <b>TG Быстрые подписчики без списаний</b>\n"
        f"🔗 Ссылка: <code>{link}</code>\n"
        f"👥 Количество: <b>{quantity}</b>\n"
        f"💸 Сумма: <b>{price:.2f} USDT</b>\n"
        f"💰 Ваш баланс: <b>{balance:.2f} USDT</b>"
    )

    await premium.answer_html(
        message,
        text,
        reply_markup=tg_provider_subs_confirm_kb(),
    )

@router.message(PromotionStates.tt_live_quantity)
async def tt_live_get_quantity(message: Message, state: FSMContext, db: Database, premium: PremiumEmoji):

    raw = (message.text or "").strip()

    if not raw.isdigit():
        await premium.answer_html(message, "❌ Введите количество цифрами.")
        return

    quantity = int(raw)

    if quantity < TT_LIVE_MIN:
        await premium.answer_html(message, f"❌ Минимальное количество: <b>{TT_LIVE_MIN}</b>")
        return

    if quantity > TT_LIVE_MAX:
        await premium.answer_html(message, f"❌ Максимальное количество: <b>{TT_LIVE_MAX}</b>")
        return

    data = await state.get_data()
    link = data["link"]

    price = _calc_tt_live_price(quantity)

    user = db.get_user(message.from_user.id)
    balance = float(user["usdt_balance"] or 0.0) if user else 0.0

    await state.update_data(quantity=quantity, price=price)

    text = (
        "📦 <b>Подтверждение заказа</b>\n\n"
        "Услуга: <b>TikTok Зрители в прямой эфир</b>\n"
        f"🔗 Ссылка: <code>{link}</code>\n"
        f"👥 Количество: <b>{quantity}</b>\n"
        f"💸 Сумма: <b>{price:.2f} USDT</b>\n"
        f"💰 Ваш баланс: <b>{balance:.2f} USDT</b>"
    )

    await premium.answer_html(
        message,
        text,
        reply_markup=tt_live_confirm_kb()
    )

@router.message(PromotionStates.tg_ru_subs_quantity)
async def tg_ru_subs_get_quantity(
    message: Message,
    state: FSMContext,
    db: Database,
    premium: PremiumEmoji,
):
    raw = (message.text or "").strip()

    if not raw.isdigit():
        await premium.answer_html(message, "❌ Введите количество цифрами.")
        return

    quantity = int(raw)

    if quantity < TG_RU_SUBS_MIN:
        await premium.answer_html(
            message,
            f"❌ Минимальное количество: <b>{TG_RU_SUBS_MIN}</b>",
        )
        return

    if quantity > TG_RU_SUBS_MAX:
        await premium.answer_html(
            message,
            f"❌ Максимальное количество: <b>{TG_RU_SUBS_MAX}</b>",
        )
        return

    data = await state.get_data()
    link = data["link"]
    price = _calc_tg_ru_subs_price(quantity)

    user = db.get_user(message.from_user.id)
    balance = float(user["usdt_balance"] or 0.0) if user else 0.0

    await state.update_data(quantity=quantity, price=price)

    text = (
        "📦 <b>Подтверждение заказа</b>\n\n"
        "Услуга: <b>TG Русские подписчики</b>\n"
        f"🔗 Ссылка: <code>{link}</code>\n"
        f"👥 Количество: <b>{quantity}</b>\n"
        f"💸 Сумма: <b>{price:.2f} USDT</b>\n"
        f"💰 Ваш баланс: <b>{balance:.2f} USDT</b>"
    )

    await premium.answer_html(
        message,
        text,
        reply_markup=tg_ru_subs_confirm_kb(),
    )

@router.message(PromotionStates.tg_comments_quantity)
async def tg_comments_get_quantity(
    message: Message,
    state: FSMContext,
    db: Database,
    premium: PremiumEmoji,
):
    raw = (message.text or "").strip()

    if not raw.isdigit():
        await premium.answer_html(message, "❌ Введите количество цифрами.")
        return

    quantity = int(raw)

    if quantity < TG_COMMENTS_MIN:
        await premium.answer_html(
            message,
            f"❌ Минимальное количество: <b>{TG_COMMENTS_MIN}</b>",
        )
        return

    if quantity > TG_COMMENTS_MAX:
        await premium.answer_html(
            message,
            f"❌ Максимальное количество: <b>{TG_COMMENTS_MAX}</b>",
        )
        return

    data = await state.get_data()
    link = data["link"]
    price = _calc_tg_comments_price(quantity)

    user = db.get_user(message.from_user.id)
    balance = float(user["usdt_balance"] or 0.0) if user else 0.0

    await state.update_data(quantity=quantity, price=price)

    text = (
        "📦 <b>Подтверждение заказа</b>\n\n"
        "Услуга: <b>TG 🇷🇺 Русские комментарии</b>\n"
        f"🔗 Ссылка на пост: <code>{link}</code>\n"
        f"💬 Количество: <b>{quantity}</b>\n"
        f"💸 Сумма: <b>{price:.2f} USDT</b>\n"
        f"💰 Ваш баланс: <b>{balance:.2f} USDT</b>"
    )

    await premium.answer_html(
        message,
        text,
        reply_markup=tg_comments_confirm_kb(),
    )

@router.message(PromotionStates.tp_ru_online_subs_quantity)
async def tp_ru_online_subs_get_quantity(
    message: Message,
    state: FSMContext,
    db: Database,
    premium: PremiumEmoji,
):
    raw = (message.text or "").strip()

    if not raw.isdigit():
        await premium.answer_html(message, "❌ Введите количество цифрами.")
        return

    quantity = int(raw)

    if quantity < TP_RU_ONLINE_SUBS_MIN:
        await premium.answer_html(
            message,
            f"❌ Минимальное количество: <b>{TP_RU_ONLINE_SUBS_MIN}</b>",
        )
        return

    if quantity > TP_RU_ONLINE_SUBS_MAX:
        await premium.answer_html(
            message,
            f"❌ Максимальное количество: <b>{TP_RU_ONLINE_SUBS_MAX}</b>",
        )
        return

    data = await state.get_data()
    link = data["link"]
    price = _calc_ru_online_subs_price(quantity)

    user = db.get_user(message.from_user.id)
    balance = float(user["usdt_balance"] or 0.0) if user else 0.0

    await state.update_data(quantity=quantity, price=price)

    text = (
        "📦 <b>Подтверждение заказа</b>\n\n"
        "Услуга: <b>TG 🇷🇺 Русские премиум подписчики</b>\n"
        f"🔗 Ссылка: <code>{link}</code>\n"
        f"👥 Количество: <b>{quantity}</b>\n"
        f"💸 Сумма: <b>{price:.2f} USDT</b>\n"
        f"💰 Ваш баланс: <b>{balance:.2f} USDT</b>"
    )

    await premium.answer_html(
        message,
        text,
        reply_markup=tp_ru_online_subs_confirm_kb(),
    )

@router.message(PromotionStates.tt_provider_subs_quantity)
async def tt_provider_subs_get_quantity(
    message: Message,
    state: FSMContext,
    db: Database,
    premium: PremiumEmoji,
):
    raw = (message.text or "").strip()

    if not raw.isdigit():
        await premium.answer_html(message, "❌ Введите количество цифрами.")
        return

    quantity = int(raw)

    if quantity < TT_PROVIDER_SUBS_MIN:
        await premium.answer_html(
            message,
            f"❌ Минимальное количество: <b>{TT_PROVIDER_SUBS_MIN}</b>",
        )
        return

    if quantity > TT_PROVIDER_SUBS_MAX:
        await premium.answer_html(
            message,
            f"❌ Максимальное количество: <b>{TT_PROVIDER_SUBS_MAX}</b>",
        )
        return

    data = await state.get_data()
    link = data["link"]
    price = _calc_tt_provider_subs_price(quantity)

    user = db.get_user(message.from_user.id)
    balance = float(user["usdt_balance"] or 0.0) if user else 0.0

    await state.update_data(quantity=quantity, price=price)

    text = (
        "📦 <b>Подтверждение заказа</b>\n\n"
        "Услуга: <b>TT Живые подписчики (RU)</b>\n"
        f"🔗 Ссылка: <code>{link}</code>\n"
        f"👥 Количество: <b>{quantity}</b>\n"
        f"💸 Сумма: <b>{price:.2f} USDT</b>\n"
        f"💰 Ваш баланс: <b>{balance:.2f} USDT</b>"
    )

    await premium.answer_html(
        message,
        text,
        reply_markup=tt_provider_subs_confirm_kb(),
    )

@router.message(PromotionStates.tt_likes_quantity)
async def tt_likes_get_quantity(
    message: Message,
    state: FSMContext,
    db: Database,
    premium: PremiumEmoji,
):
    raw = (message.text or "").strip()

    if not raw.isdigit():
        await premium.answer_html(message, "❌ Введите количество цифрами.")
        return

    quantity = int(raw)

    if quantity < TT_LIKES_MIN:
        await premium.answer_html(
            message,
            f"❌ Минимальное количество: <b>{TT_LIKES_MIN}</b>",
        )
        return

    if quantity > TT_LIKES_MAX:
        await premium.answer_html(
            message,
            f"❌ Максимальное количество: <b>{TT_LIKES_MAX}</b>",
        )
        return

    data = await state.get_data()
    link = data["link"]
    price = _calc_tt_likes_price(quantity)

    user = db.get_user(message.from_user.id)
    balance = float(user["usdt_balance"] or 0.0) if user else 0.0

    await state.update_data(quantity=quantity, price=price)

    text = (
        "📦 <b>Подтверждение заказа</b>\n\n"
        "Услуга: <b>TT Лайки живые (Ru)</b>\n"
        f"🔗 Ссылка: <code>{link}</code>\n"
        f"❤️ Количество: <b>{quantity}</b>\n"
        f"💸 Сумма: <b>{price:.2f} USDT</b>\n"
        f"💰 Ваш баланс: <b>{balance:.2f} USDT</b>"
    )

    await premium.answer_html(
        message,
        text,
        reply_markup=tt_likes_confirm_kb(),
    )

@router.message(PromotionStates.tp_online_subs_quantity)
async def tp_online_subs_get_quantity(
    message: Message,
    state: FSMContext,
    db: Database,
    premium: PremiumEmoji,
):
    raw = (message.text or "").strip()

    if not raw.isdigit():
        await premium.answer_html(message, "❌ Введите количество цифрами.")
        return

    quantity = int(raw)

    if quantity < TP_ONLINE_SUBS_MIN:
        await premium.answer_html(
            message,
            f"❌ Минимальное количество: <b>{TP_ONLINE_SUBS_MIN}</b>",
        )
        return

    if quantity > TP_ONLINE_SUBS_MAX:
        await premium.answer_html(
            message,
            f"❌ Максимальное количество: <b>{TP_ONLINE_SUBS_MAX}</b>",
        )
        return

    data = await state.get_data()
    link = data["link"]
    price = _calc_price(quantity)

    user = db.get_user(message.from_user.id)
    balance = float(user["usdt_balance"] or 0.0) if user else 0.0

    await state.update_data(quantity=quantity, price=price)

    text = (
        "📦 <b>Подтверждение заказа</b>\n\n"
        "Услуга: <b>TG Онлайн премиум подписчики</b>\n"
        f"🔗 Ссылка: <code>{link}</code>\n"
        f"👥 Количество: <b>{quantity}</b>\n"
        f"💸 Сумма: <b>{price:.2f} USDT</b>\n"
        f"💰 Ваш баланс: <b>{balance:.2f} USDT</b>"
    )

    await premium.answer_html(
        message,
        text,
        reply_markup=tp_confirm_kb(),
    )

@router.message(PromotionStates.tp_comments_quantity)
async def tp_comments_get_quantity(
    message: Message,
    state: FSMContext,
    db: Database,
    premium: PremiumEmoji,
):
    raw = (message.text or "").strip()

    if not raw.isdigit():
        await premium.answer_html(message, "❌ Введите количество цифрами.")
        return

    quantity = int(raw)

    if quantity < TP_COMMENTS_MIN:
        await premium.answer_html(
            message,
            f"❌ Минимальное количество: <b>{TP_COMMENTS_MIN}</b>",
        )
        return

    if quantity > TP_COMMENTS_MAX:
        await premium.answer_html(
            message,
            f"❌ Максимальное количество: <b>{TP_COMMENTS_MAX}</b>",
        )
        return

    data = await state.get_data()
    link = data["link"]
    price = _calc_comments_price(quantity)

    user = db.get_user(message.from_user.id)
    balance = float(user["usdt_balance"] or 0.0) if user else 0.0

    await state.update_data(quantity=quantity, price=price)

    text = (
        "📦 <b>Подтверждение заказа</b>\n\n"
        "Услуга: <b>TG Премиум комментарии</b>\n"
        f"🔗 Ссылка: <code>{link}</code>\n"
        f"💬 Количество: <b>{quantity}</b>\n"
        f"💸 Сумма: <b>{price:.2f} USDT</b>\n"
        f"💰 Ваш баланс: <b>{balance:.2f} USDT</b>"
    )

    await premium.answer_html(
        message,
        text,
        reply_markup=tp_comments_confirm_kb(),
    )

@router.message(PromotionStates.tt_views_quantity)
async def tt_views_get_quantity(
    message: Message,
    state: FSMContext,
    db: Database,
    premium: PremiumEmoji,
):
    raw = (message.text or "").strip()

    if not raw.isdigit():
        await premium.answer_html(message, "❌ Введите количество цифрами.")
        return

    quantity = int(raw)

    if quantity < TT_VIEWS_MIN:
        await premium.answer_html(
            message,
            f"❌ Минимальное количество: <b>{TT_VIEWS_MIN}</b>",
        )
        return

    if quantity > TT_VIEWS_MAX:
        await premium.answer_html(
            message,
            f"❌ Максимальное количество: <b>{TT_VIEWS_MAX}</b>",
        )
        return

    data = await state.get_data()
    link = data["link"]
    price = _calc_tt_views_price(quantity)

    user = db.get_user(message.from_user.id)
    balance = float(user["usdt_balance"] or 0.0) if user else 0.0

    await state.update_data(quantity=quantity, price=price)

    text = (
        "📦 <b>Подтверждение заказа</b>\n\n"
        "Услуга: <b>TT Реальные просмотры</b>\n"
        f"🔗 Ссылка: <code>{link}</code>\n"
        f"👁 Количество: <b>{quantity}</b>\n"
        f"💸 Сумма: <b>{price:.2f} USDT</b>\n"
        f"💰 Ваш баланс: <b>{balance:.2f} USDT</b>"
    )

    await premium.answer_html(
        message,
        text,
        reply_markup=tt_views_confirm_kb(),
    )

@router.message(PromotionStates.tp_target_subs_quantity)
async def tp_target_subs_get_quantity(
    message: Message,
    state: FSMContext,
    db: Database,
    premium: PremiumEmoji,
):
    raw = (message.text or "").strip()

    if not raw.isdigit():
        await premium.answer_html(message, "❌ Введите количество цифрами.")
        return

    quantity = int(raw)

    if quantity < TP_TARGET_SUBS_MIN:
        await premium.answer_html(
            message,
            f"❌ Минимальное количество: <b>{TP_TARGET_SUBS_MIN}</b>",
        )
        return

    if quantity > TP_TARGET_SUBS_MAX:
        await premium.answer_html(
            message,
            f"❌ Максимальное количество: <b>{TP_TARGET_SUBS_MAX}</b>",
        )
        return

    data = await state.get_data()
    link = data["link"]
    price = _calc_target_subs_price(quantity)

    user = db.get_user(message.from_user.id)
    balance = float(user["usdt_balance"] or 0.0) if user else 0.0

    await state.update_data(quantity=quantity, price=price)

    text = (
        "📦 <b>Подтверждение заказа</b>\n\n"
        "Услуга: <b>TG 🇷🇺 Премиум подписчики (СНГ)</b>\n"
        f"🔗 Ссылка на пост: <code>{link}</code>\n"
        f"👥 Количество: <b>{quantity}</b>\n"
        f"💸 Сумма: <b>{price:.2f} USDT</b>\n"
        f"💰 Ваш баланс: <b>{balance:.2f} USDT</b>"
    )

    await premium.answer_html(
        message,
        text,
        reply_markup=tp_target_subs_confirm_kb(),
    )


@router.callback_query(F.data == "tp_cancel_order")
async def tp_cancel_order(call: CallbackQuery, state: FSMContext, premium: PremiumEmoji):
    await state.clear()
    await premium.answer_html(
        call.message,
        "❌ Заказ отменён.",
        reply_markup=tg_premium_services_kb(),
    )
    await call.answer()


@router.callback_query(F.data == "tp_online_subs_confirm")
async def tp_online_subs_confirm(
    call: CallbackQuery,
    state: FSMContext,
    db: Database,
    cfg,
    premium: PremiumEmoji,
):
    data = await state.get_data()
    if not data:
        await call.answer("Данные заказа потеряны", show_alert=True)
        return

    link = data["link"]
    quantity = int(data["quantity"])
    price = float(data["price"])

    user = db.get_user(call.from_user.id)
    if not user:
        await premium.answer_html(
            call.message,
            "❌ Пользователь не найден в базе.",
        )
        await call.answer()
        return

    ok = db.subtract_ref_balance(call.from_user.id, price)
    if not ok:
        actual_user = db.get_user(call.from_user.id)
        balance = float(actual_user["usdt_balance"] or 0.0) if actual_user else 0.0
        await premium.answer_html(
            call.message,
            "❌ <b>Недостаточно USDT на балансе.</b>\n\n"
            f"Нужно: <b>{price:.2f} USDT</b>\n"
            f"У вас: <b>{balance:.2f} USDT</b>",
        )
        await call.answer()
        return

    order_id = db.create_promotion_order(
        user_id=call.from_user.id,
        username=call.from_user.username or "",
        service_code="tp_online_subs",
        service_name="TG Онлайн премиум подписчики",
        link=link,
        quantity=quantity,
        price_usdt=price,
    )

    admin_text = (
        "📥 <b>Новая заявка на продвижение</b>\n\n"
        f"🆔 Заказ: <b>#{order_id}</b>\n"
        f"👤 Пользователь: <b>{call.from_user.full_name}</b>\n"
        f"🔹 Username: @{call.from_user.username or 'без username'}\n"
        f"🆔 TG ID: <code>{call.from_user.id}</code>\n\n"
        f"🛍 Услуга: <b>TG Онлайн премиум подписчики</b>\n"
        f"🔗 Ссылка: <code>{link}</code>\n"
        f"👥 Количество: <b>{quantity}</b>\n"
        f"💸 Оплачено: <b>{price:.2f} USDT</b>\n"
        f"📌 Статус: <b>new</b>"
    )

    try:
        await call.bot.send_message(
            cfg.ADMIN_ID,
            admin_text,
            parse_mode="HTML",
            reply_markup=promo_order_admin_kb(order_id),
        )
    except Exception:
        pass

    await state.clear()

    await premium.answer_html(
        call.message,
        "✅ <b>Заявка создана</b>\n\n"
        f"🆔 Номер заказа: <b>#{order_id}</b>\n"
        "Ваша заявка отправлена администратору.\n"
        "Средства списаны с USDT баланса.",
    )
    await call.answer()

@router.callback_query(F.data == "tt_likes_confirm")
async def tt_likes_confirm(
    call: CallbackQuery,
    state: FSMContext,
    db: Database,
    cfg,
    premium: PremiumEmoji,
):
    data = await state.get_data()
    if not data:
        await call.answer("Данные заказа потеряны", show_alert=True)
        return

    link = data["link"]
    quantity = int(data["quantity"])
    price = float(data["price"])

    user = db.get_user(call.from_user.id)
    if not user:
        await premium.answer_html(call.message, "❌ Пользователь не найден в базе.")
        await call.answer()
        return

    ok = db.subtract_ref_balance(call.from_user.id, price)
    if not ok:
        actual_user = db.get_user(call.from_user.id)
        balance = float(actual_user["usdt_balance"] or 0.0) if actual_user else 0.0
        await premium.answer_html(
            call.message,
            "❌ <b>Недостаточно USDT на балансе.</b>\n\n"
            f"Нужно: <b>{price:.2f} USDT</b>\n"
            f"У вас: <b>{balance:.2f} USDT</b>",
        )
        await call.answer()
        return

    order_id = db.create_promotion_order(
        user_id=call.from_user.id,
        username=call.from_user.username or "",
        service_code="tt_likes",
        service_name="TT Лайки живые (Ru)",
        link=link,
        quantity=quantity,
        price_usdt=price,
    )

    admin_text = (
        "📥 <b>Новая заявка на продвижение</b>\n\n"
        f"🆔 Заказ: <b>#{order_id}</b>\n"
        f"👤 Пользователь: <b>{call.from_user.full_name}</b>\n"
        f"🔹 Username TG: @{call.from_user.username or 'без username'}\n"
        f"🆔 TG ID: <code>{call.from_user.id}</code>\n\n"
        f"🛍 Услуга: <b>TT Лайки живые (Ru)</b>\n"
        f"🔗 Ссылка: <code>{link}</code>\n"
        f"❤️ Количество: <b>{quantity}</b>\n"
        f"💸 Оплачено: <b>{price:.2f} USDT</b>\n"
        f"📌 Статус: <b>new</b>"
    )

    try:
        await call.bot.send_message(
            cfg.ADMIN_ID,
            admin_text,
            parse_mode="HTML",
            reply_markup=promo_order_admin_kb(order_id),
        )
    except Exception:
        pass

    await state.clear()

    await premium.answer_html(
        call.message,
        "✅ <b>Заявка создана</b>\n\n"
        f"🆔 Номер заказа: <b>#{order_id}</b>\n"
        "Ваша заявка отправлена администратору.\n"
        "Средства списаны с USDT баланса.",
    )
    await call.answer()

@router.callback_query(F.data == "tt_views_confirm")
async def tt_views_confirm(
    call: CallbackQuery,
    state: FSMContext,
    db: Database,
    cfg,
    premium: PremiumEmoji,
):
    data = await state.get_data()
    if not data:
        await call.answer("Данные заказа потеряны", show_alert=True)
        return

    link = data["link"]
    quantity = int(data["quantity"])
    price = float(data["price"])

    user = db.get_user(call.from_user.id)
    if not user:
        await premium.answer_html(call.message, "❌ Пользователь не найден в базе.")
        await call.answer()
        return

    ok = db.subtract_ref_balance(call.from_user.id, price)
    if not ok:
        actual_user = db.get_user(call.from_user.id)
        balance = float(actual_user["usdt_balance"] or 0.0) if actual_user else 0.0
        await premium.answer_html(
            call.message,
            "❌ <b>Недостаточно USDT на балансе.</b>\n\n"
            f"Нужно: <b>{price:.2f} USDT</b>\n"
            f"У вас: <b>{balance:.2f} USDT</b>",
        )
        await call.answer()
        return

    order_id = db.create_promotion_order(
        user_id=call.from_user.id,
        username=call.from_user.username or "",
        service_code="tt_views",
        service_name="TT Реальные просмотры",
        link=link,
        quantity=quantity,
        price_usdt=price,
    )

    admin_text = (
        "📥 <b>Новая заявка на продвижение</b>\n\n"
        f"🆔 Заказ: <b>#{order_id}</b>\n"
        f"👤 Пользователь: <b>{call.from_user.full_name}</b>\n"
        f"🔹 Username TG: @{call.from_user.username or 'без username'}\n"
        f"🆔 TG ID: <code>{call.from_user.id}</code>\n\n"
        f"🛍 Услуга: <b>TT Реальные просмотры</b>\n"
        f"🔗 Ссылка: <code>{link}</code>\n"
        f"👁 Количество: <b>{quantity}</b>\n"
        f"💸 Оплачено: <b>{price:.2f} USDT</b>\n"
        f"📌 Статус: <b>new</b>"
    )

    try:
        await call.bot.send_message(
            cfg.ADMIN_ID,
            admin_text,
            parse_mode="HTML",
            reply_markup=promo_order_admin_kb(order_id),
        )
    except Exception:
        pass

    await state.clear()

    await premium.answer_html(
        call.message,
        "✅ <b>Заявка создана</b>\n\n"
        f"🆔 Номер заказа: <b>#{order_id}</b>\n"
        "Ваша заявка отправлена администратору.\n"
        "Средства списаны с USDT баланса.",
    )
    await call.answer()

@router.callback_query(F.data == "tt_live_confirm")
async def tt_live_confirm(call: CallbackQuery, state: FSMContext, db: Database, cfg, premium: PremiumEmoji):

    data = await state.get_data()

    link = data["link"]
    quantity = int(data["quantity"])
    price = float(data["price"])

    ok = db.subtract_ref_balance(call.from_user.id, price)

    if not ok:

        user = db.get_user(call.from_user.id)
        balance = float(user["usdt_balance"] or 0)

        await premium.answer_html(
            call.message,
            f"❌ <b>Недостаточно средств</b>\n\n"
            f"Нужно: <b>{price:.2f} USDT</b>\n"
            f"Баланс: <b>{balance:.2f} USDT</b>"
        )
        return

    order_id = db.create_promotion_order(
        user_id=call.from_user.id,
        username=call.from_user.username or "",
        service_code="tt_live",
        service_name="TikTok Прямой эфир",
        link=link,
        quantity=quantity,
        price_usdt=price,
    )

    admin_text = (
        "📥 <b>Новая заявка</b>\n\n"
        f"🆔 Заказ #{order_id}\n"
        f"👤 {call.from_user.full_name}\n"
        f"🆔 <code>{call.from_user.id}</code>\n\n"
        f"🛍 TikTok Прямой эфир\n"
        f"🔗 <code>{link}</code>\n"
        f"👥 {quantity}\n"
        f"💸 {price:.2f} USDT"
    )

    await call.bot.send_message(
        cfg.ADMIN_ID,
        admin_text,
        parse_mode="HTML",
        reply_markup=promo_order_admin_kb(order_id)
    )

    await state.clear()

    await premium.answer_html(
        call.message,
        f"✅ <b>Заявка создана</b>\n\n"
        f"Номер заказа: <b>#{order_id}</b>"
    )

    await call.answer()

@router.callback_query(F.data == "ig_provider_subs_confirm")
async def ig_provider_subs_confirm(
    call: CallbackQuery,
    state: FSMContext,
    db: Database,
    cfg,
    premium: PremiumEmoji,
):
    data = await state.get_data()
    if not data:
        await call.answer("Данные заказа потеряны", show_alert=True)
        return

    link = data["link"]
    quantity = int(data["quantity"])
    price = float(data["price"])

    user = db.get_user(call.from_user.id)
    if not user:
        await premium.answer_html(call.message, "❌ Пользователь не найден в базе.")
        await call.answer()
        return

    ok = db.subtract_ref_balance(call.from_user.id, price)
    if not ok:
        actual_user = db.get_user(call.from_user.id)
        balance = float(actual_user["usdt_balance"] or 0.0) if actual_user else 0.0
        await premium.answer_html(
            call.message,
            "❌ <b>Недостаточно USDT на балансе.</b>\n\n"
            f"Нужно: <b>{price:.2f} USDT</b>\n"
            f"У вас: <b>{balance:.2f} USDT</b>",
        )
        await call.answer()
        return

    order_id = db.create_promotion_order(
        user_id=call.from_user.id,
        username=call.from_user.username or "",
        service_code="ig_provider_subs",
        service_name="IG Верифицированные подписчики",
        link=link,
        quantity=quantity,
        price_usdt=price,
    )

    admin_text = (
        "📥 <b>Новая заявка на продвижение</b>\n\n"
        f"🆔 Заказ: <b>#{order_id}</b>\n"
        f"👤 Пользователь: <b>{call.from_user.full_name}</b>\n"
        f"🔹 Username TG: @{call.from_user.username or 'без username'}\n"
        f"🆔 TG ID: <code>{call.from_user.id}</code>\n\n"
        f"🛍 Услуга: <b>IG Верифицированные подписчики</b>\n"
        f"🔗 Ссылка: <code>{link}</code>\n"
        f"👥 Количество: <b>{quantity}</b>\n"
        f"💸 Оплачено: <b>{price:.2f} USDT</b>\n"
        f"📌 Статус: <b>new</b>"
    )

    try:
        await call.bot.send_message(
            cfg.ADMIN_ID,
            admin_text,
            parse_mode="HTML",
            reply_markup=promo_order_admin_kb(order_id),
        )
    except Exception:
        pass

    await state.clear()

    await premium.answer_html(
        call.message,
        "✅ <b>Заявка создана</b>\n\n"
        f"🆔 Номер заказа: <b>#{order_id}</b>\n"
        "Ваша заявка отправлена администратору.\n"
        "Средства списаны с USDT баланса.",
    )
    await call.answer()

@router.callback_query(F.data == "ig_target_subs_confirm")
async def ig_target_subs_confirm(
    call: CallbackQuery,
    state: FSMContext,
    db: Database,
    cfg,
    premium: PremiumEmoji,
):
    data = await state.get_data()
    if not data:
        await call.answer("Данные заказа потеряны", show_alert=True)
        return

    link = data["link"]
    quantity = int(data["quantity"])
    price = float(data["price"])

    user = db.get_user(call.from_user.id)
    if not user:
        await premium.answer_html(call.message, "❌ Пользователь не найден в базе.")
        await call.answer()
        return

    ok = db.subtract_ref_balance(call.from_user.id, price)
    if not ok:
        actual_user = db.get_user(call.from_user.id)
        balance = float(actual_user["usdt_balance"] or 0.0) if actual_user else 0.0
        await premium.answer_html(
            call.message,
            "❌ <b>Недостаточно USDT на балансе.</b>\n\n"
            f"Нужно: <b>{price:.2f} USDT</b>\n"
            f"У вас: <b>{balance:.2f} USDT</b>",
        )
        await call.answer()
        return

    order_id = db.create_promotion_order(
        user_id=call.from_user.id,
        username=call.from_user.username or "",
        service_code="ig_target_subs",
        service_name="IG Живые RU (плавные)",
        link=link,
        quantity=quantity,
        price_usdt=price,
    )

    admin_text = (
        "📥 <b>Новая заявка на продвижение</b>\n\n"
        f"🆔 Заказ: <b>#{order_id}</b>\n"
        f"👤 Пользователь: <b>{call.from_user.full_name}</b>\n"
        f"🔹 Username TG: @{call.from_user.username or 'без username'}\n"
        f"🆔 TG ID: <code>{call.from_user.id}</code>\n\n"
        f"🛍 Услуга: <b>IG Живые RU (плавные)</b>\n"
        f"🔗 Ссылка: <code>{link}</code>\n"
        f"👥 Количество: <b>{quantity}</b>\n"
        f"💸 Оплачено: <b>{price:.2f} USDT</b>\n"
        f"📌 Статус: <b>new</b>"
    )

    try:
        await call.bot.send_message(
            cfg.ADMIN_ID,
            admin_text,
            parse_mode="HTML",
            reply_markup=promo_order_admin_kb(order_id),
        )
    except Exception:
        pass

    await state.clear()

    await premium.answer_html(
        call.message,
        "✅ <b>Заявка создана</b>\n\n"
        f"🆔 Номер заказа: <b>#{order_id}</b>\n"
        "Ваша заявка отправлена администратору.\n"
        "Средства списаны с USDT баланса.",
    )
    await call.answer()

@router.callback_query(F.data == "ig_provider_likes_confirm")
async def ig_provider_likes_confirm(
    call: CallbackQuery,
    state: FSMContext,
    db: Database,
    cfg,
    premium: PremiumEmoji,
):
    data = await state.get_data()
    if not data:
        await call.answer("Данные заказа потеряны", show_alert=True)
        return

    link = data["link"]
    quantity = int(data["quantity"])
    price = float(data["price"])

    user = db.get_user(call.from_user.id)
    if not user:
        await premium.answer_html(call.message, "❌ Пользователь не найден в базе.")
        await call.answer()
        return

    ok = db.subtract_ref_balance(call.from_user.id, price)
    if not ok:
        actual_user = db.get_user(call.from_user.id)
        balance = float(actual_user["usdt_balance"] or 0.0) if actual_user else 0.0
        await premium.answer_html(
            call.message,
            "❌ <b>Недостаточно USDT на балансе.</b>\n\n"
            f"Нужно: <b>{price:.2f} USDT</b>\n"
            f"У вас: <b>{balance:.2f} USDT</b>",
        )
        await call.answer()
        return

    order_id = db.create_promotion_order(
        user_id=call.from_user.id,
        username=call.from_user.username or "",
        service_code="ig_provider_likes",
        service_name="IG Лайки плавные",
        link=link,
        quantity=quantity,
        price_usdt=price,
    )

    admin_text = (
        "📥 <b>Новая заявка на продвижение</b>\n\n"
        f"🆔 Заказ: <b>#{order_id}</b>\n"
        f"👤 Пользователь: <b>{call.from_user.full_name}</b>\n"
        f"🔹 Username TG: @{call.from_user.username or 'без username'}\n"
        f"🆔 TG ID: <code>{call.from_user.id}</code>\n\n"
        f"🛍 Услуга: <b>IG Лайки плавные</b>\n"
        f"🔗 Ссылка: <code>{link}</code>\n"
        f"❤️ Количество: <b>{quantity}</b>\n"
        f"💸 Оплачено: <b>{price:.2f} USDT</b>\n"
        f"📌 Статус: <b>new</b>"
    )

    try:
        await call.bot.send_message(
            cfg.ADMIN_ID,
            admin_text,
            parse_mode="HTML",
            reply_markup=promo_order_admin_kb(order_id),
        )
    except Exception:
        pass

    await state.clear()

    await premium.answer_html(
        call.message,
        "✅ <b>Заявка создана</b>\n\n"
        f"🆔 Номер заказа: <b>#{order_id}</b>\n"
        "Ваша заявка отправлена администратору.\n"
        "Средства списаны с USDT баланса.",
    )
    await call.answer()

@router.callback_query(F.data == "ig_comments_confirm")
async def ig_comments_confirm(
    call: CallbackQuery,
    state: FSMContext,
    db: Database,
    cfg,
    premium: PremiumEmoji,
):
    data = await state.get_data()
    if not data:
        await call.answer("Данные заказа потеряны", show_alert=True)
        return

    link = data["link"]
    quantity = int(data["quantity"])
    price = float(data["price"])

    user = db.get_user(call.from_user.id)
    if not user:
        await premium.answer_html(call.message, "❌ Пользователь не найден в базе.")
        await call.answer()
        return

    ok = db.subtract_ref_balance(call.from_user.id, price)
    if not ok:
        actual_user = db.get_user(call.from_user.id)
        balance = float(actual_user["usdt_balance"] or 0.0) if actual_user else 0.0
        await premium.answer_html(
            call.message,
            "❌ <b>Недостаточно USDT на балансе.</b>\n\n"
            f"Нужно: <b>{price:.2f} USDT</b>\n"
            f"У вас: <b>{balance:.2f} USDT</b>",
        )
        await call.answer()
        return

    order_id = db.create_promotion_order(
        user_id=call.from_user.id,
        username=call.from_user.username or "",
        service_code="ig_comments",
        service_name="IG Комментарии живые",
        link=link,
        quantity=quantity,
        price_usdt=price,
    )

    admin_text = (
        "📥 <b>Новая заявка на продвижение</b>\n\n"
        f"🆔 Заказ: <b>#{order_id}</b>\n"
        f"👤 Пользователь: <b>{call.from_user.full_name}</b>\n"
        f"🔹 Username TG: @{call.from_user.username or 'без username'}\n"
        f"🆔 TG ID: <code>{call.from_user.id}</code>\n\n"
        f"🛍 Услуга: <b>IG Комментарии живые</b>\n"
        f"🔗 Ссылка: <code>{link}</code>\n"
        f"💬 Количество: <b>{quantity}</b>\n"
        f"💸 Оплачено: <b>{price:.2f} USDT</b>\n"
        f"📌 Статус: <b>new</b>"
    )

    try:
        await call.bot.send_message(
            cfg.ADMIN_ID,
            admin_text,
            parse_mode="HTML",
            reply_markup=promo_order_admin_kb(order_id),
        )
    except Exception:
        pass

    await state.clear()

    await premium.answer_html(
        call.message,
        "✅ <b>Заявка создана</b>\n\n"
        f"🆔 Номер заказа: <b>#{order_id}</b>\n"
        "Ваша заявка отправлена администратору.\n"
        "Средства списаны с USDT баланса.",
    )
    await call.answer()

@router.callback_query(F.data == "ig_stories_confirm")
async def ig_stories_confirm(
    call: CallbackQuery,
    state: FSMContext,
    db: Database,
    cfg,
    premium: PremiumEmoji,
):
    data = await state.get_data()
    if not data:
        await call.answer("Данные заказа потеряны", show_alert=True)
        return

    username = data["username"]
    quantity = int(data["quantity"])
    price = float(data["price"])

    user = db.get_user(call.from_user.id)
    if not user:
        await premium.answer_html(
            call.message,
            "❌ Пользователь не найден в базе.",
        )
        await call.answer()
        return

    ok = db.subtract_ref_balance(call.from_user.id, price)
    if not ok:
        actual_user = db.get_user(call.from_user.id)
        balance = float(actual_user["usdt_balance"] or 0.0) if actual_user else 0.0
        await premium.answer_html(
            call.message,
            "❌ <b>Недостаточно USDT на балансе.</b>\n\n"
            f"Нужно: <b>{price:.2f} USDT</b>\n"
            f"У вас: <b>{balance:.2f} USDT</b>",
        )
        await call.answer()
        return

    order_id = db.create_promotion_order(
        user_id=call.from_user.id,
        username=call.from_user.username or "",
        service_code="ig_stories",
        service_name="IG Просмотры историй",
        link=username,
        quantity=quantity,
        price_usdt=price,
    )

    admin_text = (
        "📥 <b>Новая заявка на продвижение</b>\n\n"
        f"🆔 Заказ: <b>#{order_id}</b>\n"
        f"👤 Пользователь: <b>{call.from_user.full_name}</b>\n"
        f"🔹 Username TG: @{call.from_user.username or 'без username'}\n"
        f"🆔 TG ID: <code>{call.from_user.id}</code>\n\n"
        f"🛍 Услуга: <b>IG Просмотры историй</b>\n"
        f"👤 Instagram username: <code>{username}</code>\n"
        f"👁 Количество: <b>{quantity}</b>\n"
        f"💸 Оплачено: <b>{price:.2f} USDT</b>\n"
        f"📌 Статус: <b>new</b>"
    )

    try:
        await call.bot.send_message(
            cfg.ADMIN_ID,
            admin_text,
            parse_mode="HTML",
            reply_markup=promo_order_admin_kb(order_id),
        )
    except Exception:
        pass

    await state.clear()

    await premium.answer_html(
        call.message,
        "✅ <b>Заявка создана</b>\n\n"
        f"🆔 Номер заказа: <b>#{order_id}</b>\n"
        "Ваша заявка отправлена администратору.\n"
        "Средства списаны с USDT баланса.",
    )
    await call.answer()

@router.callback_query(F.data == "tg_provider_reactions_confirm")
async def tg_provider_reactions_confirm(
    call: CallbackQuery,
    state: FSMContext,
    db: Database,
    cfg,
    premium: PremiumEmoji,
):
    data = await state.get_data()
    if not data:
        await call.answer("Данные заказа потеряны", show_alert=True)
        return

    link = data["link"]
    quantity = int(data["quantity"])
    price = float(data["price"])

    user = db.get_user(call.from_user.id)
    if not user:
        await premium.answer_html(
            call.message,
            "❌ Пользователь не найден в базе.",
        )
        await call.answer()
        return

    ok = db.subtract_ref_balance(call.from_user.id, price)
    if not ok:
        actual_user = db.get_user(call.from_user.id)
        balance = float(actual_user["usdt_balance"] or 0.0) if actual_user else 0.0
        await premium.answer_html(
            call.message,
            "❌ <b>Недостаточно USDT на балансе.</b>\n\n"
            f"Нужно: <b>{price:.2f} USDT</b>\n"
            f"У вас: <b>{balance:.2f} USDT</b>",
        )
        await call.answer()
        return

    order_id = db.create_promotion_order(
        user_id=call.from_user.id,
        username=call.from_user.username or "",
        service_code="tg_provider_reactions",
        service_name="TG Кастомные реакции под постом",
        link=link,
        quantity=quantity,
        price_usdt=price,
    )

    admin_text = (
        "📥 <b>Новая заявка на продвижение</b>\n\n"
        f"🆔 Заказ: <b>#{order_id}</b>\n"
        f"👤 Пользователь: <b>{call.from_user.full_name}</b>\n"
        f"🔹 Username: @{call.from_user.username or 'без username'}\n"
        f"🆔 TG ID: <code>{call.from_user.id}</code>\n\n"
        f"🛍 Услуга: <b>TG Кастомные реакции под постом</b>\n"
        f"🔗 Ссылка на пост: <code>{link}</code>\n"
        f"❤️ Количество: <b>{quantity}</b>\n"
        f"💸 Оплачено: <b>{price:.2f} USDT</b>\n"
        f"📌 Статус: <b>new</b>"
    )

    try:
        await call.bot.send_message(
            cfg.ADMIN_ID,
            admin_text,
            parse_mode="HTML",
            reply_markup=promo_order_admin_kb(order_id),
        )
    except Exception:
        pass

    await state.clear()

    await premium.answer_html(
        call.message,
        "✅ <b>Заявка создана</b>\n\n"
        f"🆔 Номер заказа: <b>#{order_id}</b>\n"
        "Ваша заявка отправлена администратору.\n"
        "Средства списаны с USDT баланса.",
    )
    await call.answer()

@router.callback_query(F.data == "tg_provider_views_confirm")
async def tg_provider_views_confirm(
    call: CallbackQuery,
    state: FSMContext,
    db: Database,
    cfg,
    premium: PremiumEmoji,
):
    data = await state.get_data()
    if not data:
        await call.answer("Данные заказа потеряны", show_alert=True)
        return

    link = data["link"]
    quantity = int(data["quantity"])
    price = float(data["price"])

    user = db.get_user(call.from_user.id)
    if not user:
        await premium.answer_html(
            call.message,
            "❌ Пользователь не найден в базе.",
        )
        await call.answer()
        return

    ok = db.subtract_ref_balance(call.from_user.id, price)
    if not ok:
        actual_user = db.get_user(call.from_user.id)
        balance = float(actual_user["usdt_balance"] or 0.0) if actual_user else 0.0
        await premium.answer_html(
            call.message,
            "❌ <b>Недостаточно USDT на балансе.</b>\n\n"
            f"Нужно: <b>{price:.2f} USDT</b>\n"
            f"У вас: <b>{balance:.2f} USDT</b>",
        )
        await call.answer()
        return

    order_id = db.create_promotion_order(
        user_id=call.from_user.id,
        username=call.from_user.username or "",
        service_code="tg_provider_views",
        service_name="TG Моментальные просмотры",
        link=link,
        quantity=quantity,
        price_usdt=price,
    )

    admin_text = (
        "📥 <b>Новая заявка на продвижение</b>\n\n"
        f"🆔 Заказ: <b>#{order_id}</b>\n"
        f"👤 Пользователь: <b>{call.from_user.full_name}</b>\n"
        f"🔹 Username: @{call.from_user.username or 'без username'}\n"
        f"🆔 TG ID: <code>{call.from_user.id}</code>\n\n"
        f"🛍 Услуга: <b>TG Моментальные просмотры</b>\n"
        f"🔗 Ссылка на пост: <code>{link}</code>\n"
        f"👁 Количество: <b>{quantity}</b>\n"
        f"💸 Оплачено: <b>{price:.2f} USDT</b>\n"
        f"📌 Статус: <b>new</b>"
    )

    try:
        await call.bot.send_message(
            cfg.ADMIN_ID,
            admin_text,
            parse_mode="HTML",
            reply_markup=promo_order_admin_kb(order_id),
        )
    except Exception:
        pass

    await state.clear()

    await premium.answer_html(
        call.message,
        "✅ <b>Заявка создана</b>\n\n"
        f"🆔 Номер заказа: <b>#{order_id}</b>\n"
        "Ваша заявка отправлена администратору.\n"
        "Средства списаны с USDT баланса.",
    )
    await call.answer()

@router.callback_query(F.data == "tg_provider_subs_confirm")
async def tg_provider_subs_confirm(
    call: CallbackQuery,
    state: FSMContext,
    db: Database,
    cfg,
    premium: PremiumEmoji,
):
    data = await state.get_data()
    if not data:
        await call.answer("Данные заказа потеряны", show_alert=True)
        return

    link = data["link"]
    quantity = int(data["quantity"])
    price = float(data["price"])

    user = db.get_user(call.from_user.id)
    if not user:
        await premium.answer_html(
            call.message,
            "❌ Пользователь не найден в базе.",
        )
        await call.answer()
        return

    ok = db.subtract_ref_balance(call.from_user.id, price)
    if not ok:
        actual_user = db.get_user(call.from_user.id)
        balance = float(actual_user["usdt_balance"] or 0.0) if actual_user else 0.0
        await premium.answer_html(
            call.message,
            "❌ <b>Недостаточно USDT на балансе.</b>\n\n"
            f"Нужно: <b>{price:.2f} USDT</b>\n"
            f"У вас: <b>{balance:.2f} USDT</b>",
        )
        await call.answer()
        return

    order_id = db.create_promotion_order(
        user_id=call.from_user.id,
        username=call.from_user.username or "",
        service_code="tg_provider_subs",
        service_name="TG Быстрые подписчики без списаний",
        link=link,
        quantity=quantity,
        price_usdt=price,
    )

    admin_text = (
        "📥 <b>Новая заявка на продвижение</b>\n\n"
        f"🆔 Заказ: <b>#{order_id}</b>\n"
        f"👤 Пользователь: <b>{call.from_user.full_name}</b>\n"
        f"🔹 Username: @{call.from_user.username or 'без username'}\n"
        f"🆔 TG ID: <code>{call.from_user.id}</code>\n\n"
        f"🛍 Услуга: <b>TG Быстрые подписчики без списаний</b>\n"
        f"🔗 Ссылка: <code>{link}</code>\n"
        f"👥 Количество: <b>{quantity}</b>\n"
        f"💸 Оплачено: <b>{price:.2f} USDT</b>\n"
        f"📌 Статус: <b>new</b>"
    )

    try:
        await call.bot.send_message(
            cfg.ADMIN_ID,
            admin_text,
            parse_mode="HTML",
            reply_markup=promo_order_admin_kb(order_id),
        )
    except Exception:
        pass

    await state.clear()

    await premium.answer_html(
        call.message,
        "✅ <b>Заявка создана</b>\n\n"
        f"🆔 Номер заказа: <b>#{order_id}</b>\n"
        "Ваша заявка отправлена администратору.\n"
        "Средства списаны с USDT баланса.",
    )
    await call.answer()

@router.callback_query(F.data == "tg_ru_subs_confirm")
async def tg_ru_subs_confirm(
    call: CallbackQuery,
    state: FSMContext,
    db: Database,
    cfg,
    premium: PremiumEmoji,
):
    data = await state.get_data()
    if not data:
        await call.answer("Данные заказа потеряны", show_alert=True)
        return

    link = data["link"]
    quantity = int(data["quantity"])
    price = float(data["price"])

    user = db.get_user(call.from_user.id)
    if not user:
        await premium.answer_html(
            call.message,
            "❌ Пользователь не найден в базе.",
        )
        await call.answer()
        return

    ok = db.subtract_ref_balance(call.from_user.id, price)
    if not ok:
        actual_user = db.get_user(call.from_user.id)
        balance = float(actual_user["usdt_balance"] or 0.0) if actual_user else 0.0
        await premium.answer_html(
            call.message,
            "❌ <b>Недостаточно USDT на балансе.</b>\n\n"
            f"Нужно: <b>{price:.2f} USDT</b>\n"
            f"У вас: <b>{balance:.2f} USDT</b>",
        )
        await call.answer()
        return

    order_id = db.create_promotion_order(
        user_id=call.from_user.id,
        username=call.from_user.username or "",
        service_code="tg_ru_subs",
        service_name="TG Русские подписчики",
        link=link,
        quantity=quantity,
        price_usdt=price,
    )

    admin_text = (
        "📥 <b>Новая заявка на продвижение</b>\n\n"
        f"🆔 Заказ: <b>#{order_id}</b>\n"
        f"👤 Пользователь: <b>{call.from_user.full_name}</b>\n"
        f"🔹 Username: @{call.from_user.username or 'без username'}\n"
        f"🆔 TG ID: <code>{call.from_user.id}</code>\n\n"
        f"🛍 Услуга: <b>TG Русские подписчики</b>\n"
        f"🔗 Ссылка: <code>{link}</code>\n"
        f"👥 Количество: <b>{quantity}</b>\n"
        f"💸 Оплачено: <b>{price:.2f} USDT</b>\n"
        f"📌 Статус: <b>new</b>"
    )

    try:
        await call.bot.send_message(
            cfg.ADMIN_ID,
            admin_text,
            parse_mode="HTML",
            reply_markup=promo_order_admin_kb(order_id),
        )
    except Exception:
        pass

    await state.clear()

    await premium.answer_html(
        call.message,
        "✅ <b>Заявка создана</b>\n\n"
        f"🆔 Номер заказа: <b>#{order_id}</b>\n"
        "Ваша заявка отправлена администратору.\n"
        "Средства списаны с USDT баланса.",
    )
    await call.answer()

@router.callback_query(F.data == "tp_ru_online_subs_confirm")
async def tp_ru_online_subs_confirm(
        call: CallbackQuery,
        state: FSMContext,
        db: Database,
        cfg,
        premium: PremiumEmoji,
):
    data = await state.get_data()
    if not data:
        await call.answer("Данные заказа потеряны", show_alert=True)
        return

    link = data["link"]
    quantity = int(data["quantity"])
    price = float(data["price"])

    user = db.get_user(call.from_user.id)
    if not user:
        await premium.answer_html(
            call.message,
            "❌ Пользователь не найден в базе.",
        )
        await call.answer()
        return

    ok = db.subtract_ref_balance(call.from_user.id, price)
    if not ok:
        actual_user = db.get_user(call.from_user.id)
        balance = float(actual_user["usdt_balance"] or 0.0) if actual_user else 0.0
        await premium.answer_html(
            call.message,
            "❌ <b>Недостаточно USDT на балансе.</b>\n\n"
            f"Нужно: <b>{price:.2f} USDT</b>\n"
            f"У вас: <b>{balance:.2f} USDT</b>",
        )
        await call.answer()
        return

    order_id = db.create_promotion_order(
        user_id=call.from_user.id,
        username=call.from_user.username or "",
        service_code="tp_ru_online_subs",
        service_name="TG 🇷🇺 Русские премиум подписчики",
        link=link,
        quantity=quantity,
        price_usdt=price,
    )

    admin_text = (
        "📥 <b>Новая заявка на продвижение</b>\n\n"
        f"🆔 Заказ: <b>#{order_id}</b>\n"
        f"👤 Пользователь: <b>{call.from_user.full_name}</b>\n"
        f"🔹 Username: @{call.from_user.username or 'без username'}\n"
        f"🆔 TG ID: <code>{call.from_user.id}</code>\n\n"
        f"🛍 Услуга: <b>TG 🇷🇺 Русские премиум подписчики</b>\n"
        f"🔗 Ссылка: <code>{link}</code>\n"
        f"👥 Количество: <b>{quantity}</b>\n"
        f"💸 Оплачено: <b>{price:.2f} USDT</b>\n"
        f"📌 Статус: <b>new</b>"
    )

    try:
        await call.bot.send_message(
            cfg.ADMIN_ID,
            admin_text,
            parse_mode="HTML",
            reply_markup=promo_order_admin_kb(order_id),
        )
    except Exception:
        pass

    await state.clear()

    await premium.answer_html(
        call.message,
        "✅ <b>Заявка создана</b>\n\n"
        f"🆔 Номер заказа: <b>#{order_id}</b>\n"
        "Ваша заявка отправлена администратору.\n"
        "Средства списаны с USDT баланса.",
    )
    await call.answer()

@router.callback_query(F.data == "tp_target_subs_confirm")
async def tp_target_subs_confirm(
    call: CallbackQuery,
    state: FSMContext,
    db: Database,
    cfg,
    premium: PremiumEmoji,
):
    data = await state.get_data()
    if not data:
        await call.answer("Данные заказа потеряны", show_alert=True)
        return

    link = data["link"]
    quantity = int(data["quantity"])
    price = float(data["price"])

    user = db.get_user(call.from_user.id)
    if not user:
        await premium.answer_html(
            call.message,
            "❌ Пользователь не найден в базе.",
        )
        await call.answer()
        return

    ok = db.subtract_ref_balance(call.from_user.id, price)
    if not ok:
        actual_user = db.get_user(call.from_user.id)
        balance = float(actual_user["usdt_balance"] or 0.0) if actual_user else 0.0
        await premium.answer_html(
            call.message,
            "❌ <b>Недостаточно USDT на балансе.</b>\n\n"
            f"Нужно: <b>{price:.2f} USDT</b>\n"
            f"У вас: <b>{balance:.2f} USDT</b>",
        )
        await call.answer()
        return

    order_id = db.create_promotion_order(
        user_id=call.from_user.id,
        username=call.from_user.username or "",
        service_code="tp_target_subs",
        service_name="TG 🇷🇺 Премиум подписчики (СНГ)",
        link=link,
        quantity=quantity,
        price_usdt=price,
    )

    admin_text = (
        "📥 <b>Новая заявка на продвижение</b>\n\n"
        f"🆔 Заказ: <b>#{order_id}</b>\n"
        f"👤 Пользователь: <b>{call.from_user.full_name}</b>\n"
        f"🔹 Username: @{call.from_user.username or 'без username'}\n"
        f"🆔 TG ID: <code>{call.from_user.id}</code>\n\n"
        f"🛍 Услуга: <b>TG 🇷🇺 Премиум подписчики (СНГ)</b>\n"
        f"🔗 Ссылка на пост: <code>{link}</code>\n"
        f"👥 Количество: <b>{quantity}</b>\n"
        f"💸 Оплачено: <b>{price:.2f} USDT</b>\n"
        f"📌 Статус: <b>new</b>"
    )

    try:
        await call.bot.send_message(
            cfg.ADMIN_ID,
            admin_text,
            parse_mode="HTML",
            reply_markup=promo_order_admin_kb(order_id),
        )
    except Exception:
        pass

    await state.clear()

    await premium.answer_html(
        call.message,
        "✅ <b>Заявка создана</b>\n\n"
        f"🆔 Номер заказа: <b>#{order_id}</b>\n"
        "Ваша заявка отправлена администратору.\n"
        "Средства списаны с USDT баланса.",
    )
    await call.answer()

@router.callback_query(F.data == "tp_comments_confirm")
async def tp_comments_confirm(
    call: CallbackQuery,
    state: FSMContext,
    db: Database,
    cfg,
    premium: PremiumEmoji,
):
    data = await state.get_data()
    if not data:
        await call.answer("Данные заказа потеряны", show_alert=True)
        return

    link = data["link"]
    quantity = int(data["quantity"])
    price = float(data["price"])

    user = db.get_user(call.from_user.id)
    if not user:
        await premium.answer_html(
            call.message,
            "❌ Пользователь не найден в базе.",
        )
        await call.answer()
        return

    ok = db.subtract_ref_balance(call.from_user.id, price)
    if not ok:
        actual_user = db.get_user(call.from_user.id)
        balance = float(actual_user["usdt_balance"] or 0.0) if actual_user else 0.0
        await premium.answer_html(
            call.message,
            "❌ <b>Недостаточно USDT на балансе.</b>\n\n"
            f"Нужно: <b>{price:.2f} USDT</b>\n"
            f"У вас: <b>{balance:.2f} USDT</b>",
        )
        await call.answer()
        return

    order_id = db.create_promotion_order(
        user_id=call.from_user.id,
        username=call.from_user.username or "",
        service_code="tp_comments",
        service_name="TG Премиум комментарии",
        link=link,
        quantity=quantity,
        price_usdt=price,
    )

    admin_text = (
        "📥 <b>Новая заявка на продвижение</b>\n\n"
        f"🆔 Заказ: <b>#{order_id}</b>\n"
        f"👤 Пользователь: <b>{call.from_user.full_name}</b>\n"
        f"🔹 Username: @{call.from_user.username or 'без username'}\n"
        f"🆔 TG ID: <code>{call.from_user.id}</code>\n\n"
        f"🛍 Услуга: <b>TG Премиум комментарии</b>\n"
        f"🔗 Ссылка: <code>{link}</code>\n"
        f"💬 Количество: <b>{quantity}</b>\n"
        f"💸 Оплачено: <b>{price:.2f} USDT</b>\n"
        f"📌 Статус: <b>new</b>"
    )

    try:
        await call.bot.send_message(
            cfg.ADMIN_ID,
            admin_text,
            parse_mode="HTML",
            reply_markup=promo_order_admin_kb(order_id),
        )
    except Exception:
        pass

    await state.clear()

    await premium.answer_html(
        call.message,
        "✅ <b>Заявка создана</b>\n\n"
        f"🆔 Номер заказа: <b>#{order_id}</b>\n"
        "Ваша заявка отправлена администратору.\n"
        "Средства списаны с USDT баланса.",
    )
    await call.answer()

@router.callback_query(F.data == "tp_target_views_confirm")
async def tp_target_views_confirm(
    call: CallbackQuery,
    state: FSMContext,
    db: Database,
    cfg,
    premium: PremiumEmoji,
):
    data = await state.get_data()
    if not data:
        await call.answer("Данные заказа потеряны", show_alert=True)
        return

    link = data["link"]
    quantity = int(data["quantity"])
    price = float(data["price"])

    user = db.get_user(call.from_user.id)
    if not user:
        await premium.answer_html(
            call.message,
            "❌ Пользователь не найден в базе.",
        )
        await call.answer()
        return

    ok = db.subtract_ref_balance(call.from_user.id, price)
    if not ok:
        actual_user = db.get_user(call.from_user.id)
        balance = float(actual_user["usdt_balance"] or 0.0) if actual_user else 0.0
        await premium.answer_html(
            call.message,
            "❌ <b>Недостаточно USDT на балансе.</b>\n\n"
            f"Нужно: <b>{price:.2f} USDT</b>\n"
            f"У вас: <b>{balance:.2f} USDT</b>",
        )
        await call.answer()
        return

    order_id = db.create_promotion_order(
        user_id=call.from_user.id,
        username=call.from_user.username or "",
        service_code="tp_target_views",
        service_name="TG 🇷🇺 Премиум просмотры со статистикой",
        link=link,
        quantity=quantity,
        price_usdt=price,
    )

    admin_text = (
        "📥 <b>Новая заявка на продвижение</b>\n\n"
        f"🆔 Заказ: <b>#{order_id}</b>\n"
        f"👤 Пользователь: <b>{call.from_user.full_name}</b>\n"
        f"🔹 Username: @{call.from_user.username or 'без username'}\n"
        f"🆔 TG ID: <code>{call.from_user.id}</code>\n\n"
        f"🛍 Услуга: <b>TG 🇷🇺 Премиум просмотры со статистикой</b>\n"
        f"🔗 Ссылка на пост: <code>{link}</code>\n"
        f"👁 Количество: <b>{quantity}</b>\n"
        f"💸 Оплачено: <b>{price:.2f} USDT</b>\n"
        f"📌 Статус: <b>new</b>"
    )

    try:
        await call.bot.send_message(
            cfg.ADMIN_ID,
            admin_text,
            parse_mode="HTML",
            reply_markup=promo_order_admin_kb(order_id),
        )
    except Exception:
        pass

    await state.clear()

    await premium.answer_html(
        call.message,
        "✅ <b>Заявка создана</b>\n\n"
        f"🆔 Номер заказа: <b>#{order_id}</b>\n"
        "Ваша заявка отправлена администратору.\n"
        "Средства списаны с USDT баланса.",
    )
    await call.answer()

@router.callback_query(F.data == "tg_comments_confirm")
async def tg_comments_confirm(
    call: CallbackQuery,
    state: FSMContext,
    db: Database,
    cfg,
    premium: PremiumEmoji,
):
    data = await state.get_data()
    if not data:
        await call.answer("Данные заказа потеряны", show_alert=True)
        return

    link = data["link"]
    quantity = int(data["quantity"])
    price = float(data["price"])

    user = db.get_user(call.from_user.id)
    if not user:
        await premium.answer_html(
            call.message,
            "❌ Пользователь не найден в базе.",
        )
        await call.answer()
        return

    ok = db.subtract_ref_balance(call.from_user.id, price)
    if not ok:
        actual_user = db.get_user(call.from_user.id)
        balance = float(actual_user["usdt_balance"] or 0.0) if actual_user else 0.0
        await premium.answer_html(
            call.message,
            "❌ <b>Недостаточно USDT на балансе.</b>\n\n"
            f"Нужно: <b>{price:.2f} USDT</b>\n"
            f"У вас: <b>{balance:.2f} USDT</b>",
        )
        await call.answer()
        return

    order_id = db.create_promotion_order(
        user_id=call.from_user.id,
        username=call.from_user.username or "",
        service_code="tg_comments",
        service_name="TG Русские комментарии",
        link=link,
        quantity=quantity,
        price_usdt=price,
    )

    admin_text = (
        "📥 <b>Новая заявка на продвижение</b>\n\n"
        f"🆔 Заказ: <b>#{order_id}</b>\n"
        f"👤 Пользователь: <b>{call.from_user.full_name}</b>\n"
        f"🔹 Username: @{call.from_user.username or 'без username'}\n"
        f"🆔 TG ID: <code>{call.from_user.id}</code>\n\n"
        f"🛍 Услуга: <b>TG Русские комментарии</b>\n"
        f"🔗 Ссылка на пост: <code>{link}</code>\n"
        f"💬 Количество: <b>{quantity}</b>\n"
        f"💸 Оплачено: <b>{price:.2f} USDT</b>\n"
        f"📌 Статус: <b>new</b>"
    )

    try:
        await call.bot.send_message(
            cfg.ADMIN_ID,
            admin_text,
            parse_mode="HTML",
            reply_markup=promo_order_admin_kb(order_id),
        )
    except Exception:
        pass

    await state.clear()

    await premium.answer_html(
        call.message,
        "✅ <b>Заявка создана</b>\n\n"
        f"🆔 Номер заказа: <b>#{order_id}</b>\n"
        "Ваша заявка отправлена администратору.\n"
        "Средства списаны с USDT баланса.",
    )
    await call.answer()

@router.callback_query(F.data == "tt_provider_subs_confirm")
async def tt_provider_subs_confirm(
    call: CallbackQuery,
    state: FSMContext,
    db: Database,
    cfg,
    premium: PremiumEmoji,
):
    data = await state.get_data()
    if not data:
        await call.answer("Данные заказа потеряны", show_alert=True)
        return

    link = data["link"]
    quantity = int(data["quantity"])
    price = float(data["price"])

    user = db.get_user(call.from_user.id)
    if not user:
        await premium.answer_html(call.message, "❌ Пользователь не найден в базе.")
        await call.answer()
        return

    ok = db.subtract_ref_balance(call.from_user.id, price)
    if not ok:
        actual_user = db.get_user(call.from_user.id)
        balance = float(actual_user["usdt_balance"] or 0.0) if actual_user else 0.0
        await premium.answer_html(
            call.message,
            "❌ <b>Недостаточно USDT на балансе.</b>\n\n"
            f"Нужно: <b>{price:.2f} USDT</b>\n"
            f"У вас: <b>{balance:.2f} USDT</b>",
        )
        await call.answer()
        return

    order_id = db.create_promotion_order(
        user_id=call.from_user.id,
        username=call.from_user.username or "",
        service_code="tt_provider_subs",
        service_name="TT Живые подписчики (RU)",
        link=link,
        quantity=quantity,
        price_usdt=price,
    )

    admin_text = (
        "📥 <b>Новая заявка на продвижение</b>\n\n"
        f"🆔 Заказ: <b>#{order_id}</b>\n"
        f"👤 Пользователь: <b>{call.from_user.full_name}</b>\n"
        f"🔹 Username TG: @{call.from_user.username or 'без username'}\n"
        f"🆔 TG ID: <code>{call.from_user.id}</code>\n\n"
        f"🛍 Услуга: <b>TT Живые подписчики (RU)</b>\n"
        f"🔗 Ссылка: <code>{link}</code>\n"
        f"👥 Количество: <b>{quantity}</b>\n"
        f"💸 Оплачено: <b>{price:.2f} USDT</b>\n"
        f"📌 Статус: <b>new</b>"
    )

    try:
        await call.bot.send_message(
            cfg.ADMIN_ID,
            admin_text,
            parse_mode="HTML",
            reply_markup=promo_order_admin_kb(order_id),
        )
    except Exception:
        pass

    await state.clear()

    await premium.answer_html(
        call.message,
        "✅ <b>Заявка создана</b>\n\n"
        f"🆔 Номер заказа: <b>#{order_id}</b>\n"
        "Ваша заявка отправлена администратору.\n"
        "Средства списаны с USDT баланса.",
    )
    await call.answer()

@router.callback_query(F.data.startswith("promo_done:"))
async def promo_done(call: CallbackQuery, db: Database, cfg, premium: PremiumEmoji):
    if call.from_user.id != int(cfg.ADMIN_ID):
        await call.answer("Нет доступа", show_alert=True)
        return

    order_id = int(call.data.split(":")[1])
    order = db.get_promotion_order(order_id)

    if not order:
        await call.answer("Заявка не найдена", show_alert=True)
        return

    if order["status"] != "new":
        await call.answer("Заявка уже обработана", show_alert=True)
        return

    db.set_promotion_order_status(order_id, "done")

    try:
        await call.bot.send_message(
            order["user_id"],
            "✅ <b>Ваша заявка принята. Ожидайте выполнения.</b>\n\nЕсли вас что-то не устроит, напишите администратору: @illy228",
            parse_mode="HTML",
        )
    except Exception:
        pass

    await call.message.edit_reply_markup(reply_markup=None)
    await premium.answer_html(
        call.message,
        f"✅ Заявка <b>#{order_id}</b> отмечена как выполненная.",
    )
    await call.answer("Готово")


@router.callback_query(F.data.startswith("promo_reject:"))
async def promo_reject(call: CallbackQuery, db: Database, cfg, premium: PremiumEmoji):
    if call.from_user.id != int(cfg.ADMIN_ID):
        await call.answer("Нет доступа", show_alert=True)
        return

    order_id = int(call.data.split(":")[1])
    order = db.get_promotion_order(order_id)

    if not order:
        await call.answer("Заявка не найдена", show_alert=True)
        return

    if order["status"] != "new":
        await call.answer("Заявка уже обработана", show_alert=True)
        return

    db.set_promotion_order_status(order_id, "rejected")
    db.add_usdt_balance(order["user_id"], float(order["price_usdt"]))

    try:
        await call.bot.send_message(
            order["user_id"],
            "❌ <b>Ваше задание отклонено</b>\n\n"
            "Причина: проблема с продвижением.\n"
            "Сумма возвращена на ваш баланс.",
            parse_mode="HTML",
        )
    except Exception:
        pass

    await call.message.edit_reply_markup(reply_markup=None)
    await premium.answer_html(
        call.message,
        f"❌ Заявка <b>#{order_id}</b> отклонена. Деньги возвращены пользователю.",
    )
    await call.answer("Отклонено")