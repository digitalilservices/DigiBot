# handlers/earn.py
from __future__ import annotations

import logging
import re
import math
from typing import Optional

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

from config import Config
from database import Database
from keyboards.earn_menu import (
    earn_categories_inline,
    earn_add_root_inline,
)

from services.premium_emoji import PremiumEmoji  # ✅ premium

router = Router()


# ---------- FSM ----------
class EarnStates(StatesGroup):
    add_wait_link = State()
    add_wait_instructions = State()   # bot
    add_wait_reaction = State()       # react
    add_wait_price = State()
    add_wait_qty = State()

    manual_wait_screenshot = State()


# ---------- helpers ----------
def _get_digi_balance(db: Database, tg_id: int) -> int:
    """
    Пытаемся достать баланс DIGI из users.
    Поддержка разных названий колонок.
    """
    u = db.get_user(tg_id)
    if not u:
        return 0
    for k in ("digi_balance", "balance_digi", "balance"):
        try:
            if k in u.keys() and u[k] is not None:
                return int(u[k])
        except Exception:
            pass
    return 0


def _back_to_add_root_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="earn_add_root")]
    ])


def _after_create_task_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📦 Мои задания", callback_data="earn_my_tasks")],
        [InlineKeyboardButton(text="➕ Добавить задание", callback_data="earn_add_root")],
        [InlineKeyboardButton(text="🏠 В меню", callback_data="go_menu")],
    ])


def _after_cancel_task_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📦 Мои задания", callback_data="earn_my_tasks")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="earn_back")],
    ])


def _ensure_user(db: Database, tg_id: int, username: str):
    u = db.get_user(tg_id)
    if not u:
        db.create_user(tg_id=tg_id, username=username, referrer_id=None)
        u = db.get_user(tg_id)
    else:
        if (u["username"] or "") != (username or ""):
            db.update_username(tg_id, username)
            u = db.get_user(tg_id)
    return u


def _extract_username_from_tme(url: str) -> Optional[str]:
    """
    https://t.me/username
    t.me/username
    @username
    -> username (без @)
    """
    url = (url or "").strip()

    if url.startswith("@"):
        u = url[1:].strip()
        return u if u else None

    m = re.search(r"(?:https?:\/\/)?t\.me\/([A-Za-z0-9_]+)", url)
    if m:
        return m.group(1)

    return None


def _normalize_public_tme_link_only(url: str) -> Optional[str]:
    """
    Только публичная ссылка на t.me/<username> (без @, без invite).
    -> https://t.me/<username> или None
    """
    url = (url or "").strip()

    if url.startswith("@"):
        return None

    m = re.fullmatch(r"(?:https?:\/\/)?t\.me\/([A-Za-z0-9_]{5,32})", url)
    if not m:
        return None

    uname = m.group(1)
    if uname.lower() in ("joinchat",):
        return None

    return f"https://t.me/{uname}"


def _parse_post_link_any(url: str) -> Optional[str]:
    """
    Принимаем ЛЮБУЮ нормальную ссылку на пост:

    Публичные:
      1) https://t.me/username/123
      2) https://t.me/username/10/151     (форум/топик/пост)

    Приват/супергруппа:
      3) https://t.me/c/123456789/456
      4) https://t.me/c/123456789/10/151  (приватный форум/топик/пост)

    Возвращаем нормализованную ссылку https://... или None
    """
    url = (url or "").strip()

    # public: /username/<msg>
    m1 = re.fullmatch(r"(?:https?:\/\/)?t\.me\/([A-Za-z0-9_]{5,32})\/(\d+)", url)
    if m1:
        uname, msg_id = m1.group(1), int(m1.group(2))
        if uname.lower() == "joinchat" or msg_id <= 0:
            return None
        return f"https://t.me/{uname}/{msg_id}"

    # public forum/topic: /username/<topic>/<msg>
    m2 = re.fullmatch(r"(?:https?:\/\/)?t\.me\/([A-Za-z0-9_]{5,32})\/(\d+)\/(\d+)", url)
    if m2:
        uname, topic_id, msg_id = m2.group(1), int(m2.group(2)), int(m2.group(3))
        if uname.lower() == "joinchat" or topic_id <= 0 or msg_id <= 0:
            return None
        return f"https://t.me/{uname}/{topic_id}/{msg_id}"

    # private/supergroup: /c/<cid>/<msg>
    m3 = re.fullmatch(r"(?:https?:\/\/)?t\.me\/c\/(\d+)\/(\d+)", url)
    if m3:
        cid, msg_id = int(m3.group(1)), int(m3.group(2))
        if cid <= 0 or msg_id <= 0:
            return None
        return f"https://t.me/c/{cid}/{msg_id}"

    # private forum/topic: /c/<cid>/<topic>/<msg>
    m4 = re.fullmatch(r"(?:https?:\/\/)?t\.me\/c\/(\d+)\/(\d+)\/(\d+)", url)
    if m4:
        cid, topic_id, msg_id = int(m4.group(1)), int(m4.group(2)), int(m4.group(3))
        if cid <= 0 or topic_id <= 0 or msg_id <= 0:
            return None
        return f"https://t.me/c/{cid}/{topic_id}/{msg_id}"

    return None


async def _ensure_bot_is_admin_in_chat(bot, chat_id: str) -> bool:
    try:
        me = await bot.get_me()
        cm = await bot.get_chat_member(chat_id=chat_id, user_id=me.id)
        status = getattr(cm, "status", None)
        return status in ("administrator", "creator")
    except Exception:
        return False


def _pretty_kind(kind: str) -> str:
    return {
        "channel": "📣 Подписка на канал",
        "group": "👥 Вступление в группу",
        "views": "📰 Пост",
        "bot": "🤖 Задание в боте",
        "react": "🔥 Реакция на пост",
    }.get(kind, kind)


def _limit_state(db: Database, cfg: Config, tg_id: int) -> tuple[int, int]:
    status = db.get_status(tg_id)
    limit = 1000 if status == "active" else 1000
    done = db.get_tasks_done_today(tg_id)
    return limit, done


def _tasks_page_kb(kind: str, tasks, page: int, total_pages: int) -> InlineKeyboardMarkup:
    rows = []

    for t in tasks:
        reward = int(t["price_digi"])
        task_id = int(t["id"])

        # channel/group: URL + проверить
        if kind in ("channel", "group"):
            url = str(t["url"])
            left = "Подписаться" if kind == "channel" else "Вступить"
            rows.append([
                InlineKeyboardButton(text=f"+{reward:,} 💰 | {left}", url=url),
                InlineKeyboardButton(text="🔄 Проверить", callback_data=f"earn_check:{kind}:{page}:{task_id}"),
            ])
            continue

        # views/bot/react: открыть карточку
        rows.append([
            InlineKeyboardButton(
                text=f"+{reward:,} 💰 | 📋 Открыть",
                callback_data=f"earn_open:{kind}:{page}:{task_id}"
            ),
        ])

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="⬅️", callback_data=f"earn_page:{kind}:{page-1}"))
    nav.append(InlineKeyboardButton(text=f"{page+1}/{max(total_pages, 1)}", callback_data="noop"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton(text="➡️", callback_data=f"earn_page:{kind}:{page+1}"))
    rows.append(nav)

    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="earn_back")])

    return InlineKeyboardMarkup(inline_keyboard=rows)


async def _render_tasks_page(call: CallbackQuery, db: Database, cfg: Config, kind: str, page: int, tg_id: int, premium: PremiumEmoji):
    limit, done = _limit_state(db, cfg, tg_id)

    per_page = 5
    total = db.market_count_tasks_for_user(kind=kind, user_id=tg_id)

    if total <= 0:
        text = (
            "✅ <b>Все задания этого типа закончились</b>\n"
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад", callback_data="earn_back")]])
        try:
            await premium.edit_text_html(call.message, text, reply_markup=kb)
        except Exception:
            await premium.answer_html(call.message, text, reply_markup=kb)
        return

    total_pages = max(1, math.ceil(total / per_page))
    page = max(0, min(page, total_pages - 1))
    offset = page * per_page

    tasks = db.market_list_tasks_for_user_paged(kind=kind, user_id=tg_id, limit=per_page, offset=offset)

    text = (
        "👇 <b>Нажмите на кнопку, чтобы открыть задание</b>\n\n"
        "⚠️ <b>Запрещено отписываться</b> раньше <b>10</b> суток от каналов и групп.\n"
        "Иначе монеты будут списаны и возвращены владельцу."
    )

    try:
        await premium.edit_text_html(call.message, text, reply_markup=_tasks_page_kb(kind, tasks, page, total_pages))
    except Exception:
        await premium.answer_html(call.message, text, reply_markup=_tasks_page_kb(kind, tasks, page, total_pages))


def _my_tasks_kb(tasks) -> InlineKeyboardMarkup:
    rows = []
    for i, t in enumerate(tasks, start=1):
        tid = int(t["id"])
        rows.append([InlineKeyboardButton(text=f"🗑 Отменить #{i}", callback_data=f"earn_cancel_task:{tid}")])
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="earn_back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _task_extra_text(task_row) -> str:
    kind = str(task_row["kind"] or "")
    instr = (task_row["instructions"] or "").strip() if "instructions" in task_row.keys() else ""
    react = (task_row["reaction"] or "").strip() if "reaction" in task_row.keys() else ""

    out = []
    if kind == "bot" and instr:
        out.append(f"📝 <b>Условия:</b> {instr}")
    if kind == "react" and react:
        out.append(f"❤️ <b>Реакция:</b> {react}")
    if kind == "views":
        out.append("📰 <b>Нужно:</b> открыть пост и выполнить условие (просмотр/прочтение).")

    return ("\n".join(out) + "\n\n") if out else ""


def _task_details_kb(url: str, kind: str, page: int, task_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➡️ Перейти", url=url)],
        [InlineKeyboardButton(text="🔄 Проверить", callback_data=f"earn_check:{kind}:{page}:{task_id}")],
        [InlineKeyboardButton(text="⬅️ Назад к списку", callback_data=f"earn_page:{kind}:{page}")]
    ])


# ---------- UI ----------
@router.callback_query(F.data == "noop")
async def _noop(call: CallbackQuery):
    await call.answer()


@router.message(F.text == "💸 Заработать")
async def earn_root(message: Message, db: Database, cfg: Config, premium: PremiumEmoji):
    tg_id = message.from_user.id
    limit, done = _limit_state(db, cfg, tg_id)

    counts = db.market_counts_for_user(tg_id)

    text = (
        "🔔 <b>Выберите способ заработка</b> 👇\n\n"
        f"📣 <b>Каналы:</b> <b>{counts.get('channel', 0)}</b>\n"
        f"👥 <b>Группы:</b> <b>{counts.get('group', 0)}</b>\n"
        f"📰 <b>Посты:</b> <b>{counts.get('views', 0)}</b>\n"
        f"🤖 <b>Боты:</b> <b>{counts.get('bot', 0)}</b>\n"
        f"🔥 <b>Реакции:</b> <b>{counts.get('react', 0)}</b>"
    )

    await premium.answer_html(message, text, reply_markup=earn_categories_inline(counts))


@router.callback_query(F.data == "earn_back")
async def earn_back(call: CallbackQuery, db: Database, cfg: Config, premium: PremiumEmoji):
    tg_id = call.from_user.id
    limit, done = _limit_state(db, cfg, tg_id)

    counts = db.market_counts_for_user(tg_id)

    text = (
        "🔔 <b>Выберите способ заработка</b> 👇\n\n"
        f"📣 <b>Каналы:</b> <b>{counts.get('channel', 0)}</b>\n"
        f"👥 <b>Группы:</b> <b>{counts.get('group', 0)}</b>\n"
        f"📰 <b>Посты:</b> <b>{counts.get('views', 0)}</b>\n"
        f"🤖 <b>Боты:</b> <b>{counts.get('bot', 0)}</b>\n"
        f"🔥 <b>Реакции:</b> <b>{counts.get('react', 0)}</b>"
    )

    await premium.answer_html(call.message, text, reply_markup=earn_categories_inline(counts))
    await call.answer()


# ========================= МОИ ЗАДАНИЯ =========================
@router.message(F.text == "📦 Мои задания")
async def my_tasks_msg(message: Message, db: Database, premium: PremiumEmoji):
    tg_id = message.from_user.id
    tasks = db.market_list_my_active_tasks(owner_id=tg_id, limit=50)

    if not tasks:
        await premium.answer_html(message, "📦 <b>Мои задания</b>\n\n✅ У вас нет активных заданий.")
        return

    lines = ["📦 <b>Мои активные задания</b>\n"]
    for i, t in enumerate(tasks, start=1):
        kind = _pretty_kind(str(t["kind"]))
        price = int(t["price_digi"] or 0)
        total_qty = int(t["total_qty"] or 0)
        remaining = int(t["remaining_qty"] or 0)
        done = max(0, total_qty - remaining)
        escrow = int(t["escrow_remaining"] or 0)

        extra = ""
        if "reaction" in t.keys() and (t["reaction"] or "").strip():
            extra += f"❤️ <b>Реакция:</b> {(t['reaction'] or '').strip()}\n"
        if "instructions" in t.keys() and (t["instructions"] or "").strip():
            extra += f"📝 <b>Условия:</b> {(t['instructions'] or '').strip()}\n"

        lines.append(
            f"🆔 <b>#{i}</b> | {kind}\n"
            f"🪙 <b>{price:,} DGR</b> | 📦 <b>{done}/{total_qty}</b>\n"
            f"🔒 <b>Остаток бюджета (escrow):</b> <b>{escrow:,} DGR</b>\n"
            f"{extra}"
        )

    await premium.answer_html(message, "\n".join(lines), reply_markup=_my_tasks_kb(tasks))


@router.callback_query(F.data == "earn_my_tasks")
async def my_tasks_cb(call: CallbackQuery, db: Database, premium: PremiumEmoji):
    tg_id = call.from_user.id
    tasks = db.market_list_my_active_tasks(owner_id=tg_id, limit=50)

    if not tasks:
        await premium.answer_html(call.message, "📦 <b>Мои задания</b>\n\n✅ У вас нет активных заданий.")
        await call.answer()
        return

    lines = ["📦 <b>Мои активные задания</b>\n"]
    for i, t in enumerate(tasks, start=1):
        kind = _pretty_kind(str(t["kind"]))
        price = int(t["price_digi"] or 0)
        total_qty = int(t["total_qty"] or 0)
        remaining = int(t["remaining_qty"] or 0)
        done = max(0, total_qty - remaining)
        escrow = int(t["escrow_remaining"] or 0)

        extra = ""
        if "reaction" in t.keys() and (t["reaction"] or "").strip():
            extra += f"❤️ <b>Реакция:</b> {(t['reaction'] or '').strip()}\n"
        if "instructions" in t.keys() and (t["instructions"] or "").strip():
            extra += f"📝 <b>Условия:</b> {(t['instructions'] or '').strip()}\n"

        lines.append(
            f"#️⃣ <b>{i}</b> | {kind}\n"
            f"🪙 <b>{price:,} DGR</b> | 📦 <b>{done}/{total_qty}</b>\n"
            f"🔒 <b>Остаток бюджета:</b> <b>{escrow:,} DGR</b>\n"
            f"{extra}"
        )

    await premium.answer_html(call.message, "\n".join(lines), reply_markup=_my_tasks_kb(tasks))
    await call.answer()


@router.callback_query(F.data.startswith("earn_cancel_task:"))
async def cancel_my_task(call: CallbackQuery, db: Database, premium: PremiumEmoji):
    tg_id = call.from_user.id
    try:
        task_id = int(call.data.split(":", 1)[1])
    except Exception:
        await call.answer("Ошибка ID", show_alert=True)
        return

    ok, msg, refund = db.market_cancel_task_and_refund(task_id=task_id, owner_id=tg_id)
    if not ok:
        await call.answer(msg, show_alert=True)
        return

    await premium.answer_html(
        call.message,
        "✅ <b>Задание отменено</b>\n\n"
        f"🆔 <b>ID:</b> <b>{task_id}</b>\n"
        f"💸 <b>Возвращено:</b> <b>{refund:,} DGR</b>\n\n"
        f"{msg}",
        reply_markup=_after_cancel_task_kb()
    )
    await call.answer("✅", show_alert=True)


# ========================= КАТЕГОРИИ =========================
@router.callback_query(F.data.startswith("earn_cat:"))
async def earn_category(call: CallbackQuery, db: Database, cfg: Config, premium: PremiumEmoji):
    kind = call.data.split(":", 1)[1].strip()
    tg_id = call.from_user.id

    limit, done = _limit_state(db, cfg, tg_id)

    per_page = 5
    total = db.market_count_tasks_for_user(kind=kind, user_id=tg_id)

    if total <= 0:
        await call.answer("Нет доступных заданий", show_alert=True)
        return

    total_pages = max(1, math.ceil(total / per_page))
    page = 0
    offset = page * per_page

    tasks = db.market_list_tasks_for_user_paged(kind=kind, user_id=tg_id, limit=per_page, offset=offset)

    text = (
        "👇 <b>Нажмите на кнопку, чтобы открыть задание</b>\n\n"
        "⚠️ <b>Запрещено отписываться</b> раньше <b>10</b> суток от каналов и групп.\n"
        "Иначе монеты будут списаны и возвращены владельцу."
    )

    await premium.answer_html(call.message, text, reply_markup=_tasks_page_kb(kind, tasks, page, total_pages))
    await call.answer()


@router.callback_query(F.data.startswith("earn_page:"))
async def earn_page(call: CallbackQuery, db: Database, cfg: Config, premium: PremiumEmoji):
    _, kind, page_str = call.data.split(":")
    kind = kind.strip()
    page = int(page_str)
    tg_id = call.from_user.id

    per_page = 5
    total = db.market_count_tasks_for_user(kind=kind, user_id=tg_id)
    if total <= 0:
        await call.answer("Нет заданий", show_alert=True)
        return

    total_pages = math.ceil(total / per_page)
    page = max(0, min(page, total_pages - 1))

    offset = page * per_page
    tasks = db.market_list_tasks_for_user_paged(kind=kind, user_id=tg_id, limit=per_page, offset=offset)

    limit, done = _limit_state(db, cfg, tg_id)
    text = (
        "👇 <b>Нажмите на кнопку, чтобы открыть задание</b>\n\n"
        "⚠️ <b>Запрещено отписываться</b> раньше <b>10</b> суток от каналов и групп.\n"
        "Иначе монеты будут списаны и возвращены владельцу."
    )

    try:
        await premium.edit_text_html(call.message, text, reply_markup=_tasks_page_kb(kind, tasks, page, total_pages))
    except Exception:
        await premium.answer_html(call.message, text, reply_markup=_tasks_page_kb(kind, tasks, page, total_pages))

    await call.answer()


# ========================= OPEN (views/bot/react) =========================
@router.callback_query(F.data.startswith("earn_open:"))
async def earn_open(call: CallbackQuery, db: Database, premium: PremiumEmoji):
    # earn_open:<kind>:<page>:<task_id>
    try:
        _, kind, page_str, task_id_str = call.data.split(":", 3)
        kind = kind.strip()
        page = int(page_str)
        task_id = int(task_id_str)
    except Exception:
        await call.answer("Ошибка кнопки", show_alert=True)
        return

    task = db.market_get_task(task_id)
    if not task:
        await call.answer("Задание не найдено", show_alert=True)
        return

    url = str(task["url"] or "")
    reward = int(task["price_digi"] or 0)

    instructions = (task["instructions"] if "instructions" in task.keys() else None) or ""
    reaction = (task["reaction"] if "reaction" in task.keys() else None) or ""

    if kind == "views":
        text = (
            "📰 <b>Задание: Пост</b>\n\n"
            "✅ <b>Что нужно сделать:</b>\n"
            "1) Нажмите <b>Перейти</b> и откройте пост\n"
            "2) Посмотрите пост\n"
            "3) Сделайте скриншот и нажмите <b>Проверить</b>\n\n"
            f"🪙 <b>Награда:</b> <b>{reward:,} DGR</b>\n"
            "📎 <b>Проверка:</b> по скриншоту."
        )
    elif kind == "react":
        text = (
            "🔥 <b>Задание: Реакция</b>\n\n"
            "✅ <b>Что нужно сделать:</b>\n"
            "1) Нажмите <b>Перейти</b>\n"
            f"2) Поставьте реакцию: <b>{reaction or 'не указано'}</b>\n"
            "3) Сделайте скриншот и нажмите <b>Проверить</b>\n\n"
            f"🪙 <b>Награда:</b> <b>{reward:,} DGR</b>\n"
            "📎 <b>Проверка:</b> по скриншоту."
        )
    else:  # bot
        text = (
            "🤖 <b>Задание: Бот</b>\n\n"
            "✅ <b>Что нужно сделать:</b>\n"
            f"<b>{instructions or 'не указано'}</b>\n\n"
            "1) Нажмите <b>Перейти</b>\n"
            "2) Выполните условия\n"
            "3) Сделайте скриншот и нажмите <b>Проверить</b>\n\n"
            f"🪙 <b>Награда:</b> <b>{reward:,} DGR</b>\n"
            "📎 <b>Проверка:</b> по скриншоту."
        )

    try:
        await premium.edit_text_html(call.message, text, reply_markup=_task_details_kb(url, kind, page, task_id))
    except Exception:
        await premium.answer_html(call.message, text, reply_markup=_task_details_kb(url, kind, page, task_id))

    await call.answer()


# ========================= CHECK =========================
@router.callback_query(F.data.startswith("earn_check:"))
async def earn_check(call: CallbackQuery, db: Database, cfg: Config, state: FSMContext, premium: PremiumEmoji):
    # earn_check:<kind>:<page>:<task_id>
    try:
        _, kind, page_str, task_id_str = call.data.split(":", 3)
        kind = kind.strip()
        page = int(page_str)
        task_id = int(task_id_str)
    except Exception:
        await call.answer("Ошибка кнопки. Обновите меню.", show_alert=True)
        return

    tg_id = call.from_user.id
    username = call.from_user.username or "NoUsername"
    _ensure_user(db, tg_id, username)

    limit, done = _limit_state(db, cfg, tg_id)
    if done >= limit:
        await call.answer(f"⛔ Лимит на сегодня: {limit} заданий. Попробуйте завтра.", show_alert=True)
        return

    task = db.market_get_task(task_id)
    if not task:
        await call.answer("Задание не найдено", show_alert=True)
        return

    if str(task["status"]) != "active" or int(task["remaining_qty"] or 0) <= 0:
        await call.answer("Задание уже недоступно", show_alert=True)
        return

    if db.market_has_completed(task_id, tg_id):
        await call.answer("Вы уже выполняли это задание", show_alert=True)
        return

    url = str(task["url"] or "")

    # AUTO CHECK channel/group
    if kind in ("channel", "group"):
        uname = _extract_username_from_tme(url)
        if not uname:
            await call.answer("Нужна публичная ссылка t.me/username", show_alert=True)
            return

        chat_id = f"@{uname}"
        try:
            member = await call.bot.get_chat_member(chat_id=chat_id, user_id=tg_id)
        except Exception:
            await call.answer("Не могу проверить. Добавьте бота админом в канал/группу.", show_alert=True)
            return

        status = getattr(member, "status", None)
        if status in ("left", "kicked"):
            await call.answer("❌ Вы не подписались/не вступили", show_alert=True)
            return

        ok, msg = db.market_complete_task_and_pay(task_id=task_id, worker_id=tg_id)
        if ok:
            db.inc_tasks_done_today(tg_id, 1)
            db.increment_tasks_completed(tg_id)


            await call.answer("✅ Зачислено!", show_alert=True)
            await _render_tasks_page(call, db, cfg, kind, page, tg_id, premium)
        else:
            await call.answer(msg, show_alert=True)
        return

    # views/bot/react -> MANUAL CHECK (скрин)
    await state.clear()
    await state.set_state(EarnStates.manual_wait_screenshot)
    await state.update_data(task_id=task_id)

    extra = _task_extra_text(task)

    await premium.answer_html(
        call.message,
        "📎 <b>Нужен скриншот для проверки</b>\n\n"
        f"{extra}"
        "Отправьте <b>скриншот Фото или Документ</b> сюда ✅"
    )
    await call.answer()


@router.message(EarnStates.manual_wait_screenshot)
async def earn_manual_screenshot(message: Message, state: FSMContext, db: Database, cfg: Config, premium: PremiumEmoji):
    data = await state.get_data()
    task_id = int(data.get("task_id") or 0)
    if task_id <= 0:
        await state.clear()
        await premium.answer_html(message, "❌ Ошибка: task_id не найден. Откройте задание ещё раз.")
        return

    tg_id = message.from_user.id
    username = message.from_user.username or "NoUsername"
    _ensure_user(db, tg_id, username)

    limit, done = _limit_state(db, cfg, tg_id)
    if done >= limit:
        await state.clear()
        await premium.answer_html(message, f"⛔ Лимит на сегодня: {limit} заданий. Попробуйте завтра.")
        return

    file_id = None
    if message.photo:
        file_id = message.photo[-1].file_id
    elif message.document:
        file_id = message.document.file_id

    if not file_id:
        await premium.answer_html(message, "❌ Отправьте скриншот как <b>Фото</b> или <b>Документ</b>.")
        return

    task = db.market_get_task(task_id)
    if not task:
        await state.clear()
        await premium.answer_html(message, "❌ Задание не найдено или удалено.")
        return

    if str(task["status"]) != "active" or int(task["remaining_qty"] or 0) <= 0:
        await state.clear()
        await premium.answer_html(message, "❌ Это задание уже недоступно.")
        return

    kind = str(task["kind"] or "")
    owner_id = int(task["owner_id"])
    reward = int(task["price_digi"] or 0)
    url = str(task["url"] or "")

    ok, msg, sub_id = db.market_manual_upsert_pending(task_id=task_id, worker_id=tg_id, file_id=file_id)
    if not ok:
        await premium.answer_html(message, str(msg))
        return

    await state.clear()

    await premium.answer_html(
        message,
        "✅ <b>Заявка отправлена!</b>\n\n"
        "⏳ <b>Статус:</b> <b>на проверке</b>\n\n"
        "<b>После подтверждения владельцем будет начислено DGR.</b>"
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Принять", callback_data=f"own_ok:{sub_id}"),
        InlineKeyboardButton(text="❌ Не выполнено", callback_data=f"own_no:{sub_id}"),
    ]])

    extra = _task_extra_text(task)

    notify = (
        "🧩 <b>Проверка задания</b>\n\n"
        f"👤 <b>Исполнитель:</b> @{username} | <code>{tg_id}</code>\n"
        f"🎯 <b>Задание ID:</b> <b>{task_id}</b>\n"
        f"📌 <b>Тип:</b> <b>{_pretty_kind(kind)}</b>\n"
        f"{extra}"
        f"🪙 <b>Награда:</b> <b>{reward:,} DGR</b>\n"
        f"🔗 <b>Ссылка:</b> {url}\n\n"
        "Проверьте скриншот и выберите действие:"
    )

    try:
        if message.photo:
            await message.bot.send_photo(owner_id, photo=file_id, caption=notify, reply_markup=kb)
        else:
            await message.bot.send_document(owner_id, document=file_id, caption=notify, reply_markup=kb)
    except Exception:
        await premium.answer_html(
            message,
            "⚠️ Не удалось отправить заявку владельцу.\n"
            "Владелец должен хотя бы один раз нажать /start в боте."
        )


# ==========================================================
# =================== ADD TASK (OWNER) =====================
# ==========================================================
@router.callback_query(F.data == "earn_add_root")
async def earn_add_root(call: CallbackQuery, state: FSMContext, premium: PremiumEmoji):
    await state.clear()
    text = "➕ <b>Добавить задание</b>\n\nВыберите тип задания 👇"

    try:
        await premium.edit_text_html(call.message, text, reply_markup=earn_add_root_inline())
    except Exception:
        await premium.answer_html(call.message, text, reply_markup=earn_add_root_inline())

    await call.answer()


@router.callback_query(F.data.startswith("earn_add:"))
async def earn_add_pick(call: CallbackQuery, state: FSMContext, premium: PremiumEmoji):
    kind = call.data.split(":", 1)[1].strip().lower()

    await state.clear()
    await state.update_data(kind=kind)
    await state.set_state(EarnStates.add_wait_link)

    if kind in ("channel", "group"):
        tip = (
            "🔗 <b>Отправьте ссылку на канал/группу</b>\n\n"
            "✅ <code>https://t.me/username</code> или <code>@username</code>\n\n"
            "⚠️ <b>Важно:</b> бот должен быть админом для проверки подписки."
        )
    elif kind == "views":
        tip = (
            "📰 <b>Отправьте ссылку именно на пост</b>\n\n"
        )
    elif kind == "bot":
        tip = (
            "🔗 <b>Отправьте ссылку на бота</b>\n\n"
            "✅ <code>https://t.me/MySuperBot</code>\n"
            "⛔️ Нельзя: <code>@MySuperBot</code>"
        )
    elif kind == "react":
        tip = (
            "🔥 <b>Отправьте ссылку на пост</b>\n\n"
            "⚠️ Далее бот попросит <b>реакцию</b>."
        )
    else:
        tip = "🔗 <b>Отправьте ссылку</b> (t.me/...)"

    await premium.answer_html(
        call.message,
        f"📌 <b>{_pretty_kind(kind)}</b>\n\n{tip}",
        reply_markup=_back_to_add_root_kb()
    )
    await call.answer()


@router.message(EarnStates.add_wait_link)
async def earn_add_link(message: Message, state: FSMContext, premium: PremiumEmoji):
    url_raw = (message.text or "").strip()
    if len(url_raw) < 5:
        await premium.answer_html(message, "❌ Введите нормальную ссылку.", reply_markup=_back_to_add_root_kb())
        return

    data = await state.get_data()
    kind = str(data.get("kind") or "").lower()

    # BOT: только публичная ссылка t.me/username и username оканчивается на bot
    if kind == "bot":
        norm = _normalize_public_tme_link_only(url_raw)
        if not norm:
            await premium.answer_html(
                message,
                "❌ Для задания <b>Бот</b> нужна именно ссылка.\n\n"
                "✅ Пример: <code>https://t.me/MySuperBot</code>\n"
                "⛔️ Нельзя: <code>@MySuperBot</code>",
                reply_markup=_back_to_add_root_kb()
            )
            return

        uname = _extract_username_from_tme(norm)
        if not uname or not uname.lower().endswith("bot"):
            await premium.answer_html(
                message,
                "❌ Это похоже не на бота.\n\n"
                "Для задания <b>Бот</b> принимаются только боты (username обычно заканчивается на <b>bot</b>).\n"
                "✅ Пример: <code>https://t.me/MySuperBot</code>",
                reply_markup=_back_to_add_root_kb()
            )
            return

        url = norm

    # VIEWS / REACT: обязательно ссылка на ПОСТ (включая форум/топики)
    elif kind in ("views", "react"):
        norm_post = _parse_post_link_any(url_raw)
        if not norm_post:
            await premium.answer_html(
                message,
                "❌ Нужна ссылка <b>именно на пост</b>.\n\n",
                reply_markup=_back_to_add_root_kb()
            )
            return
        url = norm_post

    # CHANNEL/GROUP: ссылка на чат/канал + проверка админа
    else:
        url = url_raw

        if kind in ("channel", "group"):
            uname = _extract_username_from_tme(url)
            if not uname:
                await premium.answer_html(
                    message,
                    "❌ Нужна публичная ссылка.\n\n"
                    "✅ <code>https://t.me/username</code>\n"
                    "или <code>@username</code>",
                    reply_markup=_back_to_add_root_kb()
                )
                return

            chat_id = f"@{uname}"
            if not await _ensure_bot_is_admin_in_chat(message.bot, chat_id):
                me = await message.bot.get_me()
                bot_username = getattr(me, "username", None) or "ваш_бот"
                await premium.answer_html(
                    message,
                    "⛔️ <b>Нельзя создать задание</b>\n\n"
                    "Для заданий <b>Канал</b>/<b>Группа</b> бот должен быть <b>админом</b>, "
                    "иначе нельзя проверить подписку/отписку.\n\n"
                    f"✅ Добавьте бота <b>@{bot_username}</b> администратором и пришлите ссылку ещё раз.",
                    reply_markup=_back_to_add_root_kb()
                )
                return

    await state.update_data(url=url)

    if kind == "bot":
        await state.set_state(EarnStates.add_wait_instructions)
        await premium.answer_html(
            message,
            "✍️ <b>Опишите условия для бота</b>\n\n"
            "<b>Что должен сделать исполнитель?</b>\n\n"
            "<b>Пример:</b> <code>Нажать Start, пройти регистрацию, сделать 1 действие…</code>",
            reply_markup=_back_to_add_root_kb()
        )
        return

    if kind == "react":
        await state.set_state(EarnStates.add_wait_reaction)
        await premium.answer_html(
            message,
            "❤️ <b>Укажите 1 реакцию</b>\n\n"
            "<b>Отправьте одну реакцию/эмодзи.</b>\n"
            "<b>Пример:</b> ❤️ <b>или</b> 😍",
            reply_markup=_back_to_add_root_kb()
        )
        return

    await state.set_state(EarnStates.add_wait_price)
    await premium.answer_html(
        message,
        "🪙 <b>Введите оплату за 1 выполнение</b>\n\n"
        "Рекомендация: <b>от 100 DGR</b>",
        reply_markup=_back_to_add_root_kb()
    )


@router.message(EarnStates.add_wait_instructions)
async def earn_add_instructions(message: Message, state: FSMContext, premium: PremiumEmoji):
    txt = (message.text or "").strip()
    if len(txt) < 5 or len(txt) > 800:
        await premium.answer_html(message, "❌ Условия должны быть <b>5–800</b> символов.")
        return
    await state.update_data(instructions=txt)
    await state.set_state(EarnStates.add_wait_price)
    await premium.answer_html(
        message,
        "🪙 <b>Введите оплату за 1 выполнение</b>\n\n"
        "Рекомендация: <b>от 100 DGR</b>",
        reply_markup=_back_to_add_root_kb()
    )


@router.message(EarnStates.add_wait_reaction)
async def earn_add_reaction(message: Message, state: FSMContext, premium: PremiumEmoji):
    r = (message.text or "").strip()
    if len(r) < 1 or len(r) > 10:
        await premium.answer_html(message, "❌ Отправьте <b>ОДНУ</b> реакцию/эмодзи. Пример: ❤️")
        return
    await state.update_data(reaction=r)
    await state.set_state(EarnStates.add_wait_price)
    await premium.answer_html(
        message,
        "🪙 <b>Введите оплату за 1 выполнение</b>\n\n"
        "Рекомендация: <b>от 100 DGR</b>",
        reply_markup=_back_to_add_root_kb()
    )


@router.message(EarnStates.add_wait_price)
async def earn_add_price(message: Message, state: FSMContext, db: Database, premium: PremiumEmoji):
    tg_id = message.from_user.id
    bal = _get_digi_balance(db, tg_id)

    raw = (message.text or "").strip().replace(" ", "")
    if not raw.isdigit():
        await premium.answer_html(
            message,
            "🪙 <b>Введите оплату за 1 выполнение</b>\n\n"
            "📌 Пример: <b>100</b>",
            reply_markup=_back_to_add_root_kb()
        )
        return

    price = int(raw)

    if price < 50:
        await premium.answer_html(message, "❌ Минимальная цена задания: <b>50 DGR</b>")
        return
    if price > 300:
        await premium.answer_html(message, "❌ Максимальная цена задания: <b>300 DGR</b>")
        return

    await state.update_data(price=price)
    await state.set_state(EarnStates.add_wait_qty)

    await premium.answer_html(
        message,
        "📦 <b>Сколько нужно выполнений?</b>\n"
        "Например: <b>20</b>\n\n"
        f"🪙 Ваш баланс: <b>{bal:,} DGR</b>\n"
        f"🧾 Сейчас: <b>{price:,} DGR</b> за 1 выполнение",
        reply_markup=_back_to_add_root_kb()
    )


@router.message(EarnStates.add_wait_qty)
async def earn_add_qty(message: Message, state: FSMContext, db: Database, premium: PremiumEmoji):
    raw = (message.text or "").strip().replace(" ", "")
    if not raw.isdigit():
        await premium.answer_html(message, "❌ Введите число. Например: <b>20</b>")
        return

    qty = int(raw)
    if qty <= 0 or qty > 100_000:
        await premium.answer_html(message, "❌ Неверное количество.")
        return

    data = await state.get_data()
    kind = str(data.get("kind") or "").lower()
    url = str(data.get("url") or "")
    price = int(data.get("price") or 0)

    instructions = (data.get("instructions") or None)
    reaction = (data.get("reaction") or None)

    tg_id = message.from_user.id
    username = message.from_user.username or "NoUsername"
    _ensure_user(db, tg_id, username)

    bal = _get_digi_balance(db, tg_id)
    budget = price * qty

    if bal < budget:
        await premium.answer_html(
            message,
            "❌ <b>Недостаточно DGR для создания задания</b>\n\n"
            f"🪙 Ваш баланс: <b>{bal:,} DGR</b>\n"
            f"🧾 Нужно списать: <b>{budget:,} DGR</b>\n\n"
            "Пополните баланс или уменьшите количество/цену.",
            reply_markup=_back_to_add_root_kb()
        )
        return

    ok, msg, task_id = db.market_create_task(
        owner_id=tg_id,
        kind=kind,
        url=url,
        price_digi=price,
        total_qty=qty,
        title=None,
        instructions=instructions,
        reaction=reaction,
        src_chat_id=None,
        src_message_id=None,
    )

    await state.clear()

    if not ok:
        await premium.answer_html(message, f"❌ {msg}")
        return

    db.increment_tasks_created(tg_id)
    bal_after = max(0, bal - budget)

    extra = ""
    if kind == "react" and reaction:
        extra += f"❤️ <b>Реакция:</b> <b>{reaction}</b>\n"
    if kind == "bot" and instructions:
        extra += f"📝 <b>Условия:</b> <b>{instructions}</b>\n"

    text = (
        "✅ <b>Задание создано!</b>\n\n"
        f"🆔 <b>ID:</b> <b>{task_id}</b>\n"
        f"📌 <b>Тип:</b> <b>{_pretty_kind(kind)}</b>\n"
        f"{extra}"
        f"🪙 <b>За 1:</b> <b>{price:,} DGR</b>\n"
        f"📦 <b>Количество:</b> <b>{qty}</b>\n"
        f"💸 <b>Списано бюджет:</b> <b>{budget:,} DGR</b>\n"
        f"🪙 <b>Баланс:</b> <b>{bal_after:,} DGR</b>\n\n"
        "Выберите действие ниже 👇"
    )

    await premium.answer_html(message, text, reply_markup=_after_create_task_kb())


# ==========================================================
# =================== OWNER APPROVE/REJECT =================
# ==========================================================
@router.callback_query(F.data.startswith("own_ok:"))
async def owner_approve(call: CallbackQuery, db: Database, cfg: Config, premium: PremiumEmoji):
    sub_id = int(call.data.split(":", 1)[1])
    sub = db.market_manual_get(sub_id)
    if not sub:
        await call.answer("Заявка не найдена", show_alert=True)
        return

    task_id = int(sub["task_id"])
    worker_id = int(sub["worker_id"])

    task = db.market_get_task(task_id)
    if not task:
        await call.answer("Задание не найдено", show_alert=True)
        return

    owner_id = int(task["owner_id"])
    if call.from_user.id != owner_id:
        await call.answer("Это не ваше задание", show_alert=True)
        return

    if sub["status"] != "pending":
        await call.answer("Эта заявка уже обработана", show_alert=True)
        return

    limit, done = _limit_state(db, cfg, worker_id)
    if done >= limit:
        db.market_manual_set_status(sub_id, "rejected")
        await call.answer("⛔ У исполнителя лимит на сегодня. Отклонено.", show_alert=True)

        try:
            await call.bot.send_message(
                worker_id,
                f"⛔ Лимит на сегодня: {limit} заданий. Попробуйте завтра.",
                parse_mode="HTML"
            )
        except Exception as e:
            logging.exception("Failed to notify worker about daily limit: %s", e)

        try:
            await call.message.delete()
        except Exception as e:
            logging.exception("Failed to delete owner review message: %s", e)

        return

    ok, msg = db.market_complete_task_and_pay(task_id=task_id, worker_id=worker_id)
    if ok:
        db.market_manual_set_status(sub_id, "approved")
        db.inc_tasks_done_today(worker_id, 1)
        db.increment_tasks_completed(worker_id)

        await call.answer("✅ Зачислено", show_alert=True)

        try:
            await call.bot.send_message(
                worker_id,
                f"✅ Ваш скриншот подтверждён. {msg}",
                parse_mode="HTML"
            )
        except Exception as e:
            logging.exception("Failed to notify worker about approve: %s", e)

        try:
            await call.message.delete()
        except Exception as e:
            logging.exception("Failed to delete owner review message: %s", e)
    else:
        await call.answer(str(msg), show_alert=True)

@router.callback_query(F.data.startswith("own_no:"))
async def owner_reject(call: CallbackQuery, db: Database, premium: PremiumEmoji):
    sub_id = int(call.data.split(":", 1)[1])
    sub = db.market_manual_get(sub_id)
    if not sub:
        await call.answer("Заявка не найдена", show_alert=True)
        return

    task_id = int(sub["task_id"])
    worker_id = int(sub["worker_id"])

    task = db.market_get_task(task_id)
    if not task:
        await call.answer("Задание не найдено", show_alert=True)
        return

    owner_id = int(task["owner_id"])
    if call.from_user.id != owner_id:
        await call.answer("Это не ваше задание", show_alert=True)
        return

    if sub["status"] != "pending":
        await call.answer("Эта заявка уже обработана", show_alert=True)
        return

    db.market_manual_set_status(sub_id, "rejected")
    await call.answer("❌ Отклонено", show_alert=True)

    try:
        await call.bot.send_message(
            worker_id,
            "❌ Скриншот отклонён владельцем.\nПопробуйте ещё раз и отправьте новый скриншот.",
            parse_mode="HTML"
        )
    except Exception as e:
        logging.exception("Failed to notify worker about reject: %s", e)

    try:
        await call.message.delete()
    except Exception as e:
        logging.exception("Failed to delete owner review message: %s", e)
