# handlers/topup.py
import math
from typing import Optional

from aiogram import Router, F
from aiogram.types import (
    Message,
    CallbackQuery,
    LabeledPrice,
    PreCheckoutQuery,
)
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder

from services.premium_emoji import PremiumEmoji
from keyboards.main_menu import main_menu_kb
from config import Config
from database import Database
from services.cryptobot import CryptoBotAPI

router = Router()


# =========================
# FSM (CryptoBot USDT)
# =========================
class TopUpStates(StatesGroup):
    waiting_amount = State()
    confirm = State()


# =========================
# Keyboards
# =========================
def _topup_choose_kb() -> InlineKeyboardBuilder:
    kb = InlineKeyboardBuilder()
    kb.button(text="💳 Пополнить USDT CryptoBot", callback_data="topup_usdt_start")
    kb.button(text="🪙 Пополнить DIGI Stars ⭐", callback_data="topup_stars_menu")
    kb.button(text="🏠 В меню", callback_data="go_menu")
    kb.adjust(1)
    return kb


def _topup_confirm_kb() -> InlineKeyboardBuilder:
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Подтвердить", callback_data="topup_confirm")
    kb.button(text="❌ Отмена", callback_data="topup_cancel")
    kb.adjust(2)
    return kb


def _topup_back_kb() -> InlineKeyboardBuilder:
    kb = InlineKeyboardBuilder()
    kb.button(text="⬅️ Назад", callback_data="topup_back")
    kb.adjust(1)
    return kb


def _invoice_kb(pay_url: str, invoice_id: str) -> InlineKeyboardBuilder:
    kb = InlineKeyboardBuilder()
    kb.button(text="💳 Оплатить", url=pay_url)
    kb.button(text="🔄 Проверить оплату", callback_data=f"topup_check:{invoice_id}")
    kb.button(text="🏠 В меню", callback_data="go_menu")
    kb.adjust(1)
    return kb


def _stars_kb(cfg: Config) -> InlineKeyboardBuilder:
    """
    Пакеты Stars -> DIGI
    Мин: 20⭐ = 1000 DIGI (1⭐ = 50 DIGI)
    """
    digi_per_star = int(getattr(cfg, "DIGI_PER_STAR", 50))
    stars_min = int(getattr(cfg, "STARS_MIN", 20))

    kb = InlineKeyboardBuilder()

    # пакеты можно менять как хочешь
    for stars in [20, 50, 100, 200]:
        if stars < stars_min:
            continue
        digi = stars * digi_per_star
        kb.button(text=f"{stars}⭐ = {digi:,} DIGI", callback_data=f"stars_buy:{stars}")

    kb.button(text="⬅️ Назад", callback_data="topup_back_to_choose")
    kb.adjust(1)
    return kb


def _parse_amount(text: str) -> Optional[float]:
    try:
        t = (text or "").strip().replace(",", ".")
        val = float(t)
        if math.isnan(val) or math.isinf(val):
            return None
        return val
    except Exception:
        return None


# =========================
# DB helpers (CryptoBot)
# =========================
def _db_create_topup(db: Database, user_id: int, amount_usdt: float, invoice_id: str, amount_digi: int = 0):
    """
    Сохраняем topup как USDT-пополнение.
    amount_digi оставляем в таблице для совместимости, но всегда 0 (DIGI НЕ покупается).
    """
    conn = db._connect()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO topups (user_id, amount_usdt, amount_digi, status, invoice_id, created_at)
        VALUES (?, ?, ?, 'pending', ?, datetime('now'))
        """,
        (int(user_id), float(amount_usdt), int(amount_digi), str(invoice_id)),
    )
    conn.commit()
    conn.close()


def _db_get_topup_by_invoice(db: Database, invoice_id: str):
    conn = db._connect()
    cur = conn.cursor()
    cur.execute("SELECT * FROM topups WHERE invoice_id = ?", (invoice_id,))
    row = cur.fetchone()
    conn.close()
    return row


def _db_mark_topup_paid(db: Database, invoice_id: str):
    conn = db._connect()
    cur = conn.cursor()
    cur.execute("UPDATE topups SET status='paid' WHERE invoice_id = ?", (invoice_id,))
    conn.commit()
    conn.close()


# =========================
# ENTRY: "💰 Пополнить" -> choose method
# =========================
@router.message(F.text == "💰 Пополнить")
async def topup_entry(message: Message, state: FSMContext, cfg: Config, premium: PremiumEmoji):
    await state.clear()

    digi_per_star = int(getattr(cfg, "DIGI_PER_STAR", 50))
    stars_min = int(getattr(cfg, "STARS_MIN", 20))
    min_digi = stars_min * digi_per_star

    text = (
        "💵 <b>Пополнение</b>\n\n"
        "Выберите способ 👇\n\n"
        f"💳 <b>USDT</b> через CryptoBot\n\n"
        f"🪙 <b>DIGI</b> за Stars <b>{stars_min}⭐ = {min_digi:,} DIGI</b>"
    )
    await premium.answer_html(message, text, reply_markup=_topup_choose_kb().as_markup())


# =========================
# USDT (CryptoBot) flow
# =========================
@router.callback_query(F.data == "topup_usdt_start")
async def topup_usdt_start(call: CallbackQuery, state: FSMContext, cfg: Config, premium: PremiumEmoji):
    await state.clear()
    await state.set_state(TopUpStates.waiting_amount)

    text = (
        "💳 <b>Пополнение баланса USDT</b>\n\n"
        f"✅ Минимум: <b>{cfg.TOPUP_MIN_USDT:.2f} USDT</b>\n\n"
        "✍️ Введите сумму в <b>USDT</b>:"
    )
    await premium.answer_html(call.message, text, reply_markup=_topup_back_kb().as_markup())
    await call.answer()


@router.message(TopUpStates.waiting_amount)
async def topup_amount_entered(message: Message, state: FSMContext, cfg: Config, premium: PremiumEmoji):
    amount_usdt = _parse_amount(message.text)
    if amount_usdt is None:
        await premium.answer_html(message, "❌ Введите число. Пример: <b>5</b> или <b>12.5</b>")
        return

    if amount_usdt < cfg.TOPUP_MIN_USDT:
        await premium.answer_html(message, f"❌ Минимальная сумма: <b>{cfg.TOPUP_MIN_USDT:.2f} USDT</b>")
        return

    await state.update_data(amount_usdt=float(amount_usdt))
    await state.set_state(TopUpStates.confirm)

    text = (
        "✅ <b>Подтверждение</b>\n\n"
        f"💵 Сумма: <b>{amount_usdt:.2f} USDT</b>\n\n"
        "💳 После оплаты зачислим на ваш <b>USDT-баланс</b> в DigiBot.\n\n"
        "Продолжить?"
    )
    await premium.answer_html(message, text, reply_markup=_topup_confirm_kb().as_markup())


@router.callback_query(F.data == "topup_cancel")
async def topup_cancel(call: CallbackQuery, state: FSMContext, premium: PremiumEmoji):
    await state.clear()
    await premium.answer_html(call.message, "❌ Пополнение отменено.")
    await call.answer()


@router.callback_query(F.data == "topup_back")
async def topup_back(call: CallbackQuery, cfg, state: FSMContext, premium: PremiumEmoji):
    await state.clear()
    await premium.answer_html(
        call.message,
        "🏠 Головне меню 👇",
        reply_markup=main_menu_kb(
            is_admin=(call.from_user.id == cfg.ADMIN_ID),
            miniapp_url=cfg.WEBAPP_URL
        )
    )
    await call.answer()


@router.callback_query(F.data == "topup_confirm")
async def topup_confirm(call: CallbackQuery, state: FSMContext, db: Database, cfg: Config, premium: PremiumEmoji):
    data = await state.get_data()
    amount_usdt = float(data["amount_usdt"])

    tg_id = call.from_user.id
    user = db.get_user(tg_id)
    if not user:
        db.create_user(tg_id=tg_id, username=call.from_user.username or "NoUsername", referrer_id=None)
        user = db.get_user(tg_id)

    api = CryptoBotAPI(token=cfg.CRYPTOBOT_TOKEN, base_url=cfg.CRYPTOBOT_API_BASE)

    inv = await api.create_invoice(
        amount=round(amount_usdt, 2),
        asset="USDT",
        description="DigiBot • Пополнение баланса USDT",
    )
    invoice_id = str(inv["invoice_id"])
    pay_url = inv["pay_url"]

    _db_create_topup(db, user_id=int(user["tg_id"]), amount_usdt=amount_usdt, invoice_id=invoice_id, amount_digi=0)

    await state.clear()

    text = (
        "🧾 <b>Счёт создан</b>\n\n"
        f"💵 Сумма: <b>{amount_usdt:.2f} USDT</b>\n\n"
        "💳 После оплаты зачислим на ваш <b>USDT-баланс</b>.\n\n"
        "Нажмите <b>Оплатить</b>, затем <b>Проверить оплату</b>."
    )
    await premium.answer_html(call.message, text, reply_markup=_invoice_kb(pay_url, invoice_id).as_markup())
    await call.answer()


@router.callback_query(F.data.startswith("topup_check:"))
async def topup_check(call: CallbackQuery, db: Database, cfg: Config, premium: PremiumEmoji):
    invoice_id = call.data.split(":", 1)[1].strip()

    topup = _db_get_topup_by_invoice(db, invoice_id)
    if not topup:
        await call.answer("❌ Счёт не найден", show_alert=True)
        return

    if topup["status"] == "paid":
        await call.answer("✅ Уже оплачено", show_alert=True)
        return

    api = CryptoBotAPI(token=cfg.CRYPTOBOT_TOKEN, base_url=cfg.CRYPTOBOT_API_BASE)
    info = await api.get_invoice(invoice_id=invoice_id)

    status = (info.get("status") or "").lower()
    if status == "paid":
        user_id = int(topup["user_id"])
        amount_usdt = float(topup["amount_usdt"] or 0.0)

        # ✅ начисляем USDT + запускаем новую 2-уровневую рефералку:
        # - реферал считается, если total_topup_usdt >= 10
        # - 1 уровень: +4 USDT
        # - 2 уровень: +2 USDT
        db.add_usdt(
            user_id,
            amount_usdt,
            referral_min_topup_usdt=float(getattr(cfg, "REF_MIN_TOPUP_USDT", 10.0)),
            ref_l1_reward_usdt=float(getattr(cfg, "REF_L1_REWARD_USDT", 4.0)),
            ref_l2_reward_usdt=float(getattr(cfg, "REF_L2_REWARD_USDT", 2.0)),
        )

        # ✅ твоя логика статусов (оставляем)
        db.try_activate_user(user_id)

        _db_mark_topup_paid(db, invoice_id)

        text = (
            "✅ <b>Оплата подтверждена!</b>\n\n"
            f"💵 Пополнено: <b>{amount_usdt:.2f} USDT</b>\n"
            "💼 USDT-баланс обновлён.\n\n"
            "Спасибо! 🚀"
        )
        await premium.answer_html(call.message, text)
        await call.answer("✅ Оплачено!", show_alert=True)
    else:
        await call.answer("⏳ Пока не оплачено. Попробуйте позже.", show_alert=True)


# =========================
# STARS -> DIGI
# =========================
@router.callback_query(F.data == "topup_stars_menu")
async def topup_stars_menu(call: CallbackQuery, state: FSMContext, cfg: Config, premium: PremiumEmoji):
    await state.clear()

    digi_per_star = int(getattr(cfg, "DIGI_PER_STAR", 50))
    stars_min = int(getattr(cfg, "STARS_MIN", 20))
    min_digi = stars_min * digi_per_star

    text = (
        "🪙 <b>Пополнение DIGI за Stars ⭐️</b>\n\n"
        f"<b>Минимум: {stars_min}⭐️ = {min_digi:,} DIGI</b>\n"
        f"<b>Курс: 1⭐️ = {digi_per_star} DIGI</b>\n\n"
        '<b>В</b> <a href="https://t.me/Stars_buddy_bot?start=8112868218">'
        'Stars_buddy_bot</a> <b>вы сможете купить звёзды намного дешевле</b> ⭐️\n\n'
        "Выберите пакет 👇"
    )
    await premium.answer_html(
        call.message,
        text,
        reply_markup=_stars_kb(cfg).as_markup(),
        disable_web_page_preview=True
    )
    await call.answer()


@router.callback_query(F.data == "topup_back_to_choose")
async def topup_back_to_choose(call: CallbackQuery, state: FSMContext, cfg: Config, premium: PremiumEmoji):
    await state.clear()
    digi_per_star = int(getattr(cfg, "DIGI_PER_STAR", 50))
    stars_min = int(getattr(cfg, "STARS_MIN", 20))
    min_digi = stars_min * digi_per_star

    text = (
        "💵 <b>Пополнение</b>\n\n"
        "Выберите способ 👇\n\n"
        f"💳 <b>USDT</b> через CryptoBot\n\n"
        f"🪙 <b>DIGI</b> за Stars <b>{stars_min}⭐ = {min_digi:,} DIGI</b>"
    )
    await premium.answer_html(call.message, text, reply_markup=_topup_choose_kb().as_markup())
    await call.answer()


@router.callback_query(F.data.startswith("stars_buy:"))
async def stars_buy(call: CallbackQuery, cfg: Config):
    stars = int(call.data.split(":", 1)[1])

    stars_min = int(getattr(cfg, "STARS_MIN", 20))
    digi_per_star = int(getattr(cfg, "DIGI_PER_STAR", 50))

    if stars < stars_min:
        await call.answer(f"Минимум {stars_min}⭐", show_alert=True)
        return

    digi = stars * digi_per_star

    payload = f"stars_digi:{call.from_user.id}:{stars}:{digi}"

    await call.bot.send_invoice(
        chat_id=call.from_user.id,
        title="Пополнение DIGI за Stars",
        description=f"{stars}⭐ → {digi:,} DIGI",
        payload=payload,
        provider_token="",
        currency="XTR",
        prices=[LabeledPrice(label=f"{digi:,} DIGI", amount=int(stars))],
    )

    await call.answer()


@router.pre_checkout_query()
async def pre_checkout(pre: PreCheckoutQuery):
    await pre.answer(ok=True)


@router.message(F.successful_payment)
async def stars_success(message: Message, db: Database, cfg: Config, premium: PremiumEmoji):
    sp = message.successful_payment
    payload = sp.invoice_payload or ""

    if not payload.startswith("stars_digi:"):
        return

    try:
        _, uid, stars, digi = payload.split(":")
        uid = int(uid)
        stars = int(stars)
        digi = int(digi)
    except Exception:
        return

    if uid != message.from_user.id:
        return

    stars_min = int(getattr(cfg, "STARS_MIN", 20))
    digi_per_star = int(getattr(cfg, "DIGI_PER_STAR", 50))
    if stars < stars_min:
        return

    expected_digi = stars * digi_per_star
    if digi != expected_digi:
        digi = expected_digi

    u = db.get_user(uid)
    if not u:
        db.create_user(tg_id=uid, username=message.from_user.username or "NoUsername", referrer_id=None)

    db.add_balance(uid, int(digi))

    await premium.answer_html(
        message,
        "✅ <b>Оплата успешна!</b>\n\n"
        f"⭐ Stars: <b>{stars}</b>\n"
        f"🪙 Начислено: <b>{digi:,} DIGI</b>"
    )