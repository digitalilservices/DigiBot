# handlers/ads.py
from __future__ import annotations

import re
import math
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from config import Config
from database import Database

router = Router()

PER_PAGE = 1  # листаем по 1 объявлению

class AdsStates(StatesGroup):
    waiting_desc = State()
    waiting_link = State()
    waiting_days = State()


# ---------- Keyboards ----------
def ads_nav_kb(page: int, total_pages: int) -> InlineKeyboardMarkup:
    row: list[InlineKeyboardButton] = []

    if page > 0:
        row.append(InlineKeyboardButton(text="⬅️", callback_data=f"ads_page:{page-1}"))

    row.append(InlineKeyboardButton(text=f"{page+1}/{max(total_pages, 1)}", callback_data="ads_noop"))

    if page < total_pages - 1:
        row.append(InlineKeyboardButton(text="➡️", callback_data=f"ads_page:{page+1}"))

    return InlineKeyboardMarkup(inline_keyboard=[
        row,
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="ads_back_menu")]
    ])


def _ads_cancel_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="❌ Отмена", callback_data="ads_cancel")
    kb.adjust(1)
    return kb.as_markup()


def _is_valid_link(link: str) -> bool:
    link = link.strip()
    if link.startswith("https://t.me/") or link.startswith("http://") or link.startswith("https://"):
        return True
    if re.match(r"^t\.me\/[A-Za-z0-9_\/\-\+]+$", link):
        return True
    return False


def _normalize_link(link: str) -> str:
    link = link.strip()
    if link.startswith("t.me/"):
        return "https://" + link
    return link


def _format_ad(ad, idx: int, total: int) -> str:
    # ad может быть sqlite3.Row -> читаем через ["col"]
    desc = (str(ad["description"] or "")).strip()
    link = (str(ad["link"] or "")).strip()
    expires = (str(ad["expires_at"] or "")).strip()

    text = [
        "📢 <b>Объявления</b>",
        f"📌 <b>{idx}/{total}</b>\n",
    ]

    if desc:
        text.append(f"📝 {desc}\n")
    if link:
        text.append(f"🔗 {link}\n")
    if expires:
        text.append

    return "\n".join(text)



async def _show_ads_page(msg: Message, db: Database, page: int):
    ads = db.get_active_ads()  # ✅ используем то, что уже есть у тебя
    total = len(ads)

    if total <= 0:
        await msg.edit_text("📢 <b>Объявления</b>\n\nПока нет активных реклам.", reply_markup=ads_nav_kb(0, 1))
        return

    total_pages = max(1, math.ceil(total / PER_PAGE))
    page = max(0, min(page, total_pages - 1))

    ad = ads[page]  # PER_PAGE=1 => просто берём нужный элемент
    text = _format_ad(ad, idx=page + 1, total=total)

    await msg.edit_text(text, reply_markup=ads_nav_kb(page, total_pages))


# ---------- Open ads ----------
@router.message(F.text.in_(["📢 Объявления", "📣 Объявления"]))
async def ads_open(message: Message, db: Database):
    sent = await message.answer("Загрузка...")
    await _show_ads_page(sent, db, page=0)


@router.callback_query(F.data.startswith("ads_page:"))
async def ads_page(call: CallbackQuery, db: Database):
    page = int(call.data.split(":", 1)[1])
    await _show_ads_page(call.message, db, page=page)
    await call.answer()


@router.callback_query(F.data == "ads_noop")
async def ads_noop(call: CallbackQuery):
    await call.answer()


# ---------- Create ad ----------
@router.callback_query(F.data == "ads_create")
async def ads_create(call: CallbackQuery, state: FSMContext, cfg: Config):
    await state.clear()
    await state.set_state(AdsStates.waiting_desc)

    text = (
        "📢 <b>Создание рекламы</b>\n\n"
        "✍️ Введите <b>описание</b> объявления (1-3 строки).\n\n"
        f"💎 Цена: <b>{cfg.ADS_PRICE_PER_DAY_DIGI:,} DIGI</b> за 1 день"
    )
    await call.message.answer(text, reply_markup=_ads_cancel_kb())
    await call.answer()


@router.message(AdsStates.waiting_desc)
async def ads_desc(message: Message, state: FSMContext):
    desc = (message.text or "").strip()
    if len(desc) < 5:
        await message.answer("❌ Слишком коротко. Напишите описание чуть подробнее.")
        return
    if len(desc) > 500:
        await message.answer("❌ Слишком длинно. Максимум 500 символов.")
        return

    await state.update_data(description=desc)
    await state.set_state(AdsStates.waiting_link)

    await message.answer(
        "🔗 Теперь отправьте <b>ссылку</b> (например: https://t.me/your_channel)\n"
        "Можно и так: t.me/your_channel",
        reply_markup=_ads_cancel_kb()
    )


@router.message(AdsStates.waiting_link)
async def ads_link(message: Message, state: FSMContext):
    link = (message.text or "").strip()
    if not _is_valid_link(link):
        await message.answer("❌ Ссылка некорректна. Пример: https://t.me/your_channel")
        return

    link = _normalize_link(link)
    await state.update_data(link=link)
    await state.set_state(AdsStates.waiting_days)

    await message.answer(
        "📅 На сколько дней размещаем?\n"
        "Введите число дней (например: <b>1</b>, <b>3</b>, <b>7</b>)",
        reply_markup=_ads_cancel_kb()
    )


@router.message(AdsStates.waiting_days)
async def ads_days(message: Message, state: FSMContext, db: Database, cfg: Config):
    raw = (message.text or "").strip()
    if not raw.isdigit():
        await message.answer("❌ Введите число дней цифрами. Пример: <b>3</b>")
        return

    days = int(raw)
    if days <= 0:
        await message.answer("❌ Количество дней должно быть больше 0.")
        return
    if days > 365:
        await message.answer("❌ Максимум 365 дней.")
        return

    data = await state.get_data()
    desc = data["description"]
    link = data["link"]

    total_cost = days * cfg.ADS_PRICE_PER_DAY_DIGI

    tg_id = message.from_user.id
    user = db.get_user(tg_id)
    if not user:
        db.create_user(tg_id=tg_id, username=message.from_user.username or "NoUsername", referrer_id=None)
        user = db.get_user(tg_id)

    balance = int(user["balance_digi"] or 0)
    if balance < total_cost:
        await message.answer(
            "❌ Недостаточно DIGI.\n\n"
            f"💎 Нужно: <b>{total_cost:,}</b> DIGI\n"
            f"💰 Ваш баланс: <b>{balance:,}</b> DIGI"
        )
        return

    ok = db.spend_balance(tg_id, total_cost)
    if not ok:
        await message.answer("❌ Не удалось списать средства. Попробуйте ещё раз.")
        return

    db.add_ad(user_id=tg_id, description=desc, link=link, days=days)
    await state.clear()

    text = (
        "✅ <b>Реклама размещена!</b>\n\n"
        f"📝 Описание: {desc}\n"
        f"🔗 Ссылка: {link}\n"
        f"📅 Срок: <b>{days}</b> дней\n"
        f"💎 Списано: <b>{total_cost:,}</b> DIGI\n\n"
        "Теперь она появится в разделе <b>📢 Объявления</b>."
    )
    await message.answer(text)


@router.callback_query(F.data == "ads_cancel")
async def ads_cancel(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.answer("❌ Создание рекламы отменено.")
    await call.answer()

@router.callback_query(F.data == "ads_back_menu")
async def ads_back_menu(call: CallbackQuery):
    # самый простой вариант — просто имитируем "в меню"
    await call.message.answer("🏠 Главное меню 👇")
    await call.answer()





