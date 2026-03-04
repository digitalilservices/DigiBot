# handlers/purchase.py
from __future__ import annotations

from pathlib import Path
from typing import Optional

from services.premium_emoji import PremiumEmoji
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

from config import Config
from database import Database
from keyboards.purchase_menu import (
    purchase_root_inline,
    service_actions_inline,
    ads_actions_inline,
    service_pay_back_inline,
    convert_menu_inline,
)

router = Router()


class ServicePayStates(StatesGroup):
    waiting_amount = State()


class ConvertStates(StatesGroup):
    waiting_digi = State()
    waiting_usdt = State()
    confirm = State()


SERVICE_META = {
    "tgbot": {"title": "🤖 Telegram-Bot", "desc": "", "image": "tgbot.jpg"},
    "website": {"title": "🌐 Web-Site", "desc": "", "image": "website.jpg"},
    "smm": {"title": "📣 SMM-Promotion", "desc": "", "image": "smm.jpg"},
}

def _is_active(db: Database, tg_id: int) -> bool:
    try:
        return db.get_status(tg_id) in ("active", "leader")
    except Exception:
        return False

def _is_leader(db: Database, tg_id: int) -> bool:
    try:
        return db.get_status(tg_id) == "leader"
    except Exception:
        return False

def rget(row, key: str, default=None):
    if row is None:
        return default
    try:
        if isinstance(row, dict):
            return row.get(key, default)
        if key in row.keys():
            v = row[key]
            return default if v is None else v
    except Exception:
        pass
    return default


def _service_image_path(cfg: Config, filename: str) -> Optional[Path]:
    p = cfg.MEDIA_DIR / filename
    return p if p.exists() and p.is_file() else None


def _parse_int(text: str) -> Optional[int]:
    raw = (text or "").strip().replace(" ", "")
    if not raw.isdigit():
        return None
    try:
        return int(raw)
    except Exception:
        return None


def _parse_float(text: str) -> Optional[float]:
    try:
        t = (text or "").strip().replace(",", ".").replace(" ", "")
        val = float(t)
        if val <= 0:
            return None
        return val
    except Exception:
        return None


def _convert_confirm_kb():
    from aiogram.utils.keyboard import InlineKeyboardBuilder

    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Конвертировать", callback_data="convert_confirm")
    kb.button(text="❌ Отмена", callback_data="convert_cancel")
    kb.adjust(2)
    return kb.as_markup()


def _convert_cancel_kb():
    from aiogram.utils.keyboard import InlineKeyboardBuilder

    kb = InlineKeyboardBuilder()
    kb.button(text="❌ Отмена", callback_data="convert_cancel")
    kb.adjust(1)
    return kb.as_markup()


# ---------------- routes ----------------
@router.message(F.text == "🛍 Покупка")
async def purchase_open(message: Message, premium: PremiumEmoji):
    text = (
        "🛍 <b>Покупка</b>\n\n"
        "✨ <b>Здесь вы сможете:</b>\n"
        "♻️ Конвертировать <b>DIGI</b>\n"
        "📢 Разместить рекламу прямо в <b>DigiBot</b>"
    )
    await premium.answer_html(message, text, reply_markup=purchase_root_inline())


@router.callback_query(F.data == "buy_root")
async def buy_root(call: CallbackQuery, premium: PremiumEmoji):
    await premium.answer_html(
        call.message,
        "🛍 <b>Покупка</b>\n\n"
        "✨ <b>Здесь вы сможете:</b>\n"
        "♻️ Конвертировать <b>DIGI</b>\n"
        "📢 Разместить рекламу прямо в <b>DigiBot</b>",
        reply_markup=purchase_root_inline(),
    )
    await call.answer()


# =========================
# DIGI <-> USDT CONVERT
# =========================
@router.callback_query(F.data == "convert_digi_to_usdt")
async def buy_convert(call: CallbackQuery, state: FSMContext, db: Database, cfg: Config, premium: PremiumEmoji):
    await state.clear()

    tg_id = call.from_user.id
    if not _is_leader(db, tg_id):
        await call.answer("⛔ DGR → USDT доступно только со статусом Лидер", show_alert=True)
        return
    user = db.get_user(tg_id)
    if not user:
        db.create_user(tg_id=tg_id, username=call.from_user.username or "NoUsername", referrer_id=None)
        user = db.get_user(tg_id)

    digi_balance = int(rget(user, "balance_digi", 0) or 0)
    usdt_balance = float(rget(user, "usdt_balance", 0.0) or 0.0)

    rate = int(getattr(cfg, "DIGI_PER_1_USDT", 5000))

    await state.update_data(mode="d2u")
    await state.set_state(ConvertStates.waiting_digi)

    text = (
        "🔄 <b>Конвертация DGR → USDT</b>\n\n"
        f"📌 Курс: <b>{rate:,} DIGI = 1 USDT</b>\n\n"
        f"🪙 Ваш DGR: <b>{digi_balance:,}</b>\n"
        f"💵 Ваш USDT: <b>{usdt_balance:.2f}</b>\n\n"
        f"✍️ Введите сумму в <b>DGR</b> (минимум {rate:,}):"
    )
    await premium.answer_html(call.message, text, reply_markup=_convert_cancel_kb())
    await call.answer()


@router.callback_query(F.data == "convert_usdt_to_digi")
async def convert_usdt_to_digi_start(call: CallbackQuery, state: FSMContext, db: Database, cfg: Config, premium: PremiumEmoji):
    await state.clear()

    tg_id = call.from_user.id
    if not _is_active(db, tg_id):
        await call.answer("⛔ Конвертация доступна только со статусом Активный", show_alert=True)
        return
    user = db.get_user(tg_id)
    if not user:
        db.create_user(tg_id=tg_id, username=call.from_user.username or "NoUsername", referrer_id=None)
        user = db.get_user(tg_id)

    digi_balance = int(rget(user, "balance_digi", 0) or 0)
    usdt_balance = float(rget(user, "usdt_balance", 0.0) or 0.0)

    rate = int(getattr(cfg, "DIGI_PER_1_USDT", 5000))

    await state.update_data(mode="u2d")
    await state.set_state(ConvertStates.waiting_usdt)

    text = (
        "🔄 <b>Конвертация USDT → DGR</b>\n\n"
        f"📌 Курс: <b>1 USDT = {rate:,} DGR</b>\n\n"
        f"🪙 Ваш DGR: <b>{digi_balance:,}</b>\n"
        f"💵 Ваш USDT: <b>{usdt_balance:.2f}</b>\n\n"
        "✍️ Введите сумму в <b>USDT</b> (пример: <b>1</b> или <b>2.5</b>):"
    )
    await premium.answer_html(call.message, text, reply_markup=_convert_cancel_kb())
    await call.answer()


@router.callback_query(F.data == "convert_menu")
async def convert_menu(call: CallbackQuery, db: Database, cfg: Config, premium: PremiumEmoji):
    tg_id = call.from_user.id
    if not _is_active(db, tg_id):
        await premium.answer_html(
            call.message,
            "⛔️ <b>Конвертация недоступна</b>\n\n"
            "🏷 Ваш статус: <b>Новичок</b>\n\n"
            "✅ Чтобы открыть конвертацию, получите статус <b>Активный</b>:\n\n"
            "• Пополнить <b>10 USDT</b>\n"
            "• Выполнить <b>7 заданий</b>\n"
            "• Создать <b>7 заданий</b>",
        )
        await call.answer()
        return
    user = db.get_user(tg_id)
    if not user:
        db.create_user(tg_id=tg_id, username=call.from_user.username or "NoUsername", referrer_id=None)
        user = db.get_user(tg_id)

    digi_balance = int(rget(user, "balance_digi", 0) or 0)
    usdt_balance = float(rget(user, "usdt_balance", 0.0) or 0.0)

    rate = int(getattr(cfg, "DIGI_PER_1_USDT", 5000))

    text = (
        "🔄 <b>Конвертация</b>\n\n"
        f"📌 Курс: <b>{rate:,} DGR = 1 USDT</b>\n\n"
        f"🪙 Ваш DGR: <b>{digi_balance:,}</b>\n"
        f"💵 Ваш USDT: <b>{usdt_balance:.2f}</b>\n\n"
        "Выберите направление:"
    )
    await premium.answer_html(call.message, text, reply_markup=convert_menu_inline())

@router.message(ConvertStates.waiting_digi)
async def convert_amount(message: Message, state: FSMContext, db: Database, cfg: Config, premium: PremiumEmoji):
    amount_digi = _parse_int(message.text)
    if amount_digi is None or amount_digi <= 0:
        await premium.answer_html(message, "❌ Введите число DGR. Пример: <b>5000</b>")
        return

    rate = int(getattr(cfg, "DIGI_PER_1_USDT", 5000))
    if amount_digi < rate:
        await premium.answer_html(message, f"❌ Минимум для конвертации: <b>{rate:,} DGR</b>")
        return

    tg_id = message.from_user.id
    user = db.get_user(tg_id)
    if not user:
        db.create_user(tg_id=tg_id, username=message.from_user.username or "NoUsername", referrer_id=None)
        user = db.get_user(tg_id)

    digi_balance = int(rget(user, "balance_digi", 0) or 0)
    if digi_balance < amount_digi:
        await premium.answer_html(message, f"❌ Недостаточно DGR.\nВаш баланс: <b>{digi_balance:,}</b> DGR")
        return

    usdt_add = amount_digi / float(rate)
    await state.update_data(amount_digi=int(amount_digi), usdt_add=float(usdt_add))
    await state.set_state(ConvertStates.confirm)

    await premium.answer_html(message,
        "✅ <b>Подтверждение</b>\n\n"
        f"🪙 Списать: <b>{amount_digi:,} DGR</b>\n"
        f"💵 Зачислить: <b>{usdt_add:.6f} USDT</b>\n\n"
        "Подтвердить конвертацию?",
        reply_markup=_convert_confirm_kb(),
    )


@router.message(ConvertStates.waiting_usdt)
async def convert_amount_usdt(message: Message, state: FSMContext, db: Database, cfg: Config, premium: PremiumEmoji):
    amount_usdt = _parse_float(message.text)
    if amount_usdt is None:
        await premium.answer_html(message,"❌ Введите сумму USDT числом. Пример: <b>1</b> или <b>2.5</b>")
        return

    rate = int(getattr(cfg, "DIGI_PER_1_USDT", 5000))

    tg_id = message.from_user.id
    user = db.get_user(tg_id)
    if not user:
        db.create_user(tg_id=tg_id, username=message.from_user.username or "NoUsername", referrer_id=None)
        user = db.get_user(tg_id)

    usdt_balance = float(rget(user, "usdt_balance", 0.0) or 0.0)
    if usdt_balance + 1e-9 < float(amount_usdt):
        await premium.answer_html(message,f"❌ Недостаточно USDT.\nВаш баланс: <b>{usdt_balance:.2f}</b> USDT")
        return

    digi_add = int(round(float(amount_usdt) * float(rate)))

    await state.update_data(amount_usdt=float(amount_usdt), digi_add=int(digi_add))
    await state.set_state(ConvertStates.confirm)

    await premium.answer_html(message,
        "✅ <b>Подтверждение</b>\n\n"
        f"💵 Списать: <b>{amount_usdt:.2f} USDT</b>\n"
        f"🪙 Зачислить: <b>{digi_add:,} DGR</b>\n\n"
        "Подтвердить конвертацию?",
        reply_markup=_convert_confirm_kb(),
    )


@router.callback_query(F.data == "convert_cancel")
async def convert_cancel(call: CallbackQuery, state: FSMContext, premium: PremiumEmoji):
    await state.clear()
    await premium.answer_html(call.message, "❌ Отменено.")
    await call.answer()


@router.callback_query(F.data == "convert_confirm")
async def convert_confirm(call: CallbackQuery, state: FSMContext, db: Database, cfg: Config, premium: PremiumEmoji):
    tg_id = call.from_user.id
    data = await state.get_data()

    mode = str(data.get("mode") or "d2u")
    rate = int(getattr(cfg, "DIGI_PER_1_USDT", 5000))

    conn = db._connect()
    cur = conn.cursor()
    try:
        cur.execute("BEGIN IMMEDIATE")
        cur.execute("SELECT * FROM users WHERE tg_id=?", (int(tg_id),))
        u = cur.fetchone()
        if not u:
            conn.rollback()
            await call.answer("Пользователь не найден", show_alert=True)
            return

        if mode == "d2u":
            amount_digi = int(data["amount_digi"])
            usdt_add = float(data["usdt_add"])

            digi_balance = int((u["balance_digi"] if "balance_digi" in u.keys() else 0) or 0)
            if digi_balance < amount_digi:
                conn.rollback()
                await call.answer("⛔ Недостаточно DGR", show_alert=True)
                return

            cur.execute(
                "UPDATE users SET balance_digi = balance_digi - ?, usdt_balance = usdt_balance + ? WHERE tg_id=?",
                (int(amount_digi), float(usdt_add), int(tg_id)),
            )

            try:
                cur.execute(
                    "INSERT INTO purchases (user_id, service, amount_digi, created_at) VALUES (?, ?, ?, datetime('now'))",
                    (int(tg_id), f"CONVERT {amount_digi} DIGI -> {usdt_add:.6f} USDT",0),
                )
            except Exception:
                pass

            conn.commit()
            await state.clear()
            await premium.answer_html(call.message,
                "✅ <b>Конвертация выполнена!</b>\n\n"
                f"🪙 -<b>{amount_digi:,}</b> DGR\n"
                f"💵 +<b>{usdt_add:.6f}</b> USDT\n\n"
                f"📌 Курс: {rate:,} DGR = 1 USDT"
            )
            await call.answer()
            return

        # mode == "u2d"
        amount_usdt = float(data["amount_usdt"])
        digi_add = int(data["digi_add"])

        usdt_balance = float((u["usdt_balance"] if "usdt_balance" in u.keys() else 0.0) or 0.0)
        if usdt_balance + 1e-9 < float(amount_usdt):
            conn.rollback()
            await call.answer("⛔ Недостаточно USDT", show_alert=True)
            return

        cur.execute(
            "UPDATE users SET usdt_balance = usdt_balance - ?, balance_digi = balance_digi + ? WHERE tg_id=?",
            (float(amount_usdt), int(digi_add), int(tg_id)),
        )

        try:
            cur.execute(
                "INSERT INTO purchases (user_id, service, amount_digi, created_at) VALUES (?, ?, ?, datetime('now'))",
                (int(tg_id), f"CONVERT {amount_usdt:.2f} USDT -> {digi_add} DIGI", 0),
            )
        except Exception:
            pass

        conn.commit()
        await state.clear()
        await premium.answer_html(call.message,
            "✅ <b>Конвертация выполнена!</b>\n\n"
            f"💵 -<b>{amount_usdt:.2f}</b> USDT\n"
            f"🪙 +<b>{digi_add:,}</b> DGR\n\n"
            f"📌 Курс: 1 USDT = {rate:,} DGR"
        )
        await call.answer()

    except Exception:
        conn.rollback()
        await call.answer("Ошибка конвертации", show_alert=True)
    finally:
        conn.close()


# =========================
# EXISTING: Services / Ads (НЕ ЛОМАЕМ)
# =========================
@router.callback_query(F.data.startswith("svc:"))
async def service_details(call: CallbackQuery, cfg: Config):
    code = call.data.split(":", 1)[1].strip()
    meta = SERVICE_META.get(code)
    if not meta:
        await call.answer("❌ Услуга не найдена", show_alert=True)
        return

    title = meta["title"]
    desc = meta["desc"]
    text = f"{title}\n {desc}\n\n"

    img_path = _service_image_path(cfg, meta["image"])
    if img_path:
        await call.message.answer_photo(
            photo=FSInputFile(str(img_path)),
            caption=text,
            reply_markup=service_actions_inline(cfg.SUPPORT_USERNAME, code),
        )
    else:
        await call.message.answer(
            text,
            reply_markup=service_actions_inline(cfg.SUPPORT_USERNAME, code),
        )

    await call.answer()


@router.callback_query(F.data.startswith("svc_pay:"))
async def service_pay_start(call: CallbackQuery, state: FSMContext):
    code = call.data.split(":", 1)[1].strip()
    if code not in SERVICE_META:
        await call.answer("❌ Услуга не найдена", show_alert=True)
        return

    await state.clear()
    await state.set_state(ServicePayStates.waiting_amount)
    await state.update_data(service_code=code)

    await call.message.answer(
        "💳 <b>Оплата услуги DIGI</b>\n\n"
        "✍️ Введите сумму в <b>DIGI</b>\n"
        "Например: <b>1500</b>",
        reply_markup=service_pay_back_inline(code),
    )
    await call.answer()


@router.message(ServicePayStates.waiting_amount)
async def service_pay_amount(message: Message, state: FSMContext, db: Database, cfg: Config):
    raw = (message.text or "").strip().replace(" ", "")
    if not raw.isdigit():
        await message.answer("❌ Введите сумму цифрами (целое число). Пример: <b>1500</b>")
        return

    amount = int(raw)
    if amount <= 0:
        await message.answer("❌ Сумма должна быть больше 0.")
        return

    tg_id = message.from_user.id
    user = db.get_user(tg_id)
    if not user:
        db.create_user(tg_id=tg_id, username=message.from_user.username or "NoUsername", referrer_id=None)
        user = db.get_user(tg_id)

    if int(user["balance_digi"] or 0) < amount:
        await message.answer(
            "❌ Недостаточно DIGI.\n"
            f"Ваш баланс: <b>{int(user['balance_digi'] or 0):,}</b> DIGI"
        )
        return

    data = await state.get_data()
    code = data.get("service_code")
    meta = SERVICE_META.get(code, {"title": "Услуга"})
    service_title = meta["title"]

    ok = db.spend_balance(tg_id, amount)
    if not ok:
        await message.answer("❌ Не удалось списать средства. Попробуйте ещё раз.")
        return

    db.add_purchase(user_id=tg_id, service=service_title, amount=amount)

    await state.clear()

    text = (
        "✅ <b>Оплата прошла успешно!</b>\n\n"
        f"🛍 Услуга: <b>{service_title}</b>\n"
        f"💎 Списано: <b>{amount:,}</b> DIGI\n\n"
        f"👨‍💻 Для дальнейших шагов напишите администратору: <b>{cfg.SUPPORT_USERNAME}</b>"
    )
    await message.answer(text)


@router.callback_query(F.data == "buy_ads")
async def buy_ads(call: CallbackQuery, cfg: Config):
    text = (
        "📢 <b>Реклама</b>\n\n"
        "Вы можете разместить рекламу в разделе <b>Объявления</b>.\n\n"
        f"💎 Цена: <b>{cfg.ADS_PRICE_PER_DAY_DIGI:,} DIGI</b> за 1 день\n\n"
        "Нажмите кнопку ниже, чтобы создать рекламу."
    )
    await call.message.answer(text, reply_markup=ads_actions_inline())
    await call.answer()


@router.callback_query(F.data.startswith("svc_back:"))
async def svc_back(call: CallbackQuery, cfg: Config, state: FSMContext):
    code = call.data.split(":", 1)[1].strip()
    await state.clear()

    meta = SERVICE_META.get(code)
    if not meta:
        await call.answer("❌ Услуга не найдена", show_alert=True)
        return

    title = meta["title"]
    desc = meta["desc"]
    text = f"{title}\n {desc}\n\n"

    img_path = _service_image_path(cfg, meta["image"])
    if img_path:
        await call.message.answer_photo(
            photo=FSInputFile(str(img_path)),
            caption=text,
            reply_markup=service_actions_inline(cfg.SUPPORT_USERNAME, code),
        )
    else:
        await call.message.answer(
            text,
            reply_markup=service_actions_inline(cfg.SUPPORT_USERNAME, code),
        )

    await call.answer()
