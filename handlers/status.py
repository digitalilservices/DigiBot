from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext

from config import Config
from database import Database
from services.premium_emoji import PremiumEmoji

router = Router()

def _confirm_activate_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Заморозить 5 USDT", callback_data="status_activate_confirm")
    kb.button(text="⬅️ Назад", callback_data="cabinet")
    kb.adjust(1)
    return kb.as_markup()

@router.callback_query(F.data == "status_activate_info")
async def status_activate_info(call: CallbackQuery, db: Database, cfg: Config, premium: PremiumEmoji):
    tg_id = call.from_user.id
    u = db.get_user(tg_id) or {}
    usdt = float(u.get("usdt_balance") or 0.0)
    locked = float(u.get("usdt_locked") or 0.0)

    text = (
        "🟢 <b>Активация статуса «Активный»</b>\n\n"
        "Чтобы открыть рефералку, вывод и конвертацию — нужно <b>заморозить 5 USDT</b>.\n\n"
        f"💰 Баланс USDT: <b>{usdt:.2f}</b>\n"
        f"🔒 Депозит статуса: <b>{locked:.2f}</b> / <b>5.00</b>\n\n"
        "✅ Заморозка — это не комиссия.\n"
        "Вы сможете <b>вывести депозит в любой момент</b>, но тогда статус станет <b>«Новичок»</b> и доступы закроются."
    )
    await premium.answer_html(call.message, text, reply_markup=_confirm_activate_kb())
    await call.answer()

@router.callback_query(F.data == "status_activate_confirm")
async def status_activate_confirm(call: CallbackQuery, db: Database, cfg: Config, premium: PremiumEmoji):
    tg_id = call.from_user.id

    ok, msg = db.lock_status_deposit(tg_id, deposit_usdt=5.0)
    if not ok:
        await call.answer(msg, show_alert=True)
        return

    await call.answer("✅ Активировано", show_alert=True)
    await premium.answer_html(
        call.message,
        "✅ <b>Статус «Активный» включён</b>\n\n"
        "🔒 Депозит 5 USDT заморожен.\n"
        "Теперь доступны: рефералка, вывод и конвертация.",
    )
