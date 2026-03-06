# handlers/mining.py
from __future__ import annotations

import math
import random
from datetime import datetime, timezone
from typing import Optional, List

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

from database import Database
from services.premium_emoji import PremiumEmoji

router = Router()

# =========================
# Settings (tuneable)
# =========================
MIN_UPGRADE_DIGI = 100

# доход: DIGI/час = power * (hp/100) * RATE_K
# ✅ старт 1 DIGI/час при power=1 и HP=100
RATE_K = 15.0

# буст (x2) + бонус атак по пакетам
BOOST_PACKS = [
    # (id, title, price_usdt, duration_sec, bonus_attacks)
    ("b1", "⚡ 1 час", 2.0, 1 * 3600, 0),
    ("b2", "⚡ 3 часа + 1 атака", 4.0, 3 * 3600, 1),
    ("b3", "⚡ 12 часов + 2 атаки", 6.0, 12 * 3600, 2),
    ("b4", "⚡ 24 часа + 5 атак", 10.0, 24 * 3600, 5),
    ("b5", "⚡ 30 дней + 10 атак", 15.0, 30 * 24 * 3600, 10),
]

# ✅ покупка HP за USDT (без изменения текста меню "Бусты", просто доп. кнопки)
HP_PACKS = [
    # (id, title, price_usdt, add_hp)
    ("h1", "❤️ +20 HP", 2.0, 20),
    ("h2", "❤️ +50 HP", 4.0, 50),
    ("h3", "❤️ Полный ремонт до 100%", 6.0, 9999),
]

SHIELD_PACKS = [
    ("s1", "🛡 6 часов", 3.0, 6 * 3600),
    ("s2", "🛡 12 часов", 5.0, 12 * 3600),
    ("s3", "🛡 24 часа", 8.0, 24 * 3600),
    ("s4", "🛡 30 дней", 12.0, 30 * 24 * 3600),
]

# лимит времени начисления за один расчёт (анти-абуз если не заходил год)
MAX_ACCRUAL_SECONDS = 7 * 24 * 3600

# атака: % от stored, но не больше, чем cap по силе атакующего
STEAL_PCT = 0.60
STEAL_CAP_PER_POWER = 1000000.0  # max_steal = power * this

POWER_STEAL_PCT = 0.02   # 2% мощности цели
POWER_STEAL_CAP = 0.50   # но не больше 0.25 за атаку

HP_STEAL_PCT = 0.06      # 6% HP цели
HP_STEAL_CAP = 15         # но не больше 8 HP за атаку


# =========================
# FSM
# =========================
class MiningStates(StatesGroup):
    upgrade_amount = State()


# =========================
# Small helpers
# =========================
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


def _utc_now_ts() -> int:
    return int(datetime.now(timezone.utc).timestamp())


def _today_utc() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def _fmt2(x: float) -> str:
    return f"{x:.2f}"


def _fmt_until(ts: int) -> str:
    if not ts:
        return "—"
    dt = datetime.fromtimestamp(ts, tz=timezone.utc)
    return dt.strftime("%d.%m %H:%M UTC")


def _mining_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📥 Собрать", callback_data="mining_collect")],
        [InlineKeyboardButton(text="🔝 Прокачать", callback_data="mining_upgrade")],
        [InlineKeyboardButton(text="⚡ Бусты", callback_data="mining_boosts")],
        [InlineKeyboardButton(text="🛡 Щит", callback_data="mining_shield")],
        [InlineKeyboardButton(text="⚔️ Атаковать", callback_data="mining_attack_open:0")],
        [InlineKeyboardButton(text="🔄 Конвертация", callback_data="convert_menu")],  # 👈 добавили
        [InlineKeyboardButton(text="🏠 В меню", callback_data="go_menu")],
    ])


def _back_to_mining_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="mining_open")],
    ])


def _boosts_kb() -> InlineKeyboardMarkup:
    rows = []
    for bid, title, price, _, _ in BOOST_PACKS:
        rows.append([InlineKeyboardButton(text=f"{title} — {price:g} USDT", callback_data=f"mining_buy_boost:{bid}")])

    # ✅ доп. покупки HP (без изменения текста экрана)
    for hid, title, price, _ in HP_PACKS:
        rows.append([InlineKeyboardButton(text=f"{title} — {price:g} USDT", callback_data=f"mining_buy_hp:{hid}")])

    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="mining_open")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _shield_kb() -> InlineKeyboardMarkup:
    rows = []
    for sid, title, price, _ in SHIELD_PACKS:
        rows.append([InlineKeyboardButton(text=f"{title} — {price:g} USDT", callback_data=f"mining_buy_shield:{sid}")])
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="mining_open")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _attack_kb(idx: int, total: int, can_attack: bool, target_id: Optional[int]) -> InlineKeyboardMarkup:
    nav = []
    if total > 1:
        nav.append(InlineKeyboardButton(text="◀️", callback_data=f"mining_attack_open:{max(0, idx-1)}"))
        nav.append(InlineKeyboardButton(text=f"{idx+1}/{total}", callback_data="noop"))
        nav.append(InlineKeyboardButton(text="▶️", callback_data=f"mining_attack_open:{min(total-1, idx+1)}"))
    else:
        nav.append(InlineKeyboardButton(text="1/1", callback_data="noop"))

    rows = [nav]
    if can_attack and target_id:
        rows.append([InlineKeyboardButton(text="⚔️ Атаковать", callback_data=f"mining_attack_do:{target_id}:{idx}")])
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="mining_open")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


# =========================
# Core logic
# =========================
def _reset_daily_attacks_if_needed(conn, tg_id: int) -> None:
    today = _today_utc()
    cur = conn.cursor()
    cur.execute("SELECT miner_attacks_day FROM users WHERE tg_id=?", (tg_id,))
    row = cur.fetchone()
    last_day = (row["miner_attacks_day"] if row and "miner_attacks_day" in row.keys() else "") or ""
    if last_day != today:
        cur.execute("""
            UPDATE users
            SET miner_attacks_day=?,
                miner_attacks_used_today=0,
                miner_attacks_bonus_today=0
            WHERE tg_id=?
        """, (today, tg_id))


def _apply_mining(conn, tg_id: int) -> float:
    """
    Начисляет добычу в miner_stored по времени.
    Возвращает earned (сколько добавили сейчас) для красивого отображения.
    """
    now = _utc_now_ts()
    cur = conn.cursor()
    cur.execute("""
        SELECT miner_power, miner_hp, miner_last_ts, miner_stored, miner_boost_until
        FROM users WHERE tg_id=?
    """, (tg_id,))
    u = cur.fetchone()
    if not u:
        return 0.0

    power = float((u["miner_power"] if "miner_power" in u.keys() else 1.0) or 1.0)
    hp = int((u["miner_hp"] if "miner_hp" in u.keys() else 100) or 100)
    last_ts = int((u["miner_last_ts"] if "miner_last_ts" in u.keys() else 0) or 0)
    stored = float((u["miner_stored"] if "miner_stored" in u.keys() else 0.0) or 0.0)
    boost_until = int((u["miner_boost_until"] if "miner_boost_until" in u.keys() else 0) or 0)

    if last_ts <= 0:
        cur.execute("UPDATE users SET miner_last_ts=? WHERE tg_id=?", (now, tg_id))
        return 0.0

    dt = max(0, now - last_ts)
    dt = min(dt, MAX_ACCRUAL_SECONDS)
    if dt <= 0:
        return 0.0

    # ✅ HP влияет на эффективность. Если HP=0 — майнинг стоит.
    if hp <= 0:
        cur.execute("UPDATE users SET miner_last_ts=? WHERE tg_id=?", (now, tg_id))
        return 0.0

    eff = max(0.0, min(1.0, hp / 100.0))
    rate = power * eff * RATE_K
    if boost_until > now:
        rate *= 2.0

    earned = rate * (dt / 3600.0)
    earned = float(f"{earned:.4f}")  # аккуратно

    cur.execute("""
        UPDATE users
        SET miner_stored=?,
            miner_last_ts=?
        WHERE tg_id=?
    """, (stored + earned, now, tg_id))
    return earned


def _mining_text(user_row, earned_now: float = 0.0) -> str:
    now = _utc_now_ts()

    username = (rget(user_row, "username", None) or "NoUsername")
    if username and not str(username).startswith("@"):
        username = "@" + str(username)

    power = float(rget(user_row, "miner_power", 1.0) or 1.0)
    hp = int(rget(user_row, "miner_hp", 100) or 100)
    stored = float(rget(user_row, "miner_stored", 0.0) or 0.0)

    digi_balance = int(rget(user_row, "balance_digi", 0) or 0)
    usdt_balance = float(rget(user_row, "usdt_balance", 0.0) or 0.0)

    boost_until = int(rget(user_row, "miner_boost_until", 0) or 0)
    shield_until = int(rget(user_row, "miner_shield_until", 0) or 0)

    eff = max(0.0, min(1.0, hp / 100.0))
    rate = power * eff * RATE_K
    if boost_until > now:
        rate *= 2.0

    boost_str = f"активен до <b>{_fmt_until(boost_until)}</b>" if boost_until > now else "нет"
    shield_str = f"активен до <b>{_fmt_until(shield_until)}</b>" if shield_until > now else "нет"

    plus_line = ""
    if earned_now and earned_now > 0:
        plus_line = f""

    return (
        f"⛏ <b>Майнинг DGR</b>\n"
        f"👤 <b>Пользователь:</b>{username}\n\n"
        f"⚡ <b>Мощность:</b> {_fmt2(power)}\n"
        f"❤️ <b>HP:</b> {hp}%\n\n"
        f"⏱ <b>Доход/час:</b> {_fmt2(rate)} DGR/час\n"
        f"📦 <b>Намайнено:</b> {_fmt2(stored)} DGR\n\n"
        f"🪙 <b>Баланс DGR:</b> {digi_balance}\n"
        f"💵 <b>Баланс USDT:</b> {_fmt2(usdt_balance)}\n\n"
        f"⚡ <b>Буст:</b> {boost_str}\n"
        f"🛡 <b>Щит:</b> {shield_str}"
        f"{plus_line}"
    )


def _get_attack_targets(conn, attacker_id: int) -> List:
    cur = conn.cursor()
    now = _utc_now_ts()
    cur.execute("""
        SELECT tg_id, username, miner_power, miner_hp, miner_stored, miner_shield_until
        FROM users
        WHERE tg_id != ?
        ORDER BY miner_stored DESC
        LIMIT 50
    """, (attacker_id,))
    rows = cur.fetchall() or []
    out = []
    for r in rows:
        shield_until = int((r["miner_shield_until"] if "miner_shield_until" in r.keys() else 0) or 0)
        stored = float((r["miner_stored"] if "miner_stored" in r.keys() else 0.0) or 0.0)
        if shield_until > now:
            continue
        if stored <= 0.01:
            continue
        out.append(r)
    return out


# =========================
# Handlers
# =========================
@router.message(F.text == "⛏ Майнинг")
async def mining_entry(message: Message, db: Database, premium: PremiumEmoji):
    tg_id = message.from_user.id
    username = message.from_user.username or "NoUsername"

    user = db.get_user(tg_id)
    if not user:
        db.create_user(tg_id=tg_id, username=username, referrer_id=None, first_name=message.from_user.first_name or "")
        user = db.get_user(tg_id)

    conn = db._connect()
    cur = conn.cursor()
    try:
        cur.execute("BEGIN IMMEDIATE")
        _reset_daily_attacks_if_needed(conn, tg_id)
        earned = _apply_mining(conn, tg_id)
        cur.execute("SELECT * FROM users WHERE tg_id=?", (tg_id,))
        user2 = cur.fetchone()
        conn.commit()
    except Exception:
        conn.rollback()
        user2 = user
        earned = 0.0
    finally:
        conn.close()

    await premium.answer_html(message, _mining_text(user2, earned_now=earned), reply_markup=_mining_kb())


@router.callback_query(F.data == "mining_open")
async def mining_open(call: CallbackQuery, db: Database, premium: PremiumEmoji):
    tg_id = call.from_user.id
    conn = db._connect()
    cur = conn.cursor()
    try:
        cur.execute("BEGIN IMMEDIATE")
        _reset_daily_attacks_if_needed(conn, tg_id)
        earned = _apply_mining(conn, tg_id)
        cur.execute("SELECT * FROM users WHERE tg_id=?", (tg_id,))
        u = cur.fetchone()
        conn.commit()
    except Exception:
        conn.rollback()
        u = db.get_user(tg_id)
        earned = 0.0
    finally:
        conn.close()

    await premium.edit_html(call.message, _mining_text(u, earned_now=earned), reply_markup=_mining_kb())
    await call.answer()


@router.callback_query(F.data == "mining_collect")
async def mining_collect(call: CallbackQuery, db: Database, premium: PremiumEmoji):
    tg_id = call.from_user.id
    conn = db._connect()
    cur = conn.cursor()
    collected = 0.0
    try:
        cur.execute("BEGIN IMMEDIATE")
        _reset_daily_attacks_if_needed(conn, tg_id)
        _apply_mining(conn, tg_id)

        cur.execute("SELECT miner_stored, balance_digi FROM users WHERE tg_id=?", (tg_id,))
        r = cur.fetchone()
        stored = float((r["miner_stored"] if r else 0.0) or 0.0)
        bal = int((r["balance_digi"] if r else 0) or 0)

        if stored > 0:
            collected = stored
            add_int = int(round(stored))

            cur.execute("""
                UPDATE users
                SET balance_digi=?,
                    miner_stored=0
                WHERE tg_id=?
            """, (bal + add_int, tg_id))

        cur.execute("SELECT * FROM users WHERE tg_id=?", (tg_id,))
        u = cur.fetchone()
        conn.commit()
    except Exception:
        conn.rollback()
        u = db.get_user(tg_id)
    finally:
        conn.close()

    await call.answer(("✅ Собрано: " + _fmt2(collected) + " DIGI") if collected > 0 else "ℹ️ Нечего собирать")
    await premium.edit_html(call.message, _mining_text(u, earned_now=0.0), reply_markup=_mining_kb())


@router.callback_query(F.data == "mining_upgrade")
async def mining_upgrade(call: CallbackQuery, state: FSMContext, premium: PremiumEmoji):
    await state.set_state(MiningStates.upgrade_amount)
    text = (
        "🔝 <b>Прокачка майнера</b>\n\n"
        f"Введи сумму в <b>DGR</b> (минимум {MIN_UPGRADE_DIGI}).\n"
        "Чем больше вложишь — тем сильнее майнер.\n\n"
        "<b>Отправь число сообщением</b> 👇"
    )
    await premium.edit_html(call.message, text, reply_markup=_back_to_mining_kb())
    await call.answer()


@router.message(MiningStates.upgrade_amount)
async def mining_upgrade_amount(message: Message, state: FSMContext, db: Database, premium: PremiumEmoji):
    tg_id = message.from_user.id
    raw = (message.text or "").strip().replace(" ", "")
    try:
        amount = int(raw)
    except Exception:
        await premium.answer_html(message, "❌ Введи число (например 500).")
        return

    if amount < MIN_UPGRADE_DIGI:
        await premium.answer_html(message, f"❌ Минимум {MIN_UPGRADE_DIGI} DGR.")
        return

    conn = db._connect()
    cur = conn.cursor()
    power_add = 0.0
    try:
        cur.execute("BEGIN IMMEDIATE")
        _reset_daily_attacks_if_needed(conn, tg_id)
        _apply_mining(conn, tg_id)

        cur.execute("SELECT balance_digi, miner_power FROM users WHERE tg_id=?", (tg_id,))
        r = cur.fetchone()
        bal = int((r["balance_digi"] if r else 0) or 0)
        power = float((r["miner_power"] if r else 1.0) or 1.0)

        if bal < amount:
            conn.rollback()
            await premium.answer_html(message, "❌ Недостаточно DGR на балансе.")
            return

        power_add = round(math.sqrt(amount) / 100.0, 4)
        new_power = round(power + power_add, 4)

        cur.execute("""
            UPDATE users
            SET balance_digi=?,
                miner_power=?,
                total_spent_digi=COALESCE(total_spent_digi,0)+?
            WHERE tg_id=?
        """, (bal - amount, new_power, amount, tg_id))

        conn.commit()
    except Exception:
        conn.rollback()
        await premium.answer_html(message, "❌ Ошибка прокачки. Попробуй ещё раз.")
        return
    finally:
        conn.close()

    await state.clear()

    await premium.answer_html(
        message,
        f"✅ <b>Прокачка успешна!</b>\n➕ Мощность: +{_fmt2(power_add)}\n\nОткрой «⛏ Майнинг» ещё раз или нажми кнопку ниже.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⛏ Открыть майнинг", callback_data="mining_open")]])
    )


@router.callback_query(F.data == "mining_boosts")
async def mining_boosts(call: CallbackQuery, premium: PremiumEmoji):
    text = (
        "⚡ <b>Бусты</b>\n\n"
        "<b>Буст увеличивает доход (x2) и может дать дополнительные атаки на сегодня.</b>\n\n"
        "<b>Выбери пакет</b> 👇"
    )
    await premium.edit_html(call.message, text, reply_markup=_boosts_kb())
    await call.answer()


@router.callback_query(F.data.startswith("mining_buy_boost:"))
async def mining_buy_boost(call: CallbackQuery, db: Database, premium: PremiumEmoji):
    tg_id = call.from_user.id
    bid = call.data.split(":", 1)[1]

    pack = next((p for p in BOOST_PACKS if p[0] == bid), None)
    if not pack:
        await call.answer("Пакет не найден", show_alert=True)
        return

    _, title, price, dur, bonus_attacks = pack

    conn = db._connect()
    cur = conn.cursor()
    try:
        cur.execute("BEGIN IMMEDIATE")
        _reset_daily_attacks_if_needed(conn, tg_id)
        _apply_mining(conn, tg_id)

        cur.execute("SELECT usdt_balance, miner_boost_until, miner_attacks_bonus_today FROM users WHERE tg_id=?", (tg_id,))
        r = cur.fetchone()
        usdt = float((r["usdt_balance"] if r else 0.0) or 0.0)
        boost_until = int((r["miner_boost_until"] if r else 0) or 0)
        bonus_today = int((r["miner_attacks_bonus_today"] if r else 0) or 0)

        if usdt + 1e-9 < float(price):
            conn.rollback()
            await call.answer("❌ Недостаточно USDT", show_alert=True)
            return

        now = _utc_now_ts()
        base = boost_until if boost_until > now else now
        new_boost_until = base + int(dur)

        cur.execute("""
            UPDATE users
            SET usdt_balance=?,
                miner_boost_until=?,
                miner_attacks_bonus_today=?
            WHERE tg_id=?
        """, (usdt - float(price), new_boost_until, bonus_today + int(bonus_attacks), tg_id))

        conn.commit()
    except Exception:
        conn.rollback()
        await call.answer("❌ Ошибка покупки", show_alert=True)
        return
    finally:
        conn.close()

    await call.answer(f"✅ Куплено: {title}")
    await mining_open(call, db, premium)


@router.callback_query(F.data.startswith("mining_buy_hp:"))
async def mining_buy_hp(call: CallbackQuery, db: Database, premium: PremiumEmoji):
    tg_id = call.from_user.id
    hid = call.data.split(":", 1)[1]
    pack = next((p for p in HP_PACKS if p[0] == hid), None)
    if not pack:
        await call.answer("Пакет не найден", show_alert=True)
        return

    _, title, price, add_hp = pack

    conn = db._connect()
    cur = conn.cursor()
    try:
        cur.execute("BEGIN IMMEDIATE")
        _reset_daily_attacks_if_needed(conn, tg_id)
        _apply_mining(conn, tg_id)

        cur.execute("SELECT usdt_balance, miner_hp FROM users WHERE tg_id=?", (tg_id,))
        r = cur.fetchone()
        usdt = float((r["usdt_balance"] if r else 0.0) or 0.0)
        hp = int((r["miner_hp"] if r else 100) or 100)

        if usdt + 1e-9 < float(price):
            conn.rollback()
            await call.answer("❌ Недостаточно USDT", show_alert=True)
            return

        if add_hp >= 9999:
            new_hp = 100
        else:
            new_hp = min(100, hp + int(add_hp))

        cur.execute("""
            UPDATE users
            SET usdt_balance=?,
                miner_hp=?
            WHERE tg_id=?
        """, (usdt - float(price), new_hp, tg_id))

        conn.commit()
    except Exception:
        conn.rollback()
        await call.answer("❌ Ошибка покупки", show_alert=True)
        return
    finally:
        conn.close()

    await call.answer(f"✅ Куплено: {title}")
    await mining_open(call, db, premium)


@router.callback_query(F.data == "mining_shield")
async def mining_shield(call: CallbackQuery, premium: PremiumEmoji):
    text = (
        "🛡 <b>Щит</b>\n\n"
        "<b>Щит защищает от атак.</b>\n"
        "<b>Пока щит активен — атаковать вас нельзя.</b>\n\n"
        "<b>Выбери длительность</b> 👇"
    )
    await premium.edit_html(call.message, text, reply_markup=_shield_kb())
    await call.answer()


@router.callback_query(F.data.startswith("mining_buy_shield:"))
async def mining_buy_shield(call: CallbackQuery, db: Database, premium: PremiumEmoji):
    tg_id = call.from_user.id
    sid = call.data.split(":", 1)[1]
    pack = next((p for p in SHIELD_PACKS if p[0] == sid), None)
    if not pack:
        await call.answer("Пакет не найден", show_alert=True)
        return

    _, title, price, dur = pack

    conn = db._connect()
    cur = conn.cursor()
    try:
        cur.execute("BEGIN IMMEDIATE")
        _reset_daily_attacks_if_needed(conn, tg_id)
        _apply_mining(conn, tg_id)

        cur.execute("SELECT usdt_balance, miner_shield_until FROM users WHERE tg_id=?", (tg_id,))
        r = cur.fetchone()
        usdt = float((r["usdt_balance"] if r else 0.0) or 0.0)
        shield_until = int((r["miner_shield_until"] if r else 0) or 0)

        if usdt + 1e-9 < float(price):
            conn.rollback()
            await call.answer("❌ Недостаточно USDT", show_alert=True)
            return

        now = _utc_now_ts()
        base = shield_until if shield_until > now else now
        new_shield_until = base + int(dur)

        cur.execute("""
            UPDATE users
            SET usdt_balance=?,
                miner_shield_until=?
            WHERE tg_id=?
        """, (usdt - float(price), new_shield_until, tg_id))

        conn.commit()
    except Exception:
        conn.rollback()
        await call.answer("❌ Ошибка покупки", show_alert=True)
        return
    finally:
        conn.close()

    await call.answer(f"✅ Куплено: {title}")
    await mining_open(call, db, premium)


@router.callback_query(F.data.startswith("mining_attack_open:"))
async def mining_attack_open(call: CallbackQuery, db: Database, premium: PremiumEmoji):
    tg_id = call.from_user.id
    try:
        idx = int(call.data.split(":", 1)[1])
    except Exception:
        idx = 0

    conn = db._connect()
    cur = conn.cursor()
    try:
        cur.execute("BEGIN IMMEDIATE")
        _reset_daily_attacks_if_needed(conn, tg_id)
        _apply_mining(conn, tg_id)

        cur.execute("""
            SELECT miner_power, miner_attacks_used_today, miner_attacks_bonus_today
            FROM users WHERE tg_id=?
        """, (tg_id,))
        a = cur.fetchone()
        attacker_power = float((a["miner_power"] if a else 1.0) or 1.0)
        used_today = int((a["miner_attacks_used_today"] if a else 0) or 0)
        bonus_today = int((a["miner_attacks_bonus_today"] if a else 0) or 0)

        targets = _get_attack_targets(conn, tg_id)
        conn.commit()
    except Exception:
        conn.rollback()
        targets = []
        attacker_power = 1.0
        used_today = 0
        bonus_today = 0
    finally:
        conn.close()

    if not targets:
        text = (
            "⚔️ <b>Атака</b>\n\n"
            "<b>Пока нет подходящих целей.</b>\n"
            "<b>Подсказка: цели появляются, когда у них есть Намайнено и нет щита.</b>"
        )
        await premium.edit_html(call.message, text, reply_markup=_back_to_mining_kb())
        await call.answer()
        return

    idx = max(0, min(idx, len(targets) - 1))
    t = targets[idx]

    target_id = int(t["tg_id"])
    uname = (t["username"] or "NoUsername")
    if uname and not str(uname).startswith("@"):
        uname = "@" + str(uname)

    t_power = float((t["miner_power"] if "miner_power" in t.keys() else 1.0) or 1.0)
    t_hp = int((t["miner_hp"] if "miner_hp" in t.keys() else 100) or 100)
    t_stored = float((t["miner_stored"] if "miner_stored" in t.keys() else 0.0) or 0.0)

    max_steal = attacker_power * STEAL_CAP_PER_POWER
    can_steal = min(t_stored * STEAL_PCT, max_steal)

    can_attack = (used_today == 0) or (bonus_today > 0)
    attempts_left = (1 if used_today == 0 else 0) + bonus_today

    text = (
        f"⚔️ <b>Цель:</b> {uname}\n\n"
        f"⚡ <b>Сила цели:</b> {_fmt2(t_power)}\n"
        f"❤️ <b>HP цели:</b> {t_hp}%\n"
        f"📦 <b>У цели намайнено:</b> {_fmt2(t_stored)} DGR\n"
        f"🎒 <b>Ты можешь украсть:</b> до <b>{_fmt2(can_steal)}</b> DGR\n\n"
        f"🗓 <b>Атак сегодня осталось:</b> {attempts_left}"
    )

    await premium.edit_html(call.message, text, reply_markup=_attack_kb(idx, len(targets), can_attack, target_id))
    await call.answer()


@router.callback_query(F.data.startswith("mining_attack_do:"))
async def mining_attack_do(call: CallbackQuery, db: Database, premium: PremiumEmoji):
    tg_id = call.from_user.id
    parts = call.data.split(":")
    if len(parts) < 3:
        await call.answer("Ошибка", show_alert=True)
        return
    target_id = int(parts[1])
    idx = int(parts[2]) if parts[2].isdigit() else 0

    await call.answer()
    for dots in (".", "..", "..."):
        try:
            await premium.edit_html(call.message, f"⚔️ <b>Атакую{dots}</b>")
        except Exception:
            pass

    conn = db._connect()
    cur = conn.cursor()

    stolen = 0.0     # ✅ будет равно steal, чтобы текст не показывал 0.00
    dmg = 0          # ✅ будет равно hp_steal, чтобы "Урон цели" был не 0
    blocked = False
    reason = ""

    # для пуша (жертве)
    new_t_stored = 0.0
    power_steal = 0.0
    hp_steal = 0

    try:
        cur.execute("BEGIN IMMEDIATE")

        _reset_daily_attacks_if_needed(conn, tg_id)
        _reset_daily_attacks_if_needed(conn, target_id)

        _apply_mining(conn, tg_id)
        _apply_mining(conn, target_id)

        cur.execute("""
            SELECT miner_power, miner_attacks_used_today, miner_attacks_bonus_today
            FROM users WHERE tg_id=?
        """, (tg_id,))
        a = cur.fetchone()
        if not a:
            raise RuntimeError("attacker missing")

        attacker_power = float((a["miner_power"] if "miner_power" in a.keys() else 1.0) or 1.0)
        used_today = int((a["miner_attacks_used_today"] if "miner_attacks_used_today" in a.keys() else 0) or 0)
        bonus_today = int((a["miner_attacks_bonus_today"] if "miner_attacks_bonus_today" in a.keys() else 0) or 0)

        # лимит атак
        if used_today == 0:
            new_used = 1
            new_bonus = bonus_today
        else:
            if bonus_today <= 0:
                blocked = True
                reason = "❌ Лимит атак на сегодня исчерпан"
            else:
                new_used = used_today + 1
                new_bonus = bonus_today - 1

        if blocked:
            conn.rollback()
        else:
            cur.execute("""
                SELECT username, miner_stored, miner_hp, miner_shield_until, miner_power
                FROM users WHERE tg_id=?
            """, (target_id,))
            t = cur.fetchone()
            if not t:
                raise RuntimeError("target missing")

            now = _utc_now_ts()
            shield_until = int((t["miner_shield_until"] if "miner_shield_until" in t.keys() else 0) or 0)
            if shield_until > now:
                blocked = True
                reason = "🛡 Цель под щитом"
                conn.rollback()
            else:
                t_stored = float((t["miner_stored"] if "miner_stored" in t.keys() else 0.0) or 0.0)
                t_hp = int((t["miner_hp"] if "miner_hp" in t.keys() else 100) or 100)
                t_power = float((t["miner_power"] if "miner_power" in t.keys() else 1.0) or 1.0)

                # --- DIGI steal ---
                max_steal = attacker_power * STEAL_CAP_PER_POWER
                steal = min(t_stored * STEAL_PCT, max_steal)
                steal = float(f"{steal:.2f}")

                # --- steal POWER (снимаем у цели, НЕ добавляем атакеру) ---
                power_steal = min(t_power * POWER_STEAL_PCT, POWER_STEAL_CAP)
                power_steal = float(f"{power_steal:.3f}")

                # --- steal HP (снимаем у цели и добавляем атакеру) ---
                hp_steal = min(int(round(t_hp * HP_STEAL_PCT)), HP_STEAL_CAP)
                hp_steal = max(0, hp_steal)

                new_t_stored = float(f"{max(0.0, t_stored - steal):.4f}")
                new_t_power = float(f"{max(0.2, t_power - power_steal):.4f}")
                new_t_hp = max(0, t_hp - hp_steal)

                # атакующий получает DIGI в баланс (как у тебя)
                cur.execute("SELECT balance_digi, miner_hp FROM users WHERE tg_id=?", (tg_id,))
                a2 = cur.fetchone()
                a_bal = int((a2["balance_digi"] if a2 else 0) or 0)
                a_hp = int((a2["miner_hp"] if a2 else 100) or 100)

                add_int = int(round(steal))
                cur.execute("""
                    UPDATE users
                    SET balance_digi=?,
                        miner_hp=?
                    WHERE tg_id=?
                """, (a_bal + add_int, min(100, a_hp + hp_steal), tg_id))

                # цель теряет stored, мощность, hp
                cur.execute("""
                    UPDATE users
                    SET miner_stored=?,
                        miner_power=?,
                        miner_hp=?
                    WHERE tg_id=?
                """, (new_t_stored, new_t_power, new_t_hp, target_id))

                # списываем попытку атаки
                cur.execute("""
                    UPDATE users
                    SET miner_attacks_used_today=?,
                        miner_attacks_bonus_today=?
                    WHERE tg_id=?
                """, (new_used, new_bonus, tg_id))

                # ✅ фикс для текста результата:
                stolen = steal
                dmg = hp_steal

                conn.commit()

                # пуш-уведомление цели (текст НЕ меняю, только данные правильные)
                try:
                    attacker_un = call.from_user.username or "NoUsername"
                    attacker_tag = ("@" + attacker_un) if attacker_un and not attacker_un.startswith("@") else attacker_un
                    push = (
                        "🚨 <b>Вас атакуют!</b>\n\n"
                        f"🎯 Атакующий: {attacker_tag}\n"
                        f"🔻 Украдено: <b>{_fmt2(stolen)}</b> DGR\n"
                        f"⚡ Потеря мощности: <b>-{_fmt2(power_steal)}</b>\n"
                        f"❤️ Потеря HP: <b>-{hp_steal}%</b>\n"
                        f"📦 Осталось в хранилище: <b>{_fmt2(new_t_stored)}</b> DGR"
                    )
                    m = await call.bot.send_message(chat_id=target_id, text="…")
                    await premium.edit_html(m, push)
                except Exception:
                    pass

    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        blocked = True
        reason = "❌ Ошибка атаки"
    finally:
        conn.close()

    if blocked:
        await premium.edit_html(call.message, f"{reason}\n\n⬅️ Вернуться к целям.", reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ Назад к целям", callback_data=f"mining_attack_open:{idx}")],
                [InlineKeyboardButton(text="⬅️ В майнинг", callback_data="mining_open")],
            ]
        ))
        return

    # ✅ Текст НЕ трогаю, просто теперь stolen/dmg будут правильными
    res = (
        "✅ <b>Атака завершена!</b>\n\n"
        f"🔻 Украдено: <b>{_fmt2(stolen)}</b> DGR\n"
        f"❤️ Урон цели: <b>-{dmg}%</b>\n\n"
        "Открываю список целей…"
    )
    await premium.edit_html(call.message, res, reply_markup=InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🎯 К целям", callback_data=f"mining_attack_open:{idx}")],
            [InlineKeyboardButton(text="⬅️ В майнинг", callback_data="mining_open")],
        ]
    ))