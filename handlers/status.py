# handlers/status.py
from __future__ import annotations

from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import Config
from database import Database
from services.premium_emoji import PremiumEmoji

router = Router()

# =========================
# Constants (правь тут)
# =========================
ACTIVE_TOPUP_USDT = 10.0
ACTIVE_NEED_DONE = 7
ACTIVE_NEED_CREATED = 7

# ✅ Новый Лидер: баланс >= 100 USDT + обязательно статус Активный
LEADER_NEED_BALANCE_USDT = 100.0
LEADER_BONUS_USDT = 10.0


# =========================
# Keyboards
# =========================
def _activation_menu_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="💚 Активный", callback_data="activation_active_info")
    kb.button(text="💜 Лидер", callback_data="activation_leader_info")
    kb.button(text="🏠 В меню", callback_data="go_menu")
    kb.adjust(1)
    return kb.as_markup()


def _active_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Активировать", callback_data="activation_active_apply")
    kb.button(text="🏠 В меню", callback_data="go_menu")
    kb.adjust(1)
    return kb.as_markup()


def _leader_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="🔄 Проверить прогресс", callback_data="activation_leader_check")
    kb.button(text="🏠 В меню", callback_data="go_menu")
    kb.adjust(1)
    return kb.as_markup()


# =========================
# DB helpers (локально)
# =========================
def _leader_progress_raw(db: Database, tg_id: int) -> float:
    """
    Прогресс Лидера = текущий баланс USDT (usdt_balance).
    """
    conn = db._connect()
    cur = conn.cursor()
    cur.execute("SELECT usdt_balance FROM users WHERE tg_id=?", (int(tg_id),))
    row = cur.fetchone()
    conn.close()
    return float(row["usdt_balance"] or 0.0) if row else 0.0


def _try_grant_leader_raw(db: Database, tg_id: int) -> bool:
    """
    Выдаёт статус leader если:
    - текущий статус == active
    - usdt_balance >= 100
    Бонус +10 USDT выдаётся один раз (leader_bonus_given).
    """
    conn = db._connect()
    cur = conn.cursor()
    try:
        cur.execute("BEGIN IMMEDIATE")

        # миграция: leader_bonus_given (если нет колонки)
        cur.execute("PRAGMA table_info(users)")
        cols = {r["name"] for r in cur.fetchall()}
        if "leader_bonus_given" not in cols:
            cur.execute("ALTER TABLE users ADD COLUMN leader_bonus_given INTEGER DEFAULT 0")

        cur.execute(
            "SELECT status, usdt_balance, leader_bonus_given FROM users WHERE tg_id=?",
            (int(tg_id),),
        )
        u = cur.fetchone()
        if not u:
            conn.rollback()
            return False

        status = str(u["status"] or "newbie")
        usdt_balance = float(u["usdt_balance"] or 0.0)
        bonus_given = int(u["leader_bonus_given"] or 0)

        # ✅ если уже лидер — ничего не делаем
        if status == "leader":
            conn.rollback()
            return False

        # ✅ ОБЯЗАТЕЛЬНО должен быть активный
        if status != "active":
            conn.rollback()
            return False

        # ✅ условие по балансу
        if usdt_balance + 1e-9 < float(LEADER_NEED_BALANCE_USDT):
            conn.rollback()
            return False

        # выдаём статус leader
        cur.execute("UPDATE users SET status='leader' WHERE tg_id=?", (int(tg_id),))

        # бонус 1 раз
        if float(LEADER_BONUS_USDT) > 0 and bonus_given == 0:
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
        "🟢 <b>Активация статуса</b>\n\nВыберите статус 👇",
        reply_markup=_activation_menu_kb(),
    )
    await call.answer()


# =========================
# ACTIVE: info + manual activate (deduct 10 USDT)
# =========================
@router.callback_query(F.data == "activation_active_info")
async def activation_active_info(call: CallbackQuery, db: Database, cfg: Config, premium: PremiumEmoji):
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

    usdt_balance = float((u["usdt_balance"] if "usdt_balance" in u.keys() else 0.0) or 0.0)
    done = int((u["tasks_completed_total"] if "tasks_completed_total" in u.keys() else 0) or 0)
    created = int((u["tasks_created_total"] if "tasks_created_total" in u.keys() else 0) or 0)
    status = str((u["status"] if "status" in u.keys() else "newbie") or "newbie")

    status_title = "💜 Лидер" if status == "leader" else ("💚 Активный" if status == "active" else "💙 Новичок")

    if status in ("active", "leader"):
        kb = InlineKeyboardBuilder()
        kb.button(text="⬅️ Назад", callback_data="activation_menu")
        kb.adjust(1)
        reply_kb = kb.as_markup()
        extra = "\n\n✅ <b>Статус уже активирован.</b>"
    else:
        reply_kb = _active_kb()
        extra = "\n\n⚠️ <b>Важно:</b> при нажатии «Активировать» с баланса спишется <b>10 USDT</b>."

    text = (
        "💚 <b>Статус «Активный»</b>\n\n"
        "ℹ️ <b>Условия:</b>\n"
        f"<b>• На балансе должно быть {ACTIVE_TOPUP_USDT:.0f} USDT</b>\n"
        f"<b>• Выполнить {ACTIVE_NEED_DONE} заданий</b>\n"
        f"<b>• Создать {ACTIVE_NEED_CREATED} заданий</b>\n\n"
        "🟢 <b>Ваш прогресс:</b>\n"
        f"<b>• Баланс USDT: {usdt_balance:.2f}</b>\n"
        f"<b>• Выполнено: {min(done, ACTIVE_NEED_DONE)}/{ACTIVE_NEED_DONE}</b>\n"
        f"<b>• Создано: {min(created, ACTIVE_NEED_CREATED)}/{ACTIVE_NEED_CREATED}</b>\n\n"
        f"<b>Текущий статус: {status_title}</b>"
        f"{extra}"
    )

    await premium.answer_html(call.message, text, reply_markup=reply_kb)
    await call.answer()


@router.callback_query(F.data == "activation_active_apply")
async def activation_active_apply(call: CallbackQuery, db: Database, cfg: Config, premium: PremiumEmoji):
    tg_id = call.from_user.id

    u = db.get_user(tg_id)
    if not u:
        await call.answer("❌ Профиль не найден", show_alert=True)
        return

    status = str((u["status"] if "status" in u.keys() else "newbie") or "newbie")
    if status in ("active", "leader"):
        await call.answer("✅ Статус уже активен", show_alert=True)
        return

    done = int((u["tasks_completed_total"] if "tasks_completed_total" in u.keys() else 0) or 0)
    created = int((u["tasks_created_total"] if "tasks_created_total" in u.keys() else 0) or 0)

    if done < ACTIVE_NEED_DONE:
        await call.answer("⛔ Нужно выполнить 7 заданий", show_alert=True)
        return
    if created < ACTIVE_NEED_CREATED:
        await call.answer("⛔ Нужно создать 7 заданий", show_alert=True)
        return

    conn = db._connect()
    cur = conn.cursor()
    try:
        cur.execute("BEGIN IMMEDIATE")

        cur.execute("SELECT usdt_balance, status FROM users WHERE tg_id=?", (int(tg_id),))
        row = cur.fetchone()
        if not row:
            conn.rollback()
            await call.answer("❌ Пользователь не найден", show_alert=True)
            return

        current_bal = float(row["usdt_balance"] or 0.0)
        current_status = str(row["status"] or "newbie")
        if current_status in ("active", "leader"):
            conn.rollback()
            await call.answer("✅ Уже активен", show_alert=True)
            return

        if current_bal + 1e-9 < ACTIVE_TOPUP_USDT:
            conn.rollback()
            await call.answer("⛔ Недостаточно USDT (нужно 10)", show_alert=True)
            return

        cur.execute(
            """
            UPDATE users
            SET usdt_balance = usdt_balance - ?,
                status = 'active'
            WHERE tg_id=?
            """,
            (float(ACTIVE_TOPUP_USDT), int(tg_id)),
        )

        conn.commit()
    except Exception:
        conn.rollback()
        await call.answer("Ошибка активации", show_alert=True)
        return
    finally:
        conn.close()

    await premium.answer_html(
        call.message,
        "🎉 <b>Поздравляем!</b>\n\n"
        "💚 Статус <b>«Активный»</b> активирован.\n"
        f"💳 Списано с баланса: <b>{ACTIVE_TOPUP_USDT:.0f} USDT</b>",
        reply_markup=_activation_menu_kb(),
    )
    await call.answer("✅ Активировано!", show_alert=True)


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

    balance = _leader_progress_raw(db, tg_id)
    progress = min(balance, float(LEADER_NEED_BALANCE_USDT))

    text = (
        "💜 <b>Статус «Лидер»</b>\n\n"
        "ℹ️ <b>Условия:</b>\n"
        "<b>• Получите статус «Активный»</b>\n"
        f"<b>• Заработайте {LEADER_NEED_BALANCE_USDT:.0f} USDT</b>\n\n"
        "🎁 <b>Награды:</b>\n"
        f"<b> +{LEADER_BONUS_USDT:.0f} USDT на баланс</b>\n"
        "🔄<b> Вы сможете конвертировать монеты DIGI/USDT и зарабатывать</b>\n\n"
        f"📊<b> Ваш прогресс: {progress:.2f}/{LEADER_NEED_BALANCE_USDT:.0f} USDT</b>"
    )

    await premium.answer_html(call.message, text, reply_markup=_leader_kb())
    await call.answer()


@router.callback_query(F.data == "activation_leader_check")
async def activation_leader_check(call: CallbackQuery, db: Database, cfg: Config, premium: PremiumEmoji):
    tg_id = call.from_user.id

    granted = _try_grant_leader_raw(db, tg_id)
    balance = _leader_progress_raw(db, tg_id)
    progress = min(balance, float(LEADER_NEED_BALANCE_USDT))

    if granted:
        await premium.answer_html(
            call.message,
            "🎉 <b>Поздравляем!</b>\n\n"
            "Вы получили статус <b>Лидер</b>.\n"
            f"✅ Начислено: <b>+{LEADER_BONUS_USDT:.0f} USDT</b>\n"
            "✅ Лидер имеет все функции <b>Активного</b> + конвертацию <b>DIGI → USDT</b>.",
            reply_markup=_leader_kb(),
        )
        await call.answer("✅ Статус Лидер выдан!", show_alert=True)
    else:
        # точная причина для пользователя
        u = db.get_user(tg_id) or {}
        status = str((u["status"] if hasattr(u, "keys") and "status" in u.keys() else "newbie") or "newbie")

        if status != "active":
            await call.answer("⛔ Сначала нужен статус «Активный»", show_alert=True)
        else:
            await call.answer(
                f"Пока прогресс {progress:.2f}/{LEADER_NEED_BALANCE_USDT:.0f} USDT",
                show_alert=True,
            )
