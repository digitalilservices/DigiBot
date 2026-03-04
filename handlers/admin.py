# handlers/admin.py
from __future__ import annotations

import sqlite3
import math

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from services.cryptobot import CryptoBotAPI
from datetime import datetime
from config import Config
from database import Database
from keyboards.admin_menu import admin_panel_inline, admin_tasks_inline, admin_ads_inline
from keyboards.main_menu import admin_contact_inline

# ✅ Premium Emoji (custom_emoji entities + HTML->entities)
from services.premium_emoji import PremiumEmoji

router = Router()

ADMIN_ADS_PER_PAGE = 1
ADMIN_TOPUPS_PER_PAGE = 1
ADMIN_WD_PER_PAGE = 1  # ✅ заявки на вывод


# ==============================
# ✅ Premium send helpers (НЕ логика, только способ отправки)
# ==============================
async def _answer_html(message: Message, premium: PremiumEmoji, html_text: str, **kwargs):
    return await premium.answer_html(message, html_text, **kwargs)


async def _edit_html(message: Message, premium: PremiumEmoji, html_text: str, **kwargs):
    return await premium.edit_html(message, html_text, **kwargs)


# ==============================
# FSM
# ==============================
class AdminTaskAddStates(StatesGroup):
    waiting_title = State()
    waiting_desc = State()
    waiting_reward = State()


class AdminTaskDeleteStates(StatesGroup):
    waiting_task_id = State()


class AdminAdsDeleteStates(StatesGroup):
    waiting_ad_id = State()


class AdminGiveDigiStates(StatesGroup):
    waiting_user = State()
    waiting_amount = State()


class AdminGiveUsdtStates(StatesGroup):
    waiting_user = State()
    waiting_amount = State()


class AdminAppStatsStates(StatesGroup):
    waiting_turnover = State()
    waiting_invoices = State()
    waiting_payments = State()
    waiting_users = State()
    waiting_conversion = State()


# ==============================
# helpers
# ==============================
def _is_admin(user_id: int, cfg: Config) -> bool:
    return int(user_id) == int(cfg.ADMIN_ID)

def _parse_usdt_amount(txt: str):
    try:
        s = (txt or "").strip().replace(",", ".").replace(" ", "")
        return float(s)
    except Exception:
        return None

def _admin_guard(call_or_msg, cfg: Config) -> bool:
    return _is_admin(call_or_msg.from_user.id, cfg)


def _back_kb(cb: str = "admin_back"):
    kb = InlineKeyboardBuilder()
    kb.button(text="⬅️ Назад", callback_data=cb)
    kb.adjust(1)
    return kb.as_markup()


# ==============================
# ADS
# ==============================
def _admin_ads_nav_kb(page: int, total_pages: int):
    kb = InlineKeyboardBuilder()

    if page > 0:
        kb.button(text="⬅️", callback_data=f"admin_ads_page:{page-1}")

    kb.button(text=f"{page+1}/{max(total_pages,1)}", callback_data="admin_ads_noop")

    if page < total_pages - 1:
        kb.button(text="➡️", callback_data=f"admin_ads_page:{page+1}")

    kb.adjust(3)
    kb.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_ads"))
    return kb.as_markup()


def _admin_ads_format(ad, idx: int, total: int) -> str:
    ad_id = int(ad["id"])
    user_id = int(ad["user_id"])
    desc = (ad["description"] or "").strip()
    link = (ad["link"] or "").strip()
    expires = (ad["expires_at"] or "").strip()

    return (
        f"📢 <b>Реклама</b> ({idx}/{total})\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        f"🆔 <b>ID {ad_id}</b> | user_id: <code>{user_id}</code>\n"
        f"📝 {desc}\n"
        f"🔗 {link}\n"
        f"⏳ До: <b>{expires}</b>"
    )


async def _admin_show_ads_page(call: CallbackQuery, db: Database, page: int, premium: PremiumEmoji):
    conn = db._connect()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) AS cnt FROM ads")
    total = int(cur.fetchone()["cnt"])

    if total <= 0:
        conn.close()
        await _answer_html(call.message, premium, "📢 Реклам пока нет.", reply_markup=_back_kb("admin_ads"))
        return

    total_pages = max(1, math.ceil(total / ADMIN_ADS_PER_PAGE))
    page = max(0, min(page, total_pages - 1))
    offset = page * ADMIN_ADS_PER_PAGE

    cur.execute("""
        SELECT * FROM ads
        ORDER BY id DESC
        LIMIT ? OFFSET ?
    """, (ADMIN_ADS_PER_PAGE, offset))
    rows = cur.fetchall()
    conn.close()

    if not rows:
        await _answer_html(call.message, premium, "📢 Реклам пока нет.", reply_markup=_back_kb("admin_ads"))
        return

    ad = rows[0]
    text = _admin_ads_format(ad, idx=page + 1, total=total)

    try:
        await _edit_html(call.message, premium, text, reply_markup=_admin_ads_nav_kb(page, total_pages))
    except Exception:
        await _answer_html(call.message, premium, text, reply_markup=_admin_ads_nav_kb(page, total_pages))


# ==============================
# pending submissions kb
# ==============================
def _pending_kb(sub_id: int):
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Approve", callback_data=f"admin_sub_approve:{sub_id}")
    kb.button(text="❌ Deny", callback_data=f"admin_sub_deny:{sub_id}")
    kb.button(text="⬅️ Назад", callback_data="admin_back")
    kb.adjust(2, 1)
    return kb.as_markup()


def _market_pending_kb(msub_id: int):
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Approve", callback_data=f"admin_market_approve:{msub_id}")
    kb.button(text="❌ Deny", callback_data=f"admin_market_deny:{msub_id}")
    kb.button(text="⬅️ Назад", callback_data="admin_back")
    kb.adjust(2, 1)
    return kb.as_markup()


# ==============================
# Market manual submissions table
# ==============================
def _ensure_market_manual_table(db: Database):
    conn = db._connect()
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS market_manual_submissions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        task_id INTEGER NOT NULL,
        worker_id INTEGER NOT NULL,
        screenshot_file_id TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'pending',
        created_at TEXT NOT NULL,
        UNIQUE(task_id, worker_id)
    )
    """)
    conn.commit()
    conn.close()


# ==============================
# ✅ WITHDRAW REQUESTS
# ==============================
def _ensure_withdraw_table(db: Database):
    conn = db._connect()
    cur = conn.cursor()

    # 1) создаём таблицу в правильной схеме
    cur.execute("""
    CREATE TABLE IF NOT EXISTS withdraw_requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        source TEXT NOT NULL DEFAULT 'ref', -- ref/win
        amount_usdt REAL NOT NULL,
        address TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'pending', -- pending/processed/denied
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        processed_at TEXT,
        processed_by INTEGER,
        comment TEXT
    )
    """)

    # 2) миграция: если таблица уже была создана без source — добавим колонку
    cur.execute("PRAGMA table_info(withdraw_requests)")
    cols = {row["name"] for row in cur.fetchall()}
    if "source" not in cols:
        cur.execute("ALTER TABLE withdraw_requests ADD COLUMN source TEXT NOT NULL DEFAULT 'ref'")
    if "check_id" not in cols:
        cur.execute("ALTER TABLE withdraw_requests ADD COLUMN check_id INTEGER")

    if "check_url" not in cols:
        cur.execute("ALTER TABLE withdraw_requests ADD COLUMN check_url TEXT")

    conn.commit()
    conn.close()


def _withdraw_actions_kb(req_id: int):
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Processed", callback_data=f"admin_wd_process:{req_id}")
    kb.button(text="❌ Deny + Refund", callback_data=f"admin_wd_deny:{req_id}")
    kb.button(text="⬅️ Назад", callback_data="admin_withdrawals")
    kb.adjust(2, 1)
    return kb.as_markup()

def _withdraw_format(r, idx: int, total: int) -> str:
    username = (r["username"] or "").strip()
    first_name = (r["first_name"] or "").strip()

    uname_line = f"@{username}" if username else "—"
    name_line = first_name if first_name else "—"

    src = str((r["source"] if "source" in r.keys() else "ref") or "ref")
    if src == "win":
        src_name = "🎰 Выигрышный"
    elif src == "dep":
        src_name = "🔒 Депозит"
    else:
        src_name = "👥 Реферальный"

    return (
        f"💸 <b>Заявка на вывод</b> ({idx}/{total})\n\n"
        f"🆔 <b>ID {int(r['id'])}</b>\n"
        f"👤 user_id: <code>{int(r['user_id'])}</code>\n"
        f"👤 Имя: <b>{name_line}</b>\n"
        f"👤 Username: <b>{uname_line}</b>\n"
        f"📦 Источник: <b>{src_name}</b>\n"
        f"💵 Сумма: <b>{float(r['amount_usdt']):.2f} USDT</b>\n"
        f"🏦 Кошелёк: <code>{r['address']}</code>\n"
        f"📌 Статус: <b>{r['status']}</b>\n"
        f"🕒 Создано: <b>{r['created_at']}</b>\n"
    )

async def _admin_show_withdraw_page(call: CallbackQuery, db: Database, page: int, premium: PremiumEmoji):
    _ensure_withdraw_table(db)

    conn = db._connect()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) AS cnt FROM withdraw_requests WHERE status='pending'")
    total = int(cur.fetchone()["cnt"])

    if total <= 0:
        conn.close()
        await _answer_html(call.message, premium, "💸 Заявок на вывод нет.", reply_markup=_back_kb("admin_back"))
        return

    total_pages = max(1, math.ceil(total / ADMIN_WD_PER_PAGE))
    page = max(0, min(page, total_pages - 1))
    offset = page * ADMIN_WD_PER_PAGE

    cur.execute("""
        SELECT wr.*, u.username AS username, u.first_name AS first_name
        FROM withdraw_requests wr
        LEFT JOIN users u ON u.tg_id = wr.user_id
        WHERE wr.status='pending'
        ORDER BY wr.id DESC
        LIMIT ? OFFSET ?
    """, (ADMIN_WD_PER_PAGE, offset))
    rows = cur.fetchall()
    conn.close()

    if not rows:
        await _answer_html(call.message, premium, "💸 Заявок на вывод нет.", reply_markup=_back_kb("admin_back"))
        return

    r = rows[0]
    text = _withdraw_format(r, idx=page + 1, total=total)

    try:
        await _edit_html(call.message, premium, text, reply_markup=_withdraw_actions_kb(int(r["id"])))
    except Exception:
        await _answer_html(call.message, premium, text, reply_markup=_withdraw_actions_kb(int(r["id"])))

# ==============================
# APP STATS (editable)
# ==============================
def _appstats_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Оборот ($)", callback_data="appstats_edit:turnover")],
        [InlineKeyboardButton(text="✏️ Созданные счета", callback_data="appstats_edit:invoices")],
        [InlineKeyboardButton(text="✏️ Кол-во оплат", callback_data="appstats_edit:payments")],
        [InlineKeyboardButton(text="✏️ Пользователи", callback_data="appstats_edit:users")],
        [InlineKeyboardButton(text="✏️ Конверсия (%)", callback_data="appstats_edit:conversion")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_back")],
    ])


def _render_appstats(st: dict) -> str:
    return (
        "📈 <b>Статистика приложения DigaroBot</b>\n\n"
        f"💵 Оборот: <b>${st['turnover_usdt']:.2f}</b>\n"
        f"🧾 Созданных счетов: <b>{st['invoices_created']}</b>\n"
        f"✅ Оплат: <b>{st['payments_count']}</b>\n"
        f"👥 Пользователей: <b>{st['users_count']}</b>\n"
        f"📈 Конверсия: <b>{st['conversion_pct']}%</b>\n\n"
        "Выбери что изменить 👇"
    )


@router.callback_query(F.data == "admin_appstats")
async def admin_appstats(call: CallbackQuery, db: Database, cfg: Config, premium: PremiumEmoji, state: FSMContext):
    if not _admin_guard(call, cfg):
        await call.answer("⛔️ Нет доступа", show_alert=True)
        return

    await state.clear()
    st = db.get_app_stats()
    text = _render_appstats(st)
    try:
        text = premium.format(text)
    except Exception:
        pass

    await call.message.edit_text(text, reply_markup=_appstats_kb(), parse_mode="HTML")
    await call.answer()


@router.callback_query(F.data.startswith("appstats_edit:"))
async def admin_appstats_edit(call: CallbackQuery, db: Database, cfg: Config, premium: PremiumEmoji, state: FSMContext):
    if not _admin_guard(call, cfg):
        await call.answer("⛔️ Нет доступа", show_alert=True)
        return

    field = call.data.split(":", 1)[1]

    if field == "turnover":
        await state.set_state(AdminAppStatsStates.waiting_turnover)
        msg = "Введи новый <b>оборот</b> в долларах (пример: <code>376.95</code>):"
    elif field == "invoices":
        await state.set_state(AdminAppStatsStates.waiting_invoices)
        msg = "Введи новое <b>кол-во созданных счетов</b> (пример: <code>93</code>):"
    elif field == "payments":
        await state.set_state(AdminAppStatsStates.waiting_payments)
        msg = "Введи новое <b>кол-во оплат</b> (пример: <code>53</code>):"
    elif field == "users":
        await state.set_state(AdminAppStatsStates.waiting_users)
        msg = "Введи новое <b>кол-во пользователей</b> (пример: <code>283</code>):"
    elif field == "conversion":
        await state.set_state(AdminAppStatsStates.waiting_conversion)
        msg = "Введи новую <b>конверсию</b> в процентах (пример: <code>56</code>):"
    else:
        await call.answer("Неизвестное поле", show_alert=True)
        return

    try:
        msg = premium.format(msg)
    except Exception:
        pass

    await call.message.edit_text(msg, parse_mode="HTML")
    await call.answer()


def _parse_int(txt: str) -> int | None:
    try:
        s = (txt or "").strip().replace(" ", "")
        return int(s)
    except Exception:
        return None


@router.message(AdminAppStatsStates.waiting_turnover)
async def appstats_set_turnover(message: Message, db: Database, cfg: Config, premium: PremiumEmoji, state: FSMContext):
    if not _is_admin(message.from_user.id, cfg):
        return
    val = _parse_usdt_amount(message.text)  # уже есть в admin.py
    if val is None or val < 0:
        await message.answer("❌ Введи число, пример: 376.95")
        return
    db.set_app_stats(turnover_usdt=val)
    await state.clear()
    st = db.get_app_stats()
    await message.answer(_render_appstats(st), reply_markup=_appstats_kb(), parse_mode="HTML")


@router.message(AdminAppStatsStates.waiting_invoices)
async def appstats_set_invoices(message: Message, db: Database, cfg: Config, premium: PremiumEmoji, state: FSMContext):
    if not _is_admin(message.from_user.id, cfg):
        return
    val = _parse_int(message.text)
    if val is None or val < 0:
        await message.answer("❌ Введи целое число, пример: 93")
        return
    db.set_app_stats(invoices_created=val)
    await state.clear()
    st = db.get_app_stats()
    await message.answer(_render_appstats(st), reply_markup=_appstats_kb(), parse_mode="HTML")


@router.message(AdminAppStatsStates.waiting_payments)
async def appstats_set_payments(message: Message, db: Database, cfg: Config, premium: PremiumEmoji, state: FSMContext):
    if not _is_admin(message.from_user.id, cfg):
        return
    val = _parse_int(message.text)
    if val is None or val < 0:
        await message.answer("❌ Введи целое число, пример: 53")
        return
    db.set_app_stats(payments_count=val)
    await state.clear()
    st = db.get_app_stats()
    await message.answer(_render_appstats(st), reply_markup=_appstats_kb(), parse_mode="HTML")


@router.message(AdminAppStatsStates.waiting_users)
async def appstats_set_users(message: Message, db: Database, cfg: Config, premium: PremiumEmoji, state: FSMContext):
    if not _is_admin(message.from_user.id, cfg):
        return
    val = _parse_int(message.text)
    if val is None or val < 0:
        await message.answer("❌ Введи целое число, пример: 283")
        return
    db.set_app_stats(users_count=val)
    await state.clear()
    st = db.get_app_stats()
    await message.answer(_render_appstats(st), reply_markup=_appstats_kb(), parse_mode="HTML")


@router.message(AdminAppStatsStates.waiting_conversion)
async def appstats_set_conversion(message: Message, db: Database, cfg: Config, premium: PremiumEmoji, state: FSMContext):
    if not _is_admin(message.from_user.id, cfg):
        return
    val = _parse_int(message.text)
    if val is None or val < 0 or val > 100:
        await message.answer("❌ Введи число 0..100, пример: 56")
        return
    db.set_app_stats(conversion_pct=val)
    await state.clear()
    st = db.get_app_stats()
    await message.answer(_render_appstats(st), reply_markup=_appstats_kb(), parse_mode="HTML")

# ==============================
# PUBLIC: Администратор
# ==============================
@router.message(F.text == "👨‍💻 Администратор")
async def admin_contact(message: Message, cfg: Config, premium: PremiumEmoji):
    text = (
        "👨‍💻 <b>Администратор</b>\n\n"
        "⏳ <b>Ожидание ответа — до 1 час</b>\n"
    )
    await _answer_html(message, premium, text, reply_markup=admin_contact_inline(cfg.SUPPORT_USERNAME))


# ==============================
# ADMIN PANEL ENTRY
# ==============================
@router.message(F.text == "🔐 Админ Панель")
async def admin_panel_open(message: Message, cfg: Config, premium: PremiumEmoji):
    if not _is_admin(message.from_user.id, cfg):
        await _answer_html(message, premium, "⛔️ Доступ запрещён.")
        return

    await _answer_html(
        message,
        premium,
        "🔐 <b>Админ Панель</b>\n\nВыберите действие:",
        reply_markup=admin_panel_inline()
    )


@router.callback_query(F.data == "admin_back")
async def admin_back(call: CallbackQuery, cfg: Config, premium: PremiumEmoji):
    if not _admin_guard(call, cfg):
        await call.answer("⛔️ Нет доступа", show_alert=True)
        return

    await _answer_html(
        call.message,
        premium,
        "🔐 <b>Админ Панель</b>\n\nВыберите действие:",
        reply_markup=admin_panel_inline()
    )
    await call.answer()


# ==============================
# STATS
# ==============================
@router.callback_query(F.data == "admin_stats")
async def admin_stats(call: CallbackQuery, db: Database, cfg: Config, premium: PremiumEmoji):
    if not _admin_guard(call, cfg):
        await call.answer("⛔️ Нет доступа", show_alert=True)
        return

    st = db.get_stats()
    text = (
        "📊 <b>Статистика</b>\n\n"
        f"👥 Пользователей: <b>{st['users']}</b>\n"
        f"🟢 Активные (24ч): <b>{st['active_users']}</b>\n"
        f"🪙 Общий баланс (в системе): <b>{int(st['total_balance']):,}</b> DGR"
    )
    await _answer_html(call.message, premium, text, reply_markup=_back_kb())
    await call.answer()


# ==============================
# TOPUPS LIST
# ==============================
def _admin_topups_nav_kb(page: int, total_pages: int):
    kb = InlineKeyboardBuilder()

    if page > 0:
        kb.button(text="⬅️", callback_data=f"admin_topups_page:{page-1}")

    kb.button(text=f"{page+1}/{max(total_pages,1)}", callback_data="admin_topups_noop")

    if page < total_pages - 1:
        kb.button(text="➡️", callback_data=f"admin_topups_page:{page+1}")

    kb.adjust(3)
    kb.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_back"))
    return kb.as_markup()


def _topup_format(r, idx: int, total: int) -> str:
    username = (r["username"] or "").strip()
    first_name = (r["first_name"] or "").strip()

    uname_line = f"@{username}" if username else "—"
    name_line = first_name if first_name else "—"

    return (
        f"🧾 <b>Последние пополнения</b> ({idx}/{total})\n\n"
        f"🆔 <b>ID {int(r['id'])}</b>\n"
        f"👤 user_id: <code>{int(r['user_id'])}</code>\n"
        f"👤 Имя: <b>{name_line}</b>\n"
        f"👤 Username: <b>{uname_line}</b>\n\n"
        f"💵 <b>{float(r['amount_usdt']):.2f} USDT</b> → 💎 <b>{int(r['amount_digi']):,} DGR</b>\n"
        f"📌 status: <b>{r['status']}</b>\n"
        f"🧾 invoice: <code>{r['invoice_id']}</code>\n"
    )


async def _admin_show_topup_page(call: CallbackQuery, db: Database, page: int, premium: PremiumEmoji):
    conn = db._connect()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) AS cnt FROM topups")
    total = int(cur.fetchone()["cnt"])

    if total <= 0:
        conn.close()
        await _answer_html(call.message, premium, "🧾 Пополнений пока нет.", reply_markup=_back_kb())
        return

    total_pages = max(1, math.ceil(total / ADMIN_TOPUPS_PER_PAGE))
    page = max(0, min(page, total_pages - 1))
    offset = page * ADMIN_TOPUPS_PER_PAGE

    cur.execute("""
        SELECT t.*, u.username AS username, u.first_name AS first_name
        FROM topups t
        LEFT JOIN users u ON u.tg_id = t.user_id
        ORDER BY t.id DESC
        LIMIT ? OFFSET ?
    """, (ADMIN_TOPUPS_PER_PAGE, offset))
    rows = cur.fetchall()
    conn.close()

    if not rows:
        await _answer_html(call.message, premium, "🧾 Пополнений пока нет.", reply_markup=_back_kb())
        return

    r = rows[0]
    text = _topup_format(r, idx=page + 1, total=total)

    try:
        await _edit_html(call.message, premium, text, reply_markup=_admin_topups_nav_kb(page, total_pages))
    except Exception:
        await _answer_html(call.message, premium, text, reply_markup=_admin_topups_nav_kb(page, total_pages))


@router.callback_query(F.data == "admin_topups")
async def admin_topups(call: CallbackQuery, db: Database, cfg: Config, premium: PremiumEmoji):
    if not _admin_guard(call, cfg):
        await call.answer("⛔️ Нет доступа", show_alert=True)
        return

    await _admin_show_topup_page(call, db, page=0, premium=premium)
    await call.answer()


@router.callback_query(F.data.startswith("admin_topups_page:"))
async def admin_topups_page(call: CallbackQuery, db: Database, cfg: Config, premium: PremiumEmoji):
    if not _admin_guard(call, cfg):
        await call.answer("⛔️ Нет доступа", show_alert=True)
        return

    page = int(call.data.split(":", 1)[1])
    await _admin_show_topup_page(call, db, page=page, premium=premium)
    await call.answer()


@router.callback_query(F.data == "admin_topups_noop")
async def admin_topups_noop(call: CallbackQuery, cfg: Config):
    if not _admin_guard(call, cfg):
        await call.answer("⛔️ Нет доступа", show_alert=True)
        return
    await call.answer()


# ==============================
# TASKS MENU
# ==============================
@router.callback_query(F.data == "admin_tasks")
async def admin_tasks(call: CallbackQuery, cfg: Config, premium: PremiumEmoji):
    if not _admin_guard(call, cfg):
        await call.answer("⛔️ Нет доступа", show_alert=True)
        return
    await _answer_html(call.message, premium, "🎯 <b>Задания</b>\n\nВыберите:", reply_markup=admin_tasks_inline())
    await call.answer()


@router.callback_query(F.data == "admin_task_add")
async def admin_task_add_start(call: CallbackQuery, state: FSMContext, cfg: Config, premium: PremiumEmoji):
    if not _admin_guard(call, cfg):
        await call.answer("⛔️ Нет доступа", show_alert=True)
        return

    await state.clear()
    await state.set_state(AdminTaskAddStates.waiting_title)
    await _answer_html(
        call.message,
        premium,
        "➕ <b>Добавление задания</b>\n\nВведите <b>название</b> задания:",
        reply_markup=_back_kb()
    )
    await call.answer()


@router.message(AdminTaskAddStates.waiting_title)
async def admin_task_add_title(message: Message, state: FSMContext, cfg: Config, premium: PremiumEmoji):
    if not _is_admin(message.from_user.id, cfg):
        return

    title = (message.text or "").strip()
    if len(title) < 3 or len(title) > 100:
        await _answer_html(message, premium, "❌ Название должно быть 3–100 символов.")
        return

    await state.update_data(title=title)
    await state.set_state(AdminTaskAddStates.waiting_desc)
    await _answer_html(message, premium, "Теперь введите <b>описание</b> задания (до 500 символов):")


@router.message(AdminTaskAddStates.waiting_desc)
async def admin_task_add_desc(message: Message, state: FSMContext, cfg: Config, premium: PremiumEmoji):
    if not _is_admin(message.from_user.id, cfg):
        return

    desc = (message.text or "").strip()
    if len(desc) < 5 or len(desc) > 500:
        await _answer_html(message, premium, "❌ Описание должно быть 5–500 символов.")
        return

    await state.update_data(description=desc)
    await state.set_state(AdminTaskAddStates.waiting_reward)
    await _answer_html(message, premium, "Введите награду в <b>DGR</b> (целое число), например: <b>500</b>")


@router.message(AdminTaskAddStates.waiting_reward)
async def admin_task_add_reward(message: Message, state: FSMContext, db: Database, cfg: Config, premium: PremiumEmoji):
    if not _is_admin(message.from_user.id, cfg):
        return

    raw = (message.text or "").strip().replace(" ", "")
    if not raw.isdigit():
        await _answer_html(message, premium, "❌ Введите число. Например: <b>500</b>")
        return

    reward = int(raw)
    if reward <= 0 or reward > 1_000_000:
        await _answer_html(message, premium, "❌ Награда должна быть 1..1,000,000 DGR.")
        return

    data = await state.get_data()
    db.add_task(title=data["title"], description=data["description"], reward=reward)
    await state.clear()

    await _answer_html(message, premium, "✅ Задание добавлено.", reply_markup=admin_panel_inline())


@router.callback_query(F.data == "admin_task_delete")
async def admin_task_delete_start(call: CallbackQuery, state: FSMContext, cfg: Config, premium: PremiumEmoji):
    if not _admin_guard(call, cfg):
        await call.answer("⛔️ Нет доступа", show_alert=True)
        return

    await state.clear()
    await state.set_state(AdminTaskDeleteStates.waiting_task_id)
    await _answer_html(
        call.message,
        premium,
        "➖ <b>Удаление задания</b>\n\nВведите <b>ID</b> задания (например: 3):",
        reply_markup=_back_kb()
    )
    await call.answer()


@router.message(AdminTaskDeleteStates.waiting_task_id)
async def admin_task_delete(message: Message, state: FSMContext, db: Database, cfg: Config, premium: PremiumEmoji):
    if not _is_admin(message.from_user.id, cfg):
        return

    raw = (message.text or "").strip()
    if not raw.isdigit():
        await _answer_html(message, premium, "❌ Введите ID цифрами.")
        return

    task_id = int(raw)
    db.delete_task(task_id)
    await state.clear()
    await _answer_html(message, premium, "✅ Удалено (если ID существовал).", reply_markup=admin_panel_inline())


# ==============================
# PENDING OLD SUBMISSIONS (tasks)
# ==============================
@router.callback_query(F.data == "admin_pending")
async def admin_pending(call: CallbackQuery, db: Database, cfg: Config, premium: PremiumEmoji):
    if not _admin_guard(call, cfg):
        await call.answer("⛔️ Нет доступа", show_alert=True)
        return

    conn = db._connect()
    cur = conn.cursor()
    cur.execute("""
        SELECT * FROM task_submissions
        WHERE status='pending'
        ORDER BY id DESC
        LIMIT 10
    """)
    subs = cur.fetchall()
    conn.close()

    if not subs:
        await _answer_html(call.message, premium, "✅ Нет заявок на проверке.", reply_markup=_back_kb())
        await call.answer()
        return

    lines = ["🧩 <b>Заявки на проверке (старые tasks)</b>", ""]
    for s in subs:
        lines.append(
            f"🆔 Submission: <b>{s['id']}</b>\n"
            f"👤 user_id: <code>{s['user_id']}</code>\n"
            f"🎯 task_id: <b>{s['task_id']}</b>\n"
            f"📌 status: <b>{s['status']}</b>\n"
        )

    last = subs[0]
    await _answer_html(call.message, premium, "\n".join(lines))
    await _answer_html(
        call.message,
        premium,
        f"Открыть последнюю заявку <b>#{last['id']}</b>:",
        reply_markup=_pending_kb(int(last["id"]))
    )
    await call.answer()


@router.callback_query(F.data.startswith("admin_sub_approve:"))
async def admin_sub_approve(call: CallbackQuery, db: Database, cfg: Config, premium: PremiumEmoji):
    if not _admin_guard(call, cfg):
        await call.answer("⛔️ Нет доступа", show_alert=True)
        return

    sub_id = int(call.data.split(":", 1)[1])

    conn = db._connect()
    cur = conn.cursor()

    cur.execute("SELECT * FROM task_submissions WHERE id=?", (sub_id,))
    sub = cur.fetchone()
    if not sub or sub["status"] != "pending":
        conn.close()
        await call.answer("❌ Не найдено / уже обработано", show_alert=True)
        return

    cur.execute("SELECT * FROM tasks WHERE id=?", (int(sub["task_id"]),))
    task = cur.fetchone()
    if not task:
        conn.close()
        await call.answer("❌ Task не найден", show_alert=True)
        return

    user_id = int(sub["user_id"])
    task_reward = int(task["reward_digi"])

    cur.execute("UPDATE task_submissions SET status='approved' WHERE id=?", (sub_id,))
    conn.commit()
    conn.close()

    db.add_balance(user_id, task_reward)

    ref_reward = cfg.REF_REWARD_DIGI
    db.process_referral_if_ready(
        tg_id=user_id,
        reward_digi=ref_reward,
        min_earned=cfg.REF_CONDITION_EARN_DIGI,
        min_hours=cfg.REF_CONDITION_HOURS
    )

    try:
        await premium.answer_html(
            await call.bot.send_message(user_id, "…"),  # safety placeholder, will be replaced below
        )
    except Exception:
        pass

    try:
        await call.bot.send_message(
            user_id,
            " "  # placeholder; below we send proper premium text using answer_html on a Message object is not possible here
        )
    except Exception:
        pass

    # ✅ Для bot.send_message нет Message, поэтому отправляем обычным HTML
    # (премиум-emoji в личку можно сделать через bot.send_message с entities,
    # но это отдельная логика; тут НЕ трогаем логику выплат/проверок)
    try:
        await call.bot.send_message(
            user_id,
            "✅ <b>Задание подтверждено!</b>\n\n"
            f"🪙 Начислено: <b>{task_reward:,}</b> DGR",
            parse_mode="HTML"
        )
    except Exception:
        pass

    await _answer_html(
        call.message,
        premium,
        f"✅ Approved submission <b>#{sub_id}</b>\n"
        f"🪙 Начислено пользователю <code>{user_id}</code>: <b>{task_reward:,}</b> DGR",
        reply_markup=_back_kb()
    )
    await call.answer("✅ Approve", show_alert=True)


@router.callback_query(F.data.startswith("admin_sub_deny:"))
async def admin_sub_deny(call: CallbackQuery, db: Database, cfg: Config, premium: PremiumEmoji):
    if not _admin_guard(call, cfg):
        await call.answer("⛔️ Нет доступа", show_alert=True)
        return

    sub_id = int(call.data.split(":", 1)[1])

    conn = db._connect()
    cur = conn.cursor()
    cur.execute("SELECT * FROM task_submissions WHERE id=?", (sub_id,))
    sub = cur.fetchone()
    if not sub or sub["status"] != "pending":
        conn.close()
        await call.answer("❌ Не найдено / уже обработано", show_alert=True)
        return

    user_id = int(sub["user_id"])
    cur.execute("UPDATE task_submissions SET status='denied' WHERE id=?", (sub_id,))
    conn.commit()
    conn.close()

    try:
        await call.bot.send_message(
            user_id,
            "❌ <b>Задание отклонено</b>\n\n"
            "Проверьте выполнение условий и отправьте новую заявку.",
            parse_mode="HTML"
        )
    except Exception:
        pass

    await _answer_html(call.message, premium, f"❌ Denied submission <b>#{sub_id}</b>", reply_markup=_back_kb())
    await call.answer("❌ Deny", show_alert=True)


# ==============================
# MARKET MANUAL SUBMISSIONS
# ==============================
@router.callback_query(F.data == "admin_market_pending")
async def admin_market_pending(call: CallbackQuery, db: Database, cfg: Config, premium: PremiumEmoji):
    if not _admin_guard(call, cfg):
        await call.answer("⛔️ Нет доступа", show_alert=True)
        return

    _ensure_market_manual_table(db)

    conn = db._connect()
    cur = conn.cursor()
    cur.execute("""
        SELECT mms.*, mt.kind, mt.url, mt.price_digi
        FROM market_manual_submissions mms
        JOIN market_tasks mt ON mt.id = mms.task_id
        WHERE mms.status='pending'
        ORDER BY mms.id DESC
        LIMIT 10
    """)
    rows = cur.fetchall()
    conn.close()

    if not rows:
        await _answer_html(call.message, premium, "✅ Нет Market заявок на проверке.", reply_markup=_back_kb())
        await call.answer()
        return

    lines = ["🧩 <b>Market заявки (manual)</b>", ""]
    for r in rows:
        lines.append(
            f"🆔 Submission: <b>{r['id']}</b>\n"
            f"🎯 Task: <b>#{r['task_id']}</b> ({r['kind']})\n"
            f"👤 worker_id: <code>{r['worker_id']}</code>\n"
            f"💰 reward: <b>{int(r['price_digi']):,}</b> DGR\n"
            f"🔗 {r['url']}\n"
        )

    last = rows[0]
    await _answer_html(call.message, premium, "\n".join(lines))
    await _answer_html(
        call.message,
        premium,
        f"Открыть последнюю Market заявку <b>#{last['id']}</b>:",
        reply_markup=_market_pending_kb(int(last["id"]))
    )
    await call.answer()


@router.callback_query(F.data.startswith("admin_market_approve:"))
async def admin_market_approve(call: CallbackQuery, db: Database, cfg: Config, premium: PremiumEmoji):
    if not _admin_guard(call, cfg):
        await call.answer("⛔️ Нет доступа", show_alert=True)
        return

    sub_id = int(call.data.split(":", 1)[1])
    _ensure_market_manual_table(db)

    conn = db._connect()
    cur = conn.cursor()
    cur.execute("SELECT * FROM market_manual_submissions WHERE id=?", (sub_id,))
    sub = cur.fetchone()
    if not sub or sub["status"] != "pending":
        conn.close()
        await call.answer("❌ Не найдено / уже обработано", show_alert=True)
        return

    task_id = int(sub["task_id"])
    worker_id = int(sub["worker_id"])

    cur.execute("UPDATE market_manual_submissions SET status='approved' WHERE id=?", (sub_id,))
    conn.commit()
    conn.close()

    ok, msg = db.market_complete_task_and_pay(task_id=task_id, worker_id=worker_id)
    if ok:
        ref_reward = cfg.REF_REWARD_DIGI
        db.process_referral_if_ready(
            tg_id=worker_id,
            reward_digi=ref_reward,
            min_earned=cfg.REF_CONDITION_EARN_DIGI,
            min_hours=cfg.REF_CONDITION_HOURS
        )

        try:
            await call.bot.send_message(worker_id, f"✅ <b>Заявка подтверждена!</b>\n\n{msg}", parse_mode="HTML")
        except Exception:
            pass

        await _answer_html(call.message, premium, f"✅ Market approve <b>#{sub_id}</b>\n{msg}", reply_markup=_back_kb())
        await call.answer("✅ Approve", show_alert=True)
    else:
        conn = db._connect()
        cur = conn.cursor()
        cur.execute("UPDATE market_manual_submissions SET status='pending' WHERE id=?", (sub_id,))
        conn.commit()
        conn.close()

        await call.answer(msg, show_alert=True)


@router.callback_query(F.data.startswith("admin_market_deny:"))
async def admin_market_deny(call: CallbackQuery, db: Database, cfg: Config, premium: PremiumEmoji):
    if not _admin_guard(call, cfg):
        await call.answer("⛔️ Нет доступа", show_alert=True)
        return

    sub_id = int(call.data.split(":", 1)[1])
    _ensure_market_manual_table(db)

    conn = db._connect()
    cur = conn.cursor()
    cur.execute("SELECT * FROM market_manual_submissions WHERE id=?", (sub_id,))
    sub = cur.fetchone()
    if not sub or sub["status"] != "pending":
        conn.close()
        await call.answer("❌ Не найдено / уже обработано", show_alert=True)
        return

    worker_id = int(sub["worker_id"])
    cur.execute("UPDATE market_manual_submissions SET status='denied' WHERE id=?", (sub_id,))
    conn.commit()
    conn.close()

    try:
        await call.bot.send_message(
            worker_id,
            "❌ <b>Market-заявка отклонена</b>\n\n"
            "Попробуйте выполнить задание корректно и отправьте новый скрин.",
            parse_mode="HTML"
        )
    except Exception:
        pass

    await _answer_html(call.message, premium, f"❌ Market deny <b>#{sub_id}</b>", reply_markup=_back_kb())
    await call.answer("❌ Deny", show_alert=True)


# ==============================
# ADS MENU
# ==============================
@router.callback_query(F.data == "admin_ads")
async def admin_ads(call: CallbackQuery, cfg: Config, premium: PremiumEmoji):
    if not _admin_guard(call, cfg):
        await call.answer("⛔️ Нет доступа", show_alert=True)
        return
    await _answer_html(call.message, premium, "📢 <b>Объявления / Реклама</b>\n\nВыберите:", reply_markup=admin_ads_inline())
    await call.answer()


@router.callback_query(F.data == "admin_ads_list")
async def admin_ads_list(call: CallbackQuery, db: Database, cfg: Config, premium: PremiumEmoji):
    if not _admin_guard(call, cfg):
        await call.answer("⛔️ Нет доступа", show_alert=True)
        return

    await _admin_show_ads_page(call, db, page=0, premium=premium)
    await call.answer()


@router.callback_query(F.data.startswith("admin_ads_page:"))
async def admin_ads_page(call: CallbackQuery, db: Database, cfg: Config, premium: PremiumEmoji):
    if not _admin_guard(call, cfg):
        await call.answer("⛔️ Нет доступа", show_alert=True)
        return

    page = int(call.data.split(":", 1)[1])
    await _admin_show_ads_page(call, db, page=page, premium=premium)
    await call.answer()


@router.callback_query(F.data == "admin_ads_noop")
async def admin_ads_noop(call: CallbackQuery, cfg: Config):
    if not _admin_guard(call, cfg):
        await call.answer("⛔️ Нет доступа", show_alert=True)
        return
    await call.answer()


@router.callback_query(F.data == "admin_ads_delete")
async def admin_ads_delete_start(call: CallbackQuery, state: FSMContext, cfg: Config, premium: PremiumEmoji):
    if not _admin_guard(call, cfg):
        await call.answer("⛔️ Нет доступа", show_alert=True)
        return

    await state.clear()
    await state.set_state(AdminAdsDeleteStates.waiting_ad_id)
    await _answer_html(
        call.message,
        premium,
        "🗑 <b>Удаление рекламы</b>\n\nВведите <b>ID</b> рекламы (например: 12):",
        reply_markup=_back_kb()
    )
    await call.answer()


@router.message(AdminAdsDeleteStates.waiting_ad_id)
async def admin_ads_delete(message: Message, state: FSMContext, db: Database, cfg: Config, premium: PremiumEmoji):
    if not _is_admin(message.from_user.id, cfg):
        return

    raw = (message.text or "").strip()
    if not raw.isdigit():
        await _answer_html(message, premium, "❌ Введите ID цифрами.")
        return

    ad_id = int(raw)
    conn = db._connect()
    cur = conn.cursor()
    cur.execute("DELETE FROM ads WHERE id=?", (ad_id,))
    conn.commit()
    conn.close()

    await state.clear()
    await _answer_html(message, premium, "✅ Удалено (если ID существовал).", reply_markup=admin_panel_inline())


# ==============================
# GIVE DIGI
# ==============================
@router.callback_query(F.data == "admin_give_digi")
async def admin_give_digi_start(call: CallbackQuery, state: FSMContext, cfg: Config, premium: PremiumEmoji):
    if not _admin_guard(call, cfg):
        await call.answer("⛔️ Нет доступа", show_alert=True)
        return

    await state.clear()
    await state.set_state(AdminGiveDigiStates.waiting_user)

    await _answer_html(
        call.message,
        premium,
        "➕ <b>Начислить DGR</b>\n\n"
        "Введи <b>TG ID</b> пользователя (цифры) или напиши <b>me</b> чтобы начислить себе:"
    )
    await call.answer()

@router.callback_query(F.data == "admin_give_usdt")
async def admin_give_usdt_start(call: CallbackQuery, state: FSMContext, cfg: Config, premium: PremiumEmoji):
    if not _admin_guard(call, cfg):
        await call.answer("⛔️ Нет доступа", show_alert=True)
        return

    await state.clear()
    await state.set_state(AdminGiveUsdtStates.waiting_user)

    await _answer_html(
        call.message,
        premium,
        "💵 <b>Начислить USDT</b>\n\n"
        "Введи <b>TG ID</b> пользователя (цифры) или напиши <b>me</b> чтобы начислить себе:"
    )
    await call.answer()


@router.message(AdminGiveUsdtStates.waiting_user)
async def admin_give_usdt_user(message: Message, state: FSMContext, db: Database, cfg: Config, premium: PremiumEmoji):
    if not _is_admin(message.from_user.id, cfg):
        return

    raw = (message.text or "").strip().lower()

    if raw == "me":
        target_id = message.from_user.id
    else:
        if not raw.isdigit():
            await _answer_html(message, premium, "❌ Введи TG ID цифрами или <b>me</b>.")
            return
        target_id = int(raw)

    u = db.get_user(target_id)
    if not u:
        db.create_user(tg_id=target_id, username="NoUsername", referrer_id=None)

    await state.update_data(target_id=target_id)
    await state.set_state(AdminGiveUsdtStates.waiting_amount)

    await _answer_html(
        message,
        premium,
        f"✅ Кому: <code>{target_id}</code>\n\n"
        "Теперь введи сумму в <b>USDT</b> (например: <b>10</b> или <b>2.5</b>)"
    )

@router.message(AdminGiveUsdtStates.waiting_amount)
async def admin_give_usdt_amount(message: Message, state: FSMContext, db: Database, cfg: Config, premium: PremiumEmoji):
    if not _is_admin(message.from_user.id, cfg):
        return

    amount = _parse_usdt_amount(message.text)
    if amount is None or amount <= 0:
        await _answer_html(message, premium, "❌ Введи корректную сумму. Пример: <b>10</b> или <b>2.5</b>")
        return

    if amount > 1_000_000:
        await _answer_html(message, premium, "❌ Слишком большая сумма.")
        return

    data = await state.get_data()
    target_id = int(data["target_id"])

    # ✅ начисляем в основной usdt_balance
    db.add_usdt(target_id, float(amount))

    await state.clear()

    await _answer_html(
        message,
        premium,
        "✅ <b>Начислено USDT!</b>\n\n"
        f"👤 Кому: <code>{target_id}</code>\n"
        f"💵 Сумма: <b>{amount:.2f} USDT</b>",
        reply_markup=admin_panel_inline()
    )

    if target_id != message.from_user.id:
        try:
            await message.bot.send_message(
                target_id,
                "💵 <b>Вам начислено USDT</b>\n\n"
                f"✅ +<b>{amount:.2f} USDT</b>",
                parse_mode="HTML"
            )
        except Exception:
            pass


@router.message(AdminGiveDigiStates.waiting_user)
async def admin_give_digi_user(message: Message, state: FSMContext, db: Database, cfg: Config, premium: PremiumEmoji):
    if not _is_admin(message.from_user.id, cfg):
        return

    raw = (message.text or "").strip().lower()

    if raw == "me":
        target_id = message.from_user.id
    else:
        if not raw.isdigit():
            await _answer_html(message, premium, "❌ Введи TG ID цифрами или <b>me</b>.")
            return
        target_id = int(raw)

    u = db.get_user(target_id)
    if not u:
        db.create_user(tg_id=target_id, username="NoUsername", referrer_id=None)

    await state.update_data(target_id=target_id)
    await state.set_state(AdminGiveDigiStates.waiting_amount)

    await _answer_html(
        message,
        premium,
        f"✅ Кому: <code>{target_id}</code>\n\n"
        "Теперь введи сумму в <b>DGR</b> (целое число), например: <b>5000</b>"
    )


@router.message(AdminGiveDigiStates.waiting_amount)
async def admin_give_digi_amount(message: Message, state: FSMContext, db: Database, cfg: Config, premium: PremiumEmoji):
    if not _is_admin(message.from_user.id, cfg):
        return

    raw = (message.text or "").strip().replace(" ", "")
    if not raw.isdigit():
        await _answer_html(message, premium, "❌ Введи число. Например: <b>5000</b>")
        return

    amount = int(raw)
    if amount <= 0 or amount > 10_000_000:
        await _answer_html(message, premium, "❌ Неверная сумма (1..10,000,000).")
        return

    data = await state.get_data()
    target_id = int(data["target_id"])

    db.add_balance(target_id, amount)
    await state.clear()

    await _answer_html(
        message,
        premium,
        "✅ <b>Начислено!</b>\n\n"
        f"👤 Кому: <code>{target_id}</code>\n"
        f"💎 Сумма: <b>{amount:,}</b> DGR",
        reply_markup=admin_panel_inline()
    )

    if target_id != message.from_user.id:
        try:
            await message.bot.send_message(
                target_id,
                "🎁 <b>Вам начислено DGR</b>\n\n"
                f"🪙 +<b>{amount:,}</b> DGR",
                parse_mode="HTML"
            )
        except Exception:
            pass


# ==============================
# WITHDRAW ADMIN
# ==============================
@router.callback_query(F.data == "admin_withdrawals")
async def admin_withdrawals(call: CallbackQuery, db: Database, cfg: Config, premium: PremiumEmoji):
    if not _admin_guard(call, cfg):
        await call.answer("⛔️ Нет доступа", show_alert=True)
        return
    await _admin_show_withdraw_page(call, db, page=0, premium=premium)
    await call.answer()


@router.callback_query(F.data.startswith("admin_wd_page:"))
async def admin_wd_page(call: CallbackQuery, db: Database, cfg: Config, premium: PremiumEmoji):
    if not _admin_guard(call, cfg):
        await call.answer("⛔️ Нет доступа", show_alert=True)
        return
    page = int(call.data.split(":", 1)[1])
    await _admin_show_withdraw_page(call, db, page=page, premium=premium)
    await call.answer()


@router.callback_query(F.data.startswith("admin_wd_process:"))
async def admin_wd_process(call: CallbackQuery, db: Database, cfg: Config, premium: PremiumEmoji, cryptobot: CryptoBotAPI):
    if not _admin_guard(call, cfg):
        await call.answer("⛔️ Нет доступа", show_alert=True)
        return

    req_id = int(call.data.split(":", 1)[1])
    _ensure_withdraw_table(db)

    conn = db._connect()
    cur = conn.cursor()

    try:
        cur.execute("BEGIN IMMEDIATE")

        cur.execute("SELECT * FROM withdraw_requests WHERE id=?", (req_id,))
        r = cur.fetchone()

        if not r or r["status"] != "pending":
            conn.rollback()
            await call.answer("❌ Не найдено / уже обработано", show_alert=True)
            return

        user_id = int(r["user_id"])
        amount = float(r["amount_usdt"])

        # временный статус
        cur.execute("""
            UPDATE withdraw_requests
            SET status='processing'
            WHERE id=?
        """, (req_id,))
        conn.commit()

    except Exception:
        conn.rollback()
        await call.answer("Ошибка БД", show_alert=True)
        return
    finally:
        conn.close()

    # 🔥 создаём чек через CryptoBot
    try:
        check = await cryptobot.create_check(asset="USDT", amount=amount)
        check_url = check["bot_check_url"]
        check_id = check["check_id"]
    except Exception as e:
        # возвращаем статус обратно
        conn = db._connect()
        cur = conn.cursor()
        cur.execute("""
            UPDATE withdraw_requests
            SET status='pending'
            WHERE id=?
        """, (req_id,))
        conn.commit()
        conn.close()

        await call.answer(f"CryptoBot error: {e}", show_alert=True)
        return

    # сохраняем чек
    conn = db._connect()
    cur = conn.cursor()
    cur.execute("""
        UPDATE withdraw_requests
        SET status='processed',
            processed_at=datetime('now'),
            processed_by=?,
            check_id=?,
            check_url=?
        WHERE id=?
    """, (int(call.from_user.id), check_id, check_url, req_id))
    conn.commit()
    conn.close()

    # отправляем пользователю чек
    try:
        await call.bot.send_message(
            user_id,
            f"✅ <b>Ваша выплата готова!</b>\n\n"
            f"💵 Сумма: <b>{amount:.2f} USDT</b>\n\n"
            "Нажмите кнопку ниже чтобы получить чек:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text="💸 Получить USDT",
                    url=check_url
                )]
            ]),
            parse_mode="HTML"
        )
    except Exception:
        pass

    await call.answer("✅ Чек создан и отправлен", show_alert=True)
    await _admin_show_withdraw_page(call, db, page=0, premium=premium)

@router.callback_query(F.data.startswith("admin_wd_deny:"))
async def admin_wd_deny(call: CallbackQuery, db: Database, cfg: Config, premium: PremiumEmoji):
    if not _admin_guard(call, cfg):
        await call.answer("⛔️ Нет доступа", show_alert=True)
        return

    req_id = int(call.data.split(":", 1)[1])
    _ensure_withdraw_table(db)

    user_id = None
    amount = 0.0
    src = "usdt"

    conn = db._connect()
    cur = conn.cursor()
    try:
        cur.execute("BEGIN IMMEDIATE")

        # ✅ Берём заявку только если она pending (защита от повторной обработки)
        cur.execute("""
            SELECT id, user_id, amount_usdt, source, status
            FROM withdraw_requests
            WHERE id=?
        """, (req_id,))
        r = cur.fetchone()
        if not r or r["status"] != "pending":
            conn.rollback()
            await call.answer("❌ Не найдено / уже обработано", show_alert=True)
            return

        user_id = int(r["user_id"])
        amount = float(r["amount_usdt"] or 0.0)

        # source может отсутствовать в старой схеме — тогда считаем usdt
        src = str((r["source"] if "source" in r.keys() else "usdt") or "usdt")

        # ✅ 1) Сначала помечаем заявку как denied (и только если она pending)
        cur.execute("""
            UPDATE withdraw_requests
            SET status='denied',
                processed_at=datetime('now'),
                processed_by=?
            WHERE id=? AND status='pending'
        """, (int(call.from_user.id), req_id))

        if cur.rowcount == 0:
            conn.rollback()
            await call.answer("❌ Уже обработано", show_alert=True)
            return

        # ✅ 2) Refund назад ТОЛЬКО в основной usdt_balance
        # (теперь ref/win балансов нет; все списания были из usdt_balance)
        if amount > 0:
            cur.execute("""
                UPDATE users
                SET usdt_balance = usdt_balance + ?
                WHERE tg_id=?
            """, (amount, user_id))

        # ✅ 3) откатываем лимит withdrawn_today_usdt (как было у тебя)
        cur.execute("SELECT date('now') AS d")
        today = cur.fetchone()["d"]

        cur.execute("SELECT withdrawn_date, withdrawn_today_usdt FROM users WHERE tg_id=?", (user_id,))
        u = cur.fetchone()
        if u and u["withdrawn_date"] == today:
            cur.execute("""
                UPDATE users
                SET withdrawn_today_usdt = CASE
                    WHEN withdrawn_today_usdt >= ? THEN withdrawn_today_usdt - ?
                    ELSE 0
                END
                WHERE tg_id=?
            """, (amount, amount, user_id))

        conn.commit()

    except Exception:
        conn.rollback()
        await call.answer("Ошибка", show_alert=True)
        return
    finally:
        conn.close()

    # ✅ теперь всегда основной баланс
    try:
        await call.bot.send_message(
            user_id,
            "❌ <b>Заявка на вывод отклонена</b>\n\n"
            f"🆔 ID: <b>{req_id}</b>\n"
            "👨‍💻 Администратор: @illy228\n"
            f"💵 Сумма возвращена на <b>основной USDT баланс</b>: <b>{amount:.2f} USDT</b>",
            parse_mode="HTML"
        )
    except Exception:
        pass

    await call.answer("❌ Denied + Refund", show_alert=True)
    await _admin_show_withdraw_page(call, db, page=0, premium=premium)

