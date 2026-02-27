# handlers/status.py
from __future__ import annotations

from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import Config
from database import Database
from services.premium_emoji import PremiumEmoji
from services.cryptobot import CryptoBotAPI

router = Router()

# =========================
# Constants (правь тут)
# =========================
ACTIVE_TOPUP_USDT = 10.0
ACTIVE_NEED_DONE = 7
ACTIVE_NEED_CREATED = 7

LEADER_NEED_REFS = 10
LEADER_REF_MIN_TOPUP_USDT = 10.0
LEADER_BONUS_USDT = 10.0


# =========================
# Keyboards
# =========================
def _activation_menu_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="🟢 Активный", callback_data="activation_active_info")
    kb.button(text="👑 Лидер", callback_data="activation_leader_info")
    kb.button(text="⬅️ Назад", callback_data="cabinet")
    kb.adjust(1)
    return kb.as_markup()


def _active_pay_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text=f"💳 Внести {ACTIVE_TOPUP_USDT:.0f} USDT", callback_data="activation_active_pay")
    kb.button(text="⬅️ Назад", callback_data="activation_menu")
    kb.adjust(1)
    return kb.as_markup()


def _invoice_kb(pay_url: str, invoice_id: str):
    kb = InlineKeyboardBuilder()
    kb.button(text="💳 Оплатить", url=pay_url)
    kb.button(text="🔄 Проверить оплату", callback_data=f"activation_check:{invoice_id}")
    kb.button(text="⬅️ Назад", callback_data="activation_active_info")
    kb.adjust(1)
    return kb.as_markup()


def _leader_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="🔄 Проверить прогресс", callback_data="activation_leader_check")
    kb.button(text="⬅️ Назад", callback_data="activation_menu")
    kb.adjust(1)
    return kb.as_markup()


# =========================
# DB helpers (локально, чтобы не зависеть от других файлов)
# =========================
def _db_create_topup(db: Database, user_id: int, amount_usdt: float, invoice_id: str):
    conn = db._connect()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO topups (user_id, amount_usdt, amount_digi, status, invoice_id, created_at)
        VALUES (?, ?, 0, 'pending', ?, datetime('now'))
        """,
        (int(user_id), float(amount_usdt), str(invoice_id)),
    )
    conn.commit()
    conn.close()


def _db_get_topup_by_invoice(db: Database, invoice_id: str):
    conn = db._connect()
    cur = conn.cursor()
    cur.execute("SELECT * FROM topups WHERE invoice_id=?", (str(invoice_id),))
    row = cur.fetchone()
    conn.close()
    return row


def _db_mark_topup_paid(db: Database, invoice_id: str):
    conn = db._connect()
    cur = conn.cursor()
    cur.execute("UPDATE topups SET status='paid' WHERE invoice_id=?", (str(invoice_id),))
    conn.commit()
    conn.close()


def _leader_progress_raw(db: Database, tg_id: int) -> int:
    """
    Считаем сколько приглашённых (invited_by) имеют total_topup_usdt >= 10.
    Работает даже если referrer_id потом обнуляется.
    """
    conn = db._connect()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT COUNT(*) AS cnt
        FROM users
        WHERE invited_by = ?
          AND COALESCE(total_topup_usdt, 0) >= ?
        """,
        (int(tg_id), float(LEADER_REF_MIN_TOPUP_USDT)),
    )
    row = cur.fetchone()
    conn.close()
    return int(row["cnt"] or 0) if row else 0


def _try_grant_leader_raw(db: Database, tg_id: int) -> bool:
    """
    Выдаёт статус leader если прогресс >= 10.
    Бонус +10 USDT выдаётся один раз (leader_bonus_given).
    """
    conn = db._connect()
    cur = conn.cursor()
    try:
        cur.execute("BEGIN IMMEDIATE")

        # убедимся что колонка leader_bonus_given существует (если миграцию ещё не добавил)
        # если нет — просто не упадём: попробуем ALTER TABLE
        cur.execute("PRAGMA table_info(users)")
        cols = {r["name"] for r in cur.fetchall()}
        if "leader_bonus_given" not in cols:
            cur.execute("ALTER TABLE users ADD COLUMN leader_bonus_given INTEGER DEFAULT 0")
            cols.add("leader_bonus_given")

        cur.execute("SELECT status, leader_bonus_given FROM users WHERE tg_id=?", (int(tg_id),))
        u = cur.fetchone()
        if not u:
            conn.rollback()
            return False

        status = str(u["status"] or "newbie")
        if status == "leader":
            conn.rollback()
            return False

        bonus_given = int(u["leader_bonus_given"] or 0)

        cur.execute(
            """
            SELECT COUNT(*) AS cnt
            FROM users
            WHERE invited_by = ?
              AND COALESCE(total_topup_usdt, 0) >= ?
            """,
            (int(tg_id), float(LEADER_REF_MIN_TOPUP_USDT)),
        )
        cnt = int((cur.fetchone() or {})["cnt"] or 0)

        if cnt < int(LEADER_NEED_REFS):
            conn.rollback()
            return False

        cur.execute("UPDATE users SET status='leader' WHERE tg_id=?", (int(tg_id),))

        if bonus_given == 0:
            cur.execute(
                """
                UPDATE users
                SET usdt_balance = COALESCE(usdt_balance, 0) + ?,
                    leader_bonus_given = 1
                WHERE tg_id = ?
                """,
                (float(LEADER_BONUS_USDT), int(tg_id)),
            )

        conn.commit()
        return True
    except Exception:
        conn.rollback()
        return False
    finally:
        conn.close()


# =========================
# UI: Activation menu
# =========================
@router.callback_query(F.data == "activation_menu")
async def activation_menu(call: CallbackQuery, db: Database, cfg: Config, premium: PremiumEmoji):
    await premium.answer_html(
        call.message,
        "⚡️ <b>Активация</b>\n\nВыберите статус 👇",
        reply_markup=_activation_menu_kb(),
    )
    await call.answer()


# =========================
# ACTIVE: info + invoice
# =========================
@router.callback_query(F.data == "activation_active_info")
async def activation_active_info(call: CallbackQuery, db: Database, cfg: Config, premium: PremiumEmoji):
    tg_id = call.from_user.id
    u = db.get_user(tg_id)

    # если вдруг нет юзера (редко, но бывает)
    if not u:
        db.create_user(
            tg_id=tg_id,
            username=call.from_user.username or "NoUsername",
            referrer_id=None,
            first_name=call.from_user.first_name,
        )
        u = db.get_user(tg_id) or {}

    total_topup = float((u["total_topup_usdt"] if "total_topup_usdt" in u.keys() else 0.0) or 0.0)
    done = int((u["tasks_completed_total"] if "tasks_completed_total" in u.keys() else 0) or 0)
    created = int((u["tasks_created_total"] if "tasks_created_total" in u.keys() else 0) or 0)
    status = str((u["status"] if "status" in u.keys() else "newbie") or "newbie")

    text = (
        "🟢 <b>Статус «Активный»</b>\n\n"
        "Условия:\n"
        f"• Пополнить <b>{ACTIVE_TOPUP_USDT:.0f} USDT</b>\n"
        f"• Выполнить <b>{ACTIVE_NEED_DONE} заданий</b>\n"
        f"• Создать <b>{ACTIVE_NEED_CREATED} заданий</b>\n\n"
        "Ваш прогресс:\n"
        f"• Пополнено: <b>{total_topup:.2f}/{ACTIVE_TOPUP_USDT:.2f}</b>\n"
        f"• Выполнено: <b>{min(done, ACTIVE_NEED_DONE)}/{ACTIVE_NEED_DONE}</b>\n"
        f"• Создано: <b>{min(created, ACTIVE_NEED_CREATED)}/{ACTIVE_NEED_CREATED}</b>\n\n"
        f"Текущий статус: <b>{'👑 Лидер' if status=='leader' else ('🟢 Активный' if status=='active' else '🔘 Новичок')}</b>"
    )

    await premium.answer_html(call.message, text, reply_markup=_active_pay_kb())
    await call.answer()


@router.callback_query(F.data == "activation_active_pay")
async def activation_active_pay(call: CallbackQuery, db: Database, cfg: Config, premium: PremiumEmoji):
    tg_id = call.from_user.id
    u = db.get_user(tg_id)

    if not u:
        db.create_user(
            tg_id=tg_id,
            username=call.from_user.username or "NoUsername",
            referrer_id=None,
            first_name=call.from_user.first_name,
        )
        u = db.get_user(tg_id)

    if not getattr(cfg, "CRYPTOBOT_TOKEN", None):
        await call.answer("❌ CRYPTOBOT_TOKEN не задан в .env", show_alert=True)
        return

    api = CryptoBotAPI(
        token=cfg.CRYPTOBOT_TOKEN,
        base_url=getattr(cfg, "CRYPTOBOT_API_BASE", "https://pay.crypt.bot/api"),
    )

    inv = await api.create_invoice(
        amount=float(ACTIVE_TOPUP_USDT),
        asset="USDT",
        description=f"DigiBot • Активация Активный ({ACTIVE_TOPUP_USDT:.0f} USDT)",
    )

    invoice_id = str(inv["invoice_id"])
    pay_url = str(inv["pay_url"])

    _db_create_topup(db, user_id=int(u["tg_id"]), amount_usdt=float(ACTIVE_TOPUP_USDT), invoice_id=invoice_id)

    await premium.answer_html(
        call.message,
        f"🧾 <b>Счёт на {ACTIVE_TOPUP_USDT:.0f} USDT создан</b>\n\n"
        "Нажмите <b>Оплатить</b>, затем <b>Проверить оплату</b>.",
        reply_markup=_invoice_kb(pay_url, invoice_id),
    )
    await call.answer()


@router.callback_query(F.data.startswith("activation_check:"))
async def activation_check(call: CallbackQuery, db: Database, cfg: Config, premium: PremiumEmoji):
    invoice_id = call.data.split(":", 1)[1].strip()

    topup = _db_get_topup_by_invoice(db, invoice_id)
    if not topup:
        await call.answer("❌ Счёт не найден", show_alert=True)
        return

    if str(topup["status"] or "") == "paid":
        await call.answer("✅ Уже оплачено", show_alert=True)
        return

    api = CryptoBotAPI(
        token=cfg.CRYPTOBOT_TOKEN,
        base_url=getattr(cfg, "CRYPTOBOT_API_BASE", "https://pay.crypt.bot/api"),
    )
    info = await api.get_invoice(invoice_id=str(invoice_id))
    status = str(info.get("status") or "").lower()

    if status != "paid":
        await call.answer("⏳ Пока не оплачено", show_alert=True)
        return

    user_id = int(topup["user_id"])
    amount = float(topup["amount_usdt"] or ACTIVE_TOPUP_USDT)

    # зачисляем
    db.add_usdt(user_id, amount)
    _db_mark_topup_paid(db, invoice_id)

    # пробуем активировать (после пополнения) — статус станет active, если 7/7 и 7/7 выполнены
    try:
        db.try_activate_user(user_id)
    except Exception:
        pass

    await premium.answer_html(
        call.message,
        "✅ <b>Оплата подтверждена!</b>\n\n"
        f"💵 Пополнено: <b>{amount:.2f} USDT</b>\n"
        f"Если выполнены задания <b>{ACTIVE_NEED_DONE}/{ACTIVE_NEED_DONE}</b> и <b>{ACTIVE_NEED_CREATED}/{ACTIVE_NEED_CREATED}</b> — статус станет <b>Активный</b> автоматически.",
        reply_markup=_active_pay_kb(),
    )
    await call.answer("✅ Оплачено!", show_alert=True)


# =========================
# LEADER: info + check
# =========================
@router.callback_query(F.data == "activation_leader_info")
async def activation_leader_info(call: CallbackQuery, db: Database, cfg: Config, premium: PremiumEmoji):
    tg_id = call.from_user.id

    u = db.get_user(tg_id)
    if not u:
        db.create_user(
            tg_id=tg_id,
            username=call.from_user.username or "NoUsername",
            referrer_id=None,
            first_name=call.from_user.first_name,
        )
        u = db.get_user(tg_id) or {}

    cnt = _leader_progress_raw(db, tg_id)

    text = (
        "👑 <b>Статус «Лидер»</b>\n\n"
        "Условия:\n"
        f"• Привести <b>{LEADER_NEED_REFS} рефералов</b>\n"
        f"• Каждый должен пополнить <b>от {LEADER_REF_MIN_TOPUP_USDT:.0f} USDT</b>\n\n"
        "Награды:\n"
        f"• +<b>{LEADER_BONUS_USDT:.0f} USDT</b> на баланс\n"
        "• Открывается <b>DIGI → USDT</b> по курсу <b>5000 DIGI = 1 USDT</b>\n\n"
        f"Ваш прогресс: <b>{cnt}/{LEADER_NEED_REFS}</b>"
    )

    await premium.answer_html(call.message, text, reply_markup=_leader_kb())
    await call.answer()


@router.callback_query(F.data == "activation_leader_check")
async def activation_leader_check(call: CallbackQuery, db: Database, cfg: Config, premium: PremiumEmoji):
    tg_id = call.from_user.id

    granted = _try_grant_leader_raw(db, tg_id)
    cnt = _leader_progress_raw(db, tg_id)

    if granted:
        await premium.answer_html(
            call.message,
            "🎉 <b>Поздравляем!</b>\n\n"
            "Вы получили статус <b>Лидер</b>.\n"
            f"✅ Начислено: <b>+{LEADER_BONUS_USDT:.0f} USDT</b>\n"
            "✅ Теперь доступна конвертация <b>DIGI → USDT</b>.",
            reply_markup=_leader_kb(),
        )
        await call.answer("✅ Статус Лидер выдан!", show_alert=True)
    else:
        await call.answer(f"Пока прогресс {cnt}/{LEADER_NEED_REFS}", show_alert=True)