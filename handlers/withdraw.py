# handlers/withdraw.py
from __future__ import annotations

from services.premium_emoji import PremiumEmoji
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from config import Config
from database import Database
from keyboards.main_menu import main_menu_kb

router = Router()


class WithdrawStates(StatesGroup):
    waiting_amount = State()
    confirm = State()


WITHDRAW_MIN = 0.01  # минимальная сумма вывода (теперь одна для всех)

def _with_proof_video_kb(base_kb: InlineKeyboardMarkup) -> InlineKeyboardMarkup:
    # аккуратно добавим новую строку с кнопкой
    rows = []
    if base_kb and getattr(base_kb, "inline_keyboard", None):
        rows = [row[:] for row in base_kb.inline_keyboard]

    rows.append([
        InlineKeyboardButton(text="🎥 Пример получения чека", callback_data="withdraw_proof_video")
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _back_kb(cb: str = "withdraw_cancel"):
    kb = InlineKeyboardBuilder()
    kb.button(text="⬅️ Назад", callback_data=cb)
    kb.adjust(1)
    return kb.as_markup()


def _confirm_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Подтвердить", callback_data="withdraw_confirm")
    kb.button(text="❌ Отмена", callback_data="withdraw_cancel")
    kb.adjust(2)
    return kb.as_markup()


def _menu_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="🏠 В меню", callback_data="go_menu")
    kb.adjust(1)
    return kb.as_markup()


def _ensure_withdraw_tables(db: Database):
    conn = db._connect()
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS withdraw_requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        source TEXT NOT NULL DEFAULT 'usdt',
        amount_usdt REAL NOT NULL,
        address TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'pending', -- pending/processed/denied
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        processed_at TEXT,
        processed_by INTEGER,
        comment TEXT
    )
    """)
    conn.commit()
    conn.close()


def _parse_amount(txt: str):
    try:
        s = (txt or "").strip().replace(",", ".")
        return float(s)
    except Exception:
        return None


def _is_active(db: Database, tg_id: int) -> bool:
    """Активный доступ: active И leader."""
    try:
        return db.get_status(tg_id) in ("active", "leader")
    except Exception:
        return False

async def _withdraw_entry(message_or_call, state: FSMContext, db: Database, cfg: Config, premium: PremiumEmoji):
    await state.clear()
    tg_id = message_or_call.from_user.id

    # ---- НЕ АКТИВНЫЙ: показываем инфо + кнопку видео ----
    if not _is_active(db, tg_id):
        text = (
            "⛔️ <b>Вывод недоступен</b>\n\n"
            "✅ <b>Чтобы открыть вывод, получите статус «Активный»</b>\n\n"
            "<b>• Пополнить 10 USDT</b>\n"
            "<b>• Выполнить 7 заданий</b>\n"
            "<b>• Создать 7 заданий</b>\n\n"
            "👛 <b>Вывод средств происходит автоматически. После создания заявки вы получите чек в</b> @CryptoBot."
        )

        base_kb = main_menu_kb(
            is_admin=(message_or_call.from_user.id == cfg.ADMIN_ID),
            miniapp_url=cfg.WEBAPP_URL
        )
        kb = _with_proof_video_kb(base_kb)

        if isinstance(message_or_call, CallbackQuery):
            await premium.answer_html(message_or_call.message, text, reply_markup=kb)
            await message_or_call.answer()
        else:
            await premium.answer_html(message_or_call, text, reply_markup=kb)
        return

    # ---- АКТИВНЫЙ: обычный вывод ----
    try:
        usdt_bal = float(db.get_usdt_balance(tg_id) or 0.0)
    except Exception:
        usdt_bal = 0.0

    await state.set_state(WithdrawStates.waiting_amount)

    text = (
        "💸 <b>Вывод USDT</b>\n\n"
        f"💵 <b>Ваш баланс:</b> <b>{usdt_bal:.2f} USDT</b>\n\n"
        "✍️ Введите сумму вывода в <b>USDT</b>:"
    )

    if isinstance(message_or_call, CallbackQuery):
        await premium.answer_html(message_or_call.message, text, reply_markup=_back_kb("withdraw_cancel"))
        await message_or_call.answer()
    else:
        await premium.answer_html(message_or_call, text, reply_markup=_back_kb("withdraw_cancel"))

@router.callback_query(F.data == "withdraw_proof_video")
async def withdraw_proof_video(call: CallbackQuery):
    video = FSInputFile("assets/withdraw_proof.mp4")
    await call.message.answer_document(
        document=video,
        caption="✅ Пример: так приходит чек от @CryptoBot после автоматической выплаты."
    )
    await call.answer()


@router.message(F.text == "💸 Вывод")
async def withdraw_start(message: Message, state: FSMContext, db: Database, cfg: Config, premium: PremiumEmoji):
    await _withdraw_entry(message, state, db, cfg, premium)


@router.callback_query(F.data == "withdraw_menu")
async def withdraw_menu(call: CallbackQuery, state: FSMContext, db: Database, cfg: Config, premium: PremiumEmoji):
    await _withdraw_entry(call, state, db, cfg, premium)


@router.callback_query(F.data == "withdraw_cancel")
async def withdraw_cancel(call: CallbackQuery, state: FSMContext, cfg: Config):
    await state.clear()
    await call.message.answer(
        "❌ Отменено.",
        reply_markup=main_menu_kb(
            is_admin=(call.from_user.id == cfg.ADMIN_ID),
            miniapp_url=cfg.WEBAPP_URL
        )
    )
    await call.answer()


@router.message(WithdrawStates.waiting_amount)
async def withdraw_amount(message: Message, state: FSMContext, db: Database, cfg: Config, premium: PremiumEmoji):
    tg_id = message.from_user.id

    if not _is_active(db, tg_id):
        await state.clear()
        await premium.answer_html(
            message,
            "⛔ Вывод доступен только со статусом <b>Активный</b>.",
            reply_markup=main_menu_kb(
                is_admin=(message.from_user.id == cfg.ADMIN_ID),
                miniapp_url=cfg.WEBAPP_URL
            )
        )
        return

    amount = _parse_amount(message.text)
    if amount is None or amount <= 0:
        await premium.answer_html(message, "❌ Введите корректную сумму. Пример: <b>2</b> или <b>5.5</b>")
        return

    if amount + 1e-9 < WITHDRAW_MIN:
        await premium.answer_html(message, f"❌ Минимальная сумма вывода: <b>{WITHDRAW_MIN:.2f} USDT</b>")
        return

    # ✅ проверяем только основной usdt_balance
    try:
        bal = float(db.get_usdt_balance(tg_id) or 0.0)
    except Exception:
        bal = 0.0

    if bal + 1e-9 < float(amount):
        await premium.answer_html(
            message,
            "⛔ Недостаточно средств на балансе.\n\n"
            f"Ваш баланс: <b>{bal:.2f} USDT</b>"
        )
        return

    await state.update_data(amount=float(amount))
    await state.set_state(WithdrawStates.confirm)

    await premium.answer_html(
        message,
        "✅ <b>Подтвердите заявку</b>\n\n"
        f"💵 Сумма: <b>{amount:.2f} USDT</b>\n\n"
        "После подтверждения сумма будет списана с основного баланса и отправлена на обработку.",
        reply_markup=_confirm_kb()
    )

@router.callback_query(F.data == "withdraw_confirm")
async def withdraw_confirm(call: CallbackQuery, state: FSMContext, db: Database, cfg: Config, premium: PremiumEmoji):
    tg_id = call.from_user.id

    if not _is_active(db, tg_id):
        await state.clear()
        await premium.answer_html(
            call.message,
            "⛔ Вывод доступен только со статусом <b>Активный</b>.",
            reply_markup=main_menu_kb(
                is_admin=(call.from_user.id == cfg.ADMIN_ID),
                miniapp_url=cfg.WEBAPP_URL
            )
        )
        await call.answer()
        return

    data = await state.get_data()
    amount = float(data.get("amount", 0.0))

    if amount <= 0:
        await call.answer("Ошибка данных заявки", show_alert=True)
        return

    if amount + 1e-9 < WITHDRAW_MIN:
        await call.answer(f"Минимум: {WITHDRAW_MIN:.2f} USDT", show_alert=True)
        return

    _ensure_withdraw_tables(db)

    conn = db._connect()
    cur = conn.cursor()
    try:
        cur.execute("BEGIN IMMEDIATE")

        # ✅ баланс только usdt_balance
        cur.execute("SELECT usdt_balance FROM users WHERE tg_id=?", (int(tg_id),))
        row = cur.fetchone()
        bal = float(row["usdt_balance"] or 0.0) if row else 0.0
        if bal + 1e-9 < float(amount):
            conn.rollback()
            await call.answer("Недостаточно USDT баланса", show_alert=True)
            return

        cur.execute("""
            UPDATE users
            SET usdt_balance = usdt_balance - ?
            WHERE tg_id=?
        """, (float(amount), int(tg_id)))

        cur.execute("""
            INSERT INTO withdraw_requests (user_id, source, amount_usdt, address, status, created_at)
            VALUES (?, 'usdt', ?, '', 'pending', datetime('now'))
        """, (int(tg_id), float(amount)))

        req_id = int(cur.lastrowid)
        conn.commit()

    except Exception:
        conn.rollback()
        await call.answer("Ошибка создания заявки", show_alert=True)
        return
    finally:
        conn.close()

    await state.clear()

    await premium.answer_html(
        call.message,
        "✅ <b>Заявка на вывод создана</b>\n\n"
        f"🆔 ID: <b>{req_id}</b>\n"
        f"💵 Сумма: <b>{amount:.2f} USDT</b>\n\n"
        "👛 <b>После проверки вы получите чек</b> @CryptoBot\n"
        "⏳ <b>Заявка обрабатывается автоматически.</b>",
        reply_markup=_menu_kb()
    )
    await call.answer("✅ Создано", show_alert=True)
