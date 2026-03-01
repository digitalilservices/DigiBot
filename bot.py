# bot.py
import asyncio
import logging
from datetime import datetime, timedelta

from handlers.statistics import router as statistics_router
from handlers.mining import router as mining_router
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram import Bot, Dispatcher, BaseMiddleware
from handlers.status import router as status_router
from aiohttp import web

from config import load_config
from database import Database
from services.premium_emoji import PremiumEmoji
from services.cryptobot import CryptoBotAPI

from services.webapp_server import create_app

from handlers import games
from handlers.start import router as start_router
from handlers.cabinet import router as cabinet_router
from handlers.topup import router as topup_router
from handlers.purchase import router as purchase_router
from handlers.earn import router as earn_router
from handlers.ads import router as ads_router
from handlers.referral import router as referral_router
from handlers.about import router as about_router
from handlers.withdraw import router as withdraw_router
from handlers.admin import router as admin_router
from handlers.send_digi import router as send_digi_router


class ActivityMiddleware(BaseMiddleware):
    def __init__(self, db: Database):
        self.db = db

    async def __call__(self, handler, event, data):
        user = getattr(event, "from_user", None)
        if user:
            try:
                self.db.touch_user(user.id, user.username, user.first_name)
            except Exception:
                pass
        return await handler(event, data)


def _extract_username_from_tme(url: str) -> str | None:
    import re
    url = (url or "").strip()
    if url.startswith("@"):
        u = url[1:].strip()
        return u or None
    m = re.search(r"(?:https?:\/\/)?t\.me\/([A-Za-z0-9_]+)", url)
    return m.group(1) if m else None


async def _bg_auto_approve_manual(bot: Bot, db: Database, cfg) -> None:
    hours = float(getattr(cfg, "AUTO_APPROVE_HOURS", 24))
    interval = int(getattr(cfg, "AUTO_APPROVE_CHECK_INTERVAL_SEC", 120))
    notify_worker = bool(getattr(cfg, "AUTO_APPROVE_NOTIFY_WORKER", True))
    notify_owner = bool(getattr(cfg, "AUTO_APPROVE_NOTIFY_OWNER", True))

    while True:
        try:
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
                    updated_at TEXT,
                    UNIQUE(task_id, worker_id)
                )
            """)
            conn.commit()

            cur.execute("""
                SELECT id, task_id, worker_id, created_at
                FROM market_manual_submissions
                WHERE status='pending'
                  AND datetime(created_at) <= datetime('now', ?)
                ORDER BY id ASC
                LIMIT 50
            """, (f"-{hours} hours",))
            rows = cur.fetchall()
            conn.close()

            if not rows:
                await asyncio.sleep(interval)
                continue

            for r in rows:
                sub_id = int(r["id"])
                task_id = int(r["task_id"])
                worker_id = int(r["worker_id"])

                task = db.market_get_task(task_id)
                if not task:
                    conn2 = db._connect()
                    c2 = conn2.cursor()
                    c2.execute(
                        "UPDATE market_manual_submissions SET status='rejected', updated_at=datetime('now') WHERE id=? AND status='pending'",
                        (sub_id,)
                    )
                    conn2.commit()
                    conn2.close()
                    continue

                owner_id = int(task["owner_id"])
                kind = str(task["kind"] or "")
                reward = int(task["price_digi"] or 0)

                ok, msg = db.market_complete_task_and_pay(task_id=task_id, worker_id=worker_id)
                if ok:
                    conn3 = db._connect()
                    c3 = conn3.cursor()
                    c3.execute("""
                        UPDATE market_manual_submissions
                        SET status='approved', updated_at=datetime('now')
                        WHERE id=? AND status='pending'
                    """, (sub_id,))
                    conn3.commit()
                    conn3.close()

                    try:
                        db.inc_tasks_done_today(worker_id, 1)
                    except Exception:
                        pass

                    if notify_worker:
                        try:
                            await bot.send_message(
                                worker_id,
                                "✅ <b>Авто-подтверждение</b>\n\n"
                                "Владелец задания не проверил скрин за 24 часа, "
                                "поэтому система подтвердила автоматически.\n"
                                f"{msg}"
                            )
                        except Exception:
                            pass

                    if notify_owner:
                        try:
                            await bot.send_message(
                                owner_id,
                                "⚠️ <b>Авто-подтверждение заявки</b>\n\n"
                                f"Задание #{task_id} ({kind}) было подтверждено автоматически, "
                                "потому что вы не проверили заявку за 24 часа.\n"
                                f"Исполнителю начислено: <b>{reward} DIGI</b>"
                            )
                        except Exception:
                            pass
                else:
                    conn4 = db._connect()
                    c4 = conn4.cursor()
                    c4.execute("""
                        UPDATE market_manual_submissions
                        SET status='rejected', updated_at=datetime('now')
                        WHERE id=? AND status='pending'
                    """, (sub_id,))
                    conn4.commit()
                    conn4.close()

            await asyncio.sleep(2)

        except Exception:
            logging.exception("BG auto-approve error")
            await asyncio.sleep(interval)


async def _bg_check_unsub_penalty(bot: Bot, db: Database, cfg) -> None:
    days = int(getattr(cfg, "UNFOLLOW_PENALTY_DAYS", 10))
    interval = int(getattr(cfg, "UNFOLLOW_CHECK_INTERVAL_SEC", 300))

    conn = db._connect()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS unsub_penalties (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id INTEGER NOT NULL,
            worker_id INTEGER NOT NULL,
            owner_id INTEGER NOT NULL,
            amount_digi INTEGER NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            UNIQUE(task_id, worker_id)
        )
    """)
    conn.commit()
    conn.close()

    while True:
        try:
            conn = db._connect()
            cur = conn.cursor()

            cur.execute("""
                SELECT mc.task_id, mc.worker_id, mc.created_at, mt.owner_id, mt.kind, mt.url, mt.price_digi
                FROM market_completions mc
                JOIN market_tasks mt ON mt.id = mc.task_id
                WHERE mt.kind IN ('channel','group')
                  AND datetime(mc.created_at) >= datetime('now', ?)
                ORDER BY mc.created_at DESC
                LIMIT 200
            """, (f"-{days} days",))
            rows = cur.fetchall()
            conn.close()

            for r in rows:
                task_id = int(r["task_id"])
                worker_id = int(r["worker_id"])
                owner_id = int(r["owner_id"])
                kind = str(r["kind"])
                url = str(r["url"] or "")
                reward = int(r["price_digi"] or 0)
                completed_at = str(r["created_at"] or "")

                conn2 = db._connect()
                c2 = conn2.cursor()
                c2.execute("SELECT 1 FROM unsub_penalties WHERE task_id=? AND worker_id=?", (task_id, worker_id))
                already = c2.fetchone() is not None
                conn2.close()
                if already:
                    continue

                try:
                    dt = datetime.fromisoformat(completed_at.replace(" ", "T"))
                    if datetime.utcnow() - dt >= timedelta(days=days):
                        continue
                except Exception:
                    pass

                uname = _extract_username_from_tme(url)
                if not uname:
                    continue

                chat_id = f"@{uname}"
                try:
                    member = await bot.get_chat_member(chat_id=chat_id, user_id=worker_id)
                    status = getattr(member, "status", None)
                except Exception:
                    continue

                if status in ("left", "kicked"):
                    ok = db.transfer_digi_allow_negative(from_tg_id=worker_id, to_tg_id=owner_id, amount_digi=reward)
                    if ok:
                        conn3 = db._connect()
                        c3 = conn3.cursor()
                        c3.execute("""
                            INSERT OR IGNORE INTO unsub_penalties (task_id, worker_id, owner_id, amount_digi)
                            VALUES (?, ?, ?, ?)
                        """, (task_id, worker_id, owner_id, reward))
                        conn3.commit()
                        conn3.close()

                        try:
                            await bot.send_message(
                                worker_id,
                                "⛔ <b>Штраф за отписку</b>\n\n"
                                f"Ты отписался от {('канала' if kind=='channel' else 'группы')} раньше чем через {days} дней.\n"
                                f"Списано: <b>{reward} DIGI</b>."
                            )
                        except Exception:
                            pass

                        try:
                            await bot.send_message(
                                owner_id,
                                "✅ <b>Компенсация за отписку</b>\n\n"
                                f"Исполнитель отписался раньше {days} дней.\n"
                                f"Начислено вам: <b>{reward} DIGI</b> (возврат)."
                            )
                        except Exception:
                            pass

            await asyncio.sleep(interval)

        except Exception:
            logging.exception("BG unsub-penalty error")
            await asyncio.sleep(interval)


async def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

    cfg = load_config()

    bot = Bot(
        token=cfg.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode="HTML")
    )

    dp = Dispatcher(storage=MemoryStorage())
    db = Database(cfg.DB_PATH)
    logging.info(f"✅ DB_PATH(cfg) = {cfg.DB_PATH}")
    logging.info(f"✅ DB_PATH(used) = {db.db_path}")

    # DI
    dp["cfg"] = cfg
    dp["db"] = db
    cryptobot = CryptoBotAPI(cfg.CRYPTOBOT_TOKEN)
    dp["cryptobot"] = cryptobot

    # ===== PREMIUM EMOJI (auto-load from your packs) =====
    premium = await PremiumEmoji.from_sticker_sets(
        bot,
        ["sohccw_by_EmojiTitleBot", "sog5ed_by_EmojiTitleBot", "sy1gu7_by_EmojiTitleBot", "sepu9i_by_EmojiTitleBot", "sfxbpi_by_EmojiTitleBot", "s0rve8_by_EmojiTitleBot", "sl63qq_by_EmojiTitleBot", "seud88_by_EmojiTitleBot", "s77hcf_by_EmojiTitleBot"]
    )
    dp["premium"] = premium

    dp.update.middleware(ActivityMiddleware(db))

    # routers
    dp.include_router(start_router)
    dp.include_router(cabinet_router)
    dp.include_router(status_router)
    dp.include_router(topup_router)
    dp.include_router(purchase_router)
    dp.include_router(earn_router)
    dp.include_router(ads_router)
    dp.include_router(referral_router)
    dp.include_router(about_router)
    dp.include_router(statistics_router)
    dp.include_router(withdraw_router)
    dp.include_router(admin_router)
    dp.include_router(send_digi_router)
    dp.include_router(games.router)
    dp.include_router(mining_router)

    # ===== MINI APP SERVER (aiohttp) =====
    # В config должны быть: WEBAPP_HOST, WEBAPP_PORT
    app = create_app(db=db, bot_token=cfg.BOT_TOKEN)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host=getattr(cfg, "WEBAPP_HOST", "0.0.0.0"), port=int(getattr(cfg, "WEBAPP_PORT", 8080)))
    await site.start()
    logging.info(f"✅ MiniApp server started: http://{getattr(cfg, 'WEBAPP_HOST', '0.0.0.0')}:{int(getattr(cfg, 'WEBAPP_PORT', 8080))}/miniapp/")

    # ===== BACKGROUND WORKERS =====
    asyncio.create_task(_bg_auto_approve_manual(bot, db, cfg))
    asyncio.create_task(_bg_check_unsub_penalty(bot, db, cfg))

    logging.info("✅ Digital bot started")
    try:
        await dp.start_polling(bot)
    finally:
        await runner.cleanup()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("Bot stopped.")


