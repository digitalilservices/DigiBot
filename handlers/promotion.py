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
    tp_confirm_kb,
    promo_order_admin_kb,
)

router = Router()

TP_ONLINE_SUBS_PRICE_PER_1000 = 50.0
TP_ONLINE_SUBS_MIN = 10
TP_ONLINE_SUBS_MAX = 30000


class PromotionStates(StatesGroup):
    tp_online_subs_link = State()
    tp_online_subs_quantity = State()


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


def _calc_price(quantity: int) -> float:
    return round((quantity / 1000) * TP_ONLINE_SUBS_PRICE_PER_1000, 2)


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
            "✅ <b>Ваше задание успешно выполнено.</b>\n\nПроверяйте результат.",
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