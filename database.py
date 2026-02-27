# database.py
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
import hashlib
import secrets


class Database:
    def __init__(self, db_path: Path):
        self.db_path = str(db_path)
        self._init_db()

    def _connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        # немного быстрее + безопаснее для конкурентных транзакций
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA foreign_keys=ON;")
        return conn

    # ---------------- MIGRATIONS HELPERS ----------------
    @staticmethod
    def _now_iso() -> str:
        return datetime.utcnow().isoformat()

    def _table_cols(self, cur: sqlite3.Cursor, table: str) -> set[str]:
        cur.execute(f"PRAGMA table_info({table})")
        return {r["name"] for r in cur.fetchall()}

    def _ensure_col(self, cur: sqlite3.Cursor, table: str, col: str, ddl: str) -> None:
        cols = self._table_cols(cur, table)
        if col not in cols:
            cur.execute(f"ALTER TABLE {table} ADD COLUMN {ddl}")

    def _init_db(self):
        conn = self._connect()
        cur = conn.cursor()

        # ---------------- BASE TABLES (existing) ----------------
        cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tg_id INTEGER UNIQUE,
            username TEXT,
            balance_digi INTEGER DEFAULT 0,
            total_topup_usdt REAL DEFAULT 0,
            total_spent_digi INTEGER DEFAULT 0,
            referrer_id INTEGER,
            referrals_count INTEGER DEFAULT 0,
            earned_digi INTEGER DEFAULT 0,
            created_at TEXT
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS topups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            amount_usdt REAL,
            amount_digi INTEGER,
            status TEXT,
            invoice_id TEXT,
            created_at TEXT
        )
        """)

        # Старые админ-задания (скрин → pending → approve)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            description TEXT,
            reward_digi INTEGER,
            is_active INTEGER DEFAULT 1,
            created_at TEXT
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS task_submissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            task_id INTEGER,
            screenshot_file_id TEXT,
            status TEXT,
            created_at TEXT
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS ads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            description TEXT,
            link TEXT,
            expires_at TEXT,
            created_at TEXT
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS purchases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            service TEXT,
            amount_digi INTEGER,
            created_at TEXT
        )
        """)

        # ---------------- MARKET TASKS (existing) ----------------
        cur.execute("""
        CREATE TABLE IF NOT EXISTS market_tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_id INTEGER NOT NULL,
            kind TEXT NOT NULL,
            url TEXT NOT NULL,
            title TEXT,
            price_digi INTEGER NOT NULL,
            total_qty INTEGER NOT NULL,
            remaining_qty INTEGER NOT NULL,
            escrow_total INTEGER NOT NULL,
            escrow_remaining INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'active',
            created_at TEXT NOT NULL
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS market_completions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id INTEGER NOT NULL,
            worker_id INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE(task_id, worker_id)
        )
        """)

        # ---------------- NEW: WALLET/PLANS (MIGRATIONS) ----------------
        # users: add usdt balance + plan + vip_until + daily counters
        # --- NEW STATUS SYSTEM (Novichok / Active)
        # --- LEADER STATUS ---
        self._ensure_col(cur, "users", "leader_bonus_given", "leader_bonus_given INTEGER DEFAULT 0")
        self._ensure_col(cur, "users", "status", "status TEXT DEFAULT 'newbie'")
        self._ensure_col(cur, "users", "ref_balance_usdt", "ref_balance_usdt REAL DEFAULT 0")
        self._ensure_col(cur, "users", "tasks_completed_total", "tasks_completed_total INTEGER DEFAULT 0")
        self._ensure_col(cur, "users", "tasks_created_total", "tasks_created_total INTEGER DEFAULT 0")
        self._ensure_col(cur, "users", "usdt_balance", "usdt_balance REAL DEFAULT 0")
        self._ensure_col(cur, "users", "win_balance_usdt", "win_balance_usdt REAL DEFAULT 0")
        self._ensure_col(cur, "users", "balances_merged", "balances_merged INTEGER DEFAULT 0")
        self._ensure_col(cur, "users", "plan", "plan TEXT DEFAULT 'FREE'")
        self._ensure_col(cur, "users", "vip_until", "vip_until TEXT")
        self._ensure_col(cur, "users", "tasks_done_date", "tasks_done_date TEXT")
        self._ensure_col(cur, "users", "tasks_done_count", "tasks_done_count INTEGER DEFAULT 0")
        self._ensure_col(cur, "users", "withdrawn_date", "withdrawn_date TEXT")
        self._ensure_col(cur, "users", "withdrawn_today_usdt", "withdrawn_today_usdt REAL DEFAULT 0")
        # --- after CREATE TABLE users ---
        self._ensure_col(cur, "users", "invited_by", "invited_by INTEGER")
        # market_tasks extra fields
        self._ensure_col(cur, "market_tasks", "instructions", "instructions TEXT")
        self._ensure_col(cur, "market_tasks", "reaction", "reaction TEXT")
        self._ensure_col(cur, "market_completions", "last_check_at", "last_check_at TEXT")
        self._ensure_col(cur, "market_completions", "reversed_at", "reversed_at TEXT")
        self._ensure_col(cur, "market_completions", "reversed_reason", "reversed_reason TEXT")
        self._ensure_col(cur, "users", "signup_bonus_given", "signup_bonus_given INTEGER DEFAULT 0")
        self._ensure_col(cur, "users", "first_name", "first_name TEXT")
        self._ensure_col(cur, "users", "last_seen_at", "last_seen_at TEXT")
        # market_tasks: source post (for views)
        self._ensure_col(cur, "market_tasks", "src_chat_id", "src_chat_id INTEGER")
        self._ensure_col(cur, "market_tasks", "src_message_id", "src_message_id INTEGER")

        cur.execute("""
            UPDATE users
            SET usdt_balance = COALESCE(usdt_balance, 0) + COALESCE(ref_balance_usdt, 0) + COALESCE(win_balance_usdt, 0),
                ref_balance_usdt = 0,
                win_balance_usdt = 0,
                balances_merged = 1
            WHERE COALESCE(balances_merged, 0) = 0
        """)
        # --- link keys: one-time key with TTL
        cur.execute("""
        CREATE TABLE IF NOT EXISTS link_keys (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key_hash TEXT UNIQUE NOT NULL,
            user_id INTEGER NOT NULL,
            expires_at TEXT NOT NULL,
            used_at TEXT,
            created_at TEXT NOT NULL
        )
        """)

        # --- bot links: which bots are linked to user wallet
        cur.execute("""
        CREATE TABLE IF NOT EXISTS bot_links (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            bot_id TEXT NOT NULL,
            linked_at TEXT NOT NULL,
            revoked_at TEXT,
            UNIQUE(user_id, bot_id)
        )
        """)

        # --- transactions: USDT charges by bots/services
        cur.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            bot_id TEXT NOT NULL,
            amount_usdt REAL NOT NULL,
            reason TEXT,
            idempotency_key TEXT NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE(user_id, bot_id, idempotency_key)
        )
        """)
        # --- migrate: saved forwarded posts for views tasks ---
        try:
            self.market_tasks_migrate_posts()
        except Exception:
            pass

        conn.commit()
        conn.close()

    # =========================================================
    # =================== USERS (existing) ====================
    # =========================================================
    def get_referrals_joined_count(self, tg_id: int) -> int:
        conn = self._connect()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) AS cnt FROM users WHERE invited_by = ?", (int(tg_id),))
        cnt = int(cur.fetchone()["cnt"] or 0)
        conn.close()
        return cnt

    def get_user(self, tg_id: int) -> Optional[sqlite3.Row]:
        conn = self._connect()
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE tg_id = ?", (tg_id,))
        user = cur.fetchone()
        conn.close()
        return user

    def create_user(self, tg_id: int, username: str, referrer_id: Optional[int], first_name: Optional[str] = None):
        conn = self._connect()
        cur = conn.cursor()
        now = self._now_iso()

        cur.execute("""
            INSERT OR IGNORE INTO users (
                tg_id,
                username,
                first_name,
                referrer_id,
                invited_by,
                balance_digi,
                earned_digi,
                signup_bonus_given,
                created_at,
                last_seen_at
            )
            VALUES (?, ?, ?, ?, ?, 0, 0, 0, ?, ?)
        """, (tg_id, username, first_name, referrer_id, referrer_id, now, now))

        conn.commit()
        conn.close()

    def update_username(self, tg_id: int, username: str):
        conn = self._connect()
        cur = conn.cursor()
        cur.execute("UPDATE users SET username=? WHERE tg_id=?",
                    (username, tg_id))
        conn.commit()
        conn.close()

    def touch_user(self, tg_id: int, username: str | None = None, first_name: str | None = None) -> None:
        conn = self._connect()
        cur = conn.cursor()

        cur.execute("""
            UPDATE users
            SET last_seen_at = datetime('now'),
                username = COALESCE(?, username),
                first_name = COALESCE(?, first_name)
            WHERE tg_id = ?
        """, (username, first_name, int(tg_id)))

        conn.commit()
        conn.close()

    def update_profile(self, tg_id: int, username: Optional[str], first_name: Optional[str]):
        conn = self._connect()
        cur = conn.cursor()
        cur.execute("""
              UPDATE users
              SET username = COALESCE(?, username),
                  first_name = COALESCE(?, first_name)
              WHERE tg_id=?
          """, (username, first_name, tg_id))
        conn.commit()
        conn.close()

    # ---------------- DIGI balance (existing) ----------------
    def add_balance(self, tg_id: int, amount_digi: int):
        conn = self._connect()
        cur = conn.cursor()
        cur.execute("""
        UPDATE users
        SET balance_digi = balance_digi + ?,
            earned_digi = earned_digi + ?
        WHERE tg_id = ?
        """, (amount_digi, amount_digi, tg_id))
        conn.commit()
        conn.close()

    def give_signup_bonus_once(self, tg_id: int, amount_digi: int) -> bool:
        """
        Начисляет бонус один раз на аккаунт.
        Возвращает True если начислило, False если уже было.
        """
        conn = self._connect()
        cur = conn.cursor()
        try:
            cur.execute("BEGIN IMMEDIATE")
            cur.execute("SELECT signup_bonus_given FROM users WHERE tg_id=?", (int(tg_id),))
            row = cur.fetchone()
            if not row:
                conn.rollback()
                return False

            if int(row["signup_bonus_given"] or 0) == 1:
                conn.rollback()
                return False

            cur.execute("""
                 UPDATE users
                 SET balance_digi = balance_digi + ?,
                     earned_digi = earned_digi + ?,
                     signup_bonus_given = 1
                 WHERE tg_id = ?
             """, (int(amount_digi), int(amount_digi), int(tg_id)))

            conn.commit()
            return True
        except Exception:
            conn.rollback()
            return False
        finally:
            conn.close()

    def spend_balance(self, tg_id: int, amount_digi: int) -> bool:
        conn = self._connect()
        cur = conn.cursor()

        cur.execute("SELECT balance_digi FROM users WHERE tg_id=?", (tg_id,))
        row = cur.fetchone()
        if not row or row["balance_digi"] < amount_digi:
            conn.close()
            return False

        cur.execute("""
        UPDATE users
        SET balance_digi = balance_digi - ?,
            total_spent_digi = total_spent_digi + ?
        WHERE tg_id = ?
        """, (amount_digi, amount_digi, tg_id))

        conn.commit()
        conn.close()
        return True

    def transfer_digi_allow_negative(self, from_tg_id: int, to_tg_id: int, amount_digi: int) -> bool:
        """
        Перевод DIGI от одного пользователя к другому.
        ВАЖНО: у отправителя баланс может уйти в минус.
        """
        amount_digi = int(amount_digi)
        if amount_digi <= 0:
            return False

        conn = self._connect()
        cur = conn.cursor()
        try:
            cur.execute("BEGIN IMMEDIATE")

            # списываем у исполнителя (может уйти в минус)
            cur.execute("""
                UPDATE users
                SET balance_digi = balance_digi - ?
                WHERE tg_id = ?
            """, (amount_digi, int(from_tg_id)))

            # зачисляем владельцу
            cur.execute("""
                UPDATE users
                SET balance_digi = balance_digi + ?
                WHERE tg_id = ?
            """, (amount_digi, int(to_tg_id)))

            conn.commit()
            return True
        except Exception:
            conn.rollback()
            return False
        finally:
            conn.close()

    # ---------------- USDT balance (new) ----------------
    def get_balances(self, tg_id: int) -> Tuple[float, int]:
        """
        Returns: (usdt_balance, digi_balance)
        """
        conn = self._connect()
        cur = conn.cursor()
        cur.execute("SELECT usdt_balance, balance_digi FROM users WHERE tg_id=?", (int(tg_id),))
        row = cur.fetchone()
        conn.close()
        if not row:
            return 0.0, 0
        return float(row["usdt_balance"] or 0.0), int(row["balance_digi"] or 0)

    def lock_status_deposit(self, tg_id: int, deposit_usdt: float = 5.0) -> tuple[bool, str]:
        """
        Замораживает депозит статуса (usdt_locked) из общего баланса.
        ВАЖНО: статус НЕ активирует. Статус активирует try_activate_user() при выполнении условий.
        """
        deposit_usdt = float(deposit_usdt)

        conn = self._connect()
        cur = conn.cursor()
        try:
            cur.execute("BEGIN IMMEDIATE")

            cur.execute("SELECT usdt_balance, usdt_locked FROM users WHERE tg_id=?", (int(tg_id),))
            row = cur.fetchone()
            if not row:
                conn.rollback()
                return False, "Пользователь не найден"

            usdt_bal = float(row["usdt_balance"] or 0.0)
            locked = float(row["usdt_locked"] or 0.0)

            # уже заморожено (или больше) — ничего не делаем
            if locked + 1e-9 >= deposit_usdt:
                conn.rollback()
                return False, "Депозит уже заморожен"

            available = usdt_bal - locked
            if available + 1e-9 < deposit_usdt:
                conn.rollback()
                return False, f"Недостаточно USDT. Нужно {deposit_usdt:.2f} USDT доступно"

            # просто ставим locked = deposit_usdt (5)
            cur.execute("""
                UPDATE users
                SET usdt_locked = ?
                WHERE tg_id = ?
            """, (deposit_usdt, int(tg_id)))

            conn.commit()
            return True, "✅ Депозит заморожен. Статус активируется после 7/7 + 7/7."
        except Exception as e:
            conn.rollback()
            return False, f"Ошибка: {e}"
        finally:
            conn.close()

    def add_usdt(self, tg_id: int, amount_usdt: float) -> None:
        conn = self._connect()
        cur = conn.cursor()
        cur.execute("""
            UPDATE users
            SET usdt_balance = usdt_balance + ?,
                total_topup_usdt = total_topup_usdt + ?
            WHERE tg_id = ?
        """, (float(amount_usdt), float(amount_usdt), int(tg_id)))
        conn.commit()
        conn.close()

        # ✅ новая рефералка: активный реферал = пополнение >= X USDT
        # значения тут дефолтные, если хочешь — можно передавать из cfg в handler topup.py
        try:
            self.process_referral_on_topup(
                referred_tg_id=int(tg_id),
                active_min_topup_usdt=5.0,
                reward_free_digi=5000,
                reward_vip_digi=10000
            )
        except Exception:
            pass

    def spend_usdt(self, tg_id: int, amount_usdt: float) -> bool:
        """
        Простое списание USDT (без idempotency). Для внешних ботов используй charge_usdt().
        """
        conn = self._connect()
        cur = conn.cursor()
        try:
            cur.execute("BEGIN IMMEDIATE")
            cur.execute("SELECT usdt_balance FROM users WHERE tg_id=?", (int(tg_id),))
            row = cur.fetchone()
            bal = float(row["usdt_balance"] or 0.0) if row else 0.0
            if bal + 1e-9 < float(amount_usdt):
                conn.rollback()
                return False

            cur.execute("""
                UPDATE users
                SET usdt_balance = usdt_balance - ?
                WHERE tg_id = ?
            """, (float(amount_usdt), int(tg_id)))

            conn.commit()
            return True
        except Exception:
            conn.rollback()
            return False
        finally:
            conn.close()

    def add_topup_stats(self, tg_id: int, amount_usdt: float):
        # оставляю для совместимости — но теперь add_usdt() делает оба счётчика
        conn = self._connect()
        cur = conn.cursor()
        cur.execute("""
        UPDATE users
        SET total_topup_usdt = total_topup_usdt + ?
        WHERE tg_id = ?
        """, (amount_usdt, tg_id))
        conn.commit()
        conn.close()

    def get_stats(self):
        conn = self._connect()
        cur = conn.cursor()

        cur.execute("SELECT COUNT(*) as count FROM users")
        users = int(cur.fetchone()["count"] or 0)

        cur.execute("SELECT SUM(balance_digi) as total FROM users")
        total_balance = cur.fetchone()["total"] or 0

        cur.execute("""
            SELECT COUNT(*) AS cnt
            FROM users
            WHERE last_seen_at IS NOT NULL
              AND datetime(last_seen_at) >= datetime('now', '-24 hours')
        """)
        active_users = int(cur.fetchone()["cnt"] or 0)

        conn.close()
        return {
            "users": users,
            "active_users": active_users,
            "total_balance": total_balance
        }

    # =========================================================
    # ====================== PLANS (new) ======================
    # =========================================================

    def set_vip(self, tg_id: int, vip_until_iso: str) -> None:
        conn = self._connect()
        cur = conn.cursor()
        cur.execute("""
            UPDATE users
            SET plan='VIP', vip_until=?
            WHERE tg_id=?
        """, (vip_until_iso, int(tg_id)))
        conn.commit()
        conn.close()

    def set_free(self, tg_id: int) -> None:
        conn = self._connect()
        cur = conn.cursor()
        cur.execute("""
            UPDATE users
            SET plan='FREE', vip_until=NULL
            WHERE tg_id=?
        """, (int(tg_id),))
        conn.commit()
        conn.close()



    # =========================================================
    # =================== DAILY LIMITS (new) ==================
    # =========================================================

    def _today_key(self) -> str:
        # YYYY-MM-DD UTC
        return datetime.utcnow().date().isoformat()

    def inc_tasks_done_today(self, tg_id: int, inc: int = 1) -> int:
        """
        Увеличивает счётчик выполненных заданий сегодня.
        Возвращает новое значение.
        """
        conn = self._connect()
        cur = conn.cursor()
        today = self._today_key()
        try:
            cur.execute("BEGIN IMMEDIATE")
            cur.execute("SELECT tasks_done_date, tasks_done_count FROM users WHERE tg_id=?", (int(tg_id),))
            row = cur.fetchone()
            if not row:
                conn.rollback()
                return 0
            if (row["tasks_done_date"] or "") != today:
                cur.execute("""
                    UPDATE users
                    SET tasks_done_date=?, tasks_done_count=?
                    WHERE tg_id=?
                """, (today, int(inc), int(tg_id)))
                conn.commit()
                return int(inc)

            new_cnt = int(row["tasks_done_count"] or 0) + int(inc)
            cur.execute("""
                UPDATE users
                SET tasks_done_count=?
                WHERE tg_id=?
            """, (new_cnt, int(tg_id)))
            conn.commit()
            return new_cnt
        except Exception:
            conn.rollback()
            return 0
        finally:
            conn.close()

    def get_tasks_done_today(self, tg_id: int) -> int:
        conn = self._connect()
        cur = conn.cursor()
        today = self._today_key()
        cur.execute("SELECT tasks_done_date, tasks_done_count FROM users WHERE tg_id=?", (int(tg_id),))
        row = cur.fetchone()
        conn.close()
        if not row:
            return 0
        if (row["tasks_done_date"] or "") != today:
            return 0
        return int(row["tasks_done_count"] or 0)

    def can_withdraw_usdt(self, tg_id: int, amount: float, min_day: float, max_day: float) -> Tuple[bool, str]:
        """
        Проверка дневного лимита вывода. План VIP проверяй отдельно.
        Лимит: min_day..max_day в сутки.
        """
        if amount < float(min_day) - 1e-9:
            return False, f"Мінімальний вивід: {min_day} USDT"
        conn = self._connect()
        cur = conn.cursor()
        today = self._today_key()
        cur.execute("SELECT withdrawn_date, withdrawn_today_usdt FROM users WHERE tg_id=?", (int(tg_id),))
        row = cur.fetchone()
        conn.close()
        if not row:
            return False, "Користувача не знайдено"
        used_today = 0.0
        if (row["withdrawn_date"] or "") == today:
            used_today = float(row["withdrawn_today_usdt"] or 0.0)
        if used_today + float(amount) > float(max_day) + 1e-9:
            return False, f"Ліміт виводу на сьогодні: {max_day} USDT (вже: {used_today:.2f})"
        return True, "OK"

    def record_withdraw_usdt(self, tg_id: int, amount: float) -> bool:
        """
        Записывает 'выведено сегодня' (не делает реальную выплату).
        В handlers надо сначала списать usdt_balance, потом вызвать это.
        """
        conn = self._connect()
        cur = conn.cursor()
        today = self._today_key()
        try:
            cur.execute("BEGIN IMMEDIATE")
            cur.execute("SELECT withdrawn_date, withdrawn_today_usdt FROM users WHERE tg_id=?", (int(tg_id),))
            row = cur.fetchone()
            if not row:
                conn.rollback()
                return False
            if (row["withdrawn_date"] or "") != today:
                cur.execute("""
                    UPDATE users
                    SET withdrawn_date=?, withdrawn_today_usdt=?
                    WHERE tg_id=?
                """, (today, float(amount), int(tg_id)))
                conn.commit()
                return True

            new_val = float(row["withdrawn_today_usdt"] or 0.0) + float(amount)
            cur.execute("""
                UPDATE users
                SET withdrawn_today_usdt=?
                WHERE tg_id=?
            """, (new_val, int(tg_id)))
            conn.commit()
            return True
        except Exception:
            conn.rollback()
            return False
        finally:
            conn.close()

    # =========================================================
    # ============== DIGI -> USDT CONVERSION (new) ============
    # =========================================================

    def convert_digi_to_usdt(self, tg_id: int, digi_amount: int, digi_per_1_usdt: int) -> Tuple[bool, str, float]:
        """
        Конвертация: списать DIGI и зачислить USDT.
        digi_per_1_usdt: например 5000
        Возвращает (ok, msg, new_usdt_balance)
        """
        digi_amount = int(digi_amount)
        if digi_amount <= 0:
            return False, "Сума має бути > 0", 0.0
        if digi_per_1_usdt <= 0:
            return False, "Невірний курс", 0.0

        usdt_add = digi_amount / float(digi_per_1_usdt)

        conn = self._connect()
        cur = conn.cursor()
        try:
            cur.execute("BEGIN IMMEDIATE")
            cur.execute("SELECT balance_digi, usdt_balance FROM users WHERE tg_id=?", (int(tg_id),))
            row = cur.fetchone()
            if not row:
                conn.rollback()
                return False, "Користувача не знайдено", 0.0
            digi_bal = int(row["balance_digi"] or 0)
            if digi_bal < digi_amount:
                conn.rollback()
                return False, "Недостатньо DIGI", float(row["usdt_balance"] or 0.0)

            cur.execute("""
                UPDATE users
                SET balance_digi = balance_digi - ?,
                    usdt_balance = usdt_balance + ?
                WHERE tg_id = ?
            """, (int(digi_amount), float(usdt_add), int(tg_id)))

            cur.execute("SELECT usdt_balance FROM users WHERE tg_id=?", (int(tg_id),))
            new_bal = float(cur.fetchone()["usdt_balance"] or 0.0)
            conn.commit()
            return True, f"✅ Конвертовано: {digi_amount} DIGI → {usdt_add:.6f} USDT", new_bal
        except Exception as e:
            conn.rollback()
            return False, f"❌ Помилка: {e}", 0.0
        finally:
            conn.close()

    def convert_usdt_to_digi(self, tg_id: int, usdt_amount: float, digi_per_1_usdt: int) -> Tuple[bool, str, int]:
        """
        Конвертация: списать USDT и зачислить DIGI.
        Курс: 1 USDT = digi_per_1_usdt DIGI (например 5000)
        Возвращает (ok, msg, new_digi_balance)
        """
        try:
            usdt_amount = float(usdt_amount)
        except Exception:
            return False, "Неверная сумма", 0

        if usdt_amount <= 0:
            return False, "Сумма должна быть > 0", 0
        if digi_per_1_usdt <= 0:
            return False, "Неверный курс", 0

        # DIGI целые. Округляем вниз, чтобы не печатать DIGI из воздуха.
        digi_add = int(usdt_amount * float(digi_per_1_usdt))
        if digi_add <= 0:
            return False, "Слишком маленькая сумма", 0

        conn = self._connect()
        cur = conn.cursor()
        try:
            cur.execute("BEGIN IMMEDIATE")
            cur.execute("SELECT usdt_balance, balance_digi FROM users WHERE tg_id=?", (int(tg_id),))
            row = cur.fetchone()
            if not row:
                conn.rollback()
                return False, "Пользователь не найден", 0

            usdt_bal = float(row["usdt_balance"] or 0.0)
            if usdt_bal + 1e-9 < usdt_amount:
                conn.rollback()
                return False, "Недостаточно USDT", int(row["balance_digi"] or 0)

            cur.execute("""
                 UPDATE users
                 SET usdt_balance = usdt_balance - ?,
                     balance_digi = balance_digi + ?,
                     earned_digi = earned_digi + ?
                 WHERE tg_id = ?
             """, (float(usdt_amount), int(digi_add), int(digi_add), int(tg_id)))

            cur.execute("SELECT balance_digi FROM users WHERE tg_id=?", (int(tg_id),))
            new_digi = int(cur.fetchone()["balance_digi"] or 0)

            conn.commit()
            return True, f"✅ Конвертировано: {usdt_amount:.6f} USDT → {digi_add} DIGI", new_digi
        except Exception as e:
            conn.rollback()
            return False, f"❌ Ошибка: {e}", 0
        finally:
            conn.close()

    # =========================================================
    # ===================== WALLET API (new) ==================
    # =========================================================

    @staticmethod
    def _hash_key(raw_key: str) -> str:
        return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()

    def create_link_key(self, tg_id: int, ttl_seconds: int = 300) -> Tuple[str, str]:
        """
        Создаёт одноразовый ключ (raw) на ttl_seconds.
        Возвращает (raw_key, expires_at_iso)
        """
        raw = secrets.token_urlsafe(32)
        key_hash = self._hash_key(raw)
        expires_at = (datetime.utcnow() + timedelta(seconds=int(ttl_seconds))).isoformat()

        conn = self._connect()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO link_keys (key_hash, user_id, expires_at, used_at, created_at)
            VALUES (?, ?, ?, NULL, ?)
        """, (key_hash, int(tg_id), expires_at, self._now_iso()))
        conn.commit()
        conn.close()
        return raw, expires_at

    def redeem_link_key(self, raw_key: str, tg_id: int, bot_id: str) -> bool:
        """
        Погашает ключ (one-time), проверяет:
          - ключ не использован
          - не истёк
          - принадлежит tg_id
        Затем создаёт/обновляет bot_links.
        """
        bot_id = (bot_id or "").strip()
        if not bot_id:
            return False

        key_hash = self._hash_key(raw_key)
        now = self._now_iso()

        conn = self._connect()
        cur = conn.cursor()
        try:
            cur.execute("BEGIN IMMEDIATE")

            cur.execute("""
                SELECT id, user_id, expires_at, used_at
                FROM link_keys
                WHERE key_hash=?
            """, (key_hash,))
            row = cur.fetchone()
            if not row:
                conn.rollback()
                return False
            if row["used_at"] is not None:
                conn.rollback()
                return False
            if int(row["user_id"]) != int(tg_id):
                conn.rollback()
                return False

            try:
                if datetime.fromisoformat(row["expires_at"]) <= datetime.utcnow():
                    conn.rollback()
                    return False
            except Exception:
                conn.rollback()
                return False

            # mark used
            cur.execute("UPDATE link_keys SET used_at=? WHERE id=?", (now, int(row["id"])))

            # upsert bot link
            cur.execute("""
                INSERT INTO bot_links (user_id, bot_id, linked_at, revoked_at)
                VALUES (?, ?, ?, NULL)
                ON CONFLICT(user_id, bot_id) DO UPDATE SET
                    linked_at=excluded.linked_at,
                    revoked_at=NULL
            """, (int(tg_id), bot_id, now))

            conn.commit()
            return True
        except Exception:
            conn.rollback()
            return False
        finally:
            conn.close()

    def get_usdt_balance(self, tg_id: int) -> float:
        conn = self._connect()
        cur = conn.cursor()
        cur.execute("SELECT usdt_balance FROM users WHERE tg_id=?", (int(tg_id),))
        row = cur.fetchone()
        conn.close()
        return float(row["usdt_balance"] or 0.0) if row else 0.0

    def get_win_balance(self, tg_id: int) -> float:
        # win-баланса больше нет
        return 0.0

    def add_win_usdt(self, tg_id: int, amount_usdt: float) -> None:
        conn = self._connect()
        cur = conn.cursor()
        cur.execute("""
            UPDATE users
            SET usdt_balance = usdt_balance + ?
            WHERE tg_id = ?
        """, (float(amount_usdt), int(tg_id)))
        conn.commit()
        conn.close()

    def play_game_usdt(self, tg_id: int, bet_usdt: float, win_usdt: float, game: str, meta: str = "") -> tuple[
        bool, float, str]:
        """
        АТОМАРНО:
          - проверяет usdt_balance >= bet_usdt
          - списывает bet_usdt с usdt_balance
          - начисляет win_usdt на win_balance_usdt
        Возвращает (ok, new_usdt_balance, message)
        """
        try:
            bet = float(bet_usdt)
            win = float(win_usdt)
        except Exception:
            return False, self.get_usdt_balance(tg_id), "bad_amount"

        if bet <= 0:
            return False, self.get_usdt_balance(tg_id), "bet_must_be_positive"
        if win < 0:
            return False, self.get_usdt_balance(tg_id), "win_must_be_non_negative"

        conn = self._connect()
        cur = conn.cursor()
        try:
            cur.execute("BEGIN IMMEDIATE")

            cur.execute("SELECT usdt_balance FROM users WHERE tg_id=?", (int(tg_id),))
            row = cur.fetchone()
            if not row:
                conn.rollback()
                return False, 0.0, "user_not_found"

            bal = float(row["usdt_balance"] or 0.0)
            if bal + 1e-9 < bet:
                conn.rollback()
                return False, bal, "insufficient_usdt"

            # списываем ставку + начисляем выигрыш в win_balance_usdt
            cur.execute("""
                 UPDATE users
                 SET usdt_balance = usdt_balance - ? + ?
                 WHERE tg_id = ?
             """, (bet, win, int(tg_id)))

            cur.execute("SELECT usdt_balance FROM users WHERE tg_id=?", (int(tg_id),))
            new_bal = float(cur.fetchone()["usdt_balance"] or 0.0)

            conn.commit()
            return True, new_bal, "ok"
        except Exception as e:
            conn.rollback()
            return False, self.get_usdt_balance(tg_id), f"error:{e}"
        finally:
            conn.close()

    def charge_usdt(
        self,
        tg_id: int,
        bot_id: str,
        amount_usdt: float,
        reason: str,
        idempotency_key: str
    ) -> Tuple[bool, float, str]:
        """
        АТОМАРНО:
          - проверяет idempotency (user_id, bot_id, idempotency_key)
          - не допускает минус
          - списывает usdt_balance
          - пишет transactions
        Возвращает (ok, new_balance, message)
        """
        bot_id = (bot_id or "").strip()
        idem = (idempotency_key or "").strip()
        if not bot_id or not idem:
            return False, self.get_usdt_balance(tg_id), "missing bot_id/idempotency_key"
        if float(amount_usdt) <= 0:
            return False, self.get_usdt_balance(tg_id), "amount must be > 0"

        conn = self._connect()
        cur = conn.cursor()
        try:
            cur.execute("BEGIN IMMEDIATE")

            # already charged?
            cur.execute("""
                SELECT id, created_at
                FROM transactions
                WHERE user_id=? AND bot_id=? AND idempotency_key=?
            """, (int(tg_id), bot_id, idem))
            tx = cur.fetchone()
            if tx:
                # идемпотентно: считаем ОК и возвращаем текущий баланс
                cur.execute("SELECT usdt_balance FROM users WHERE tg_id=?", (int(tg_id),))
                bal = float(cur.fetchone()["usdt_balance"] or 0.0)
                conn.commit()
                return True, bal, "idempotent_ok"

            cur.execute("SELECT usdt_balance FROM users WHERE tg_id=?", (int(tg_id),))
            row = cur.fetchone()
            if not row:
                conn.rollback()
                return False, 0.0, "user not found"

            bal = float(row["usdt_balance"] or 0.0)
            if bal + 1e-9 < float(amount_usdt):
                conn.rollback()
                return False, bal, "insufficient_usdt"

            # write tx
            cur.execute("""
                INSERT INTO transactions (user_id, bot_id, amount_usdt, reason, idempotency_key, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (int(tg_id), bot_id, float(amount_usdt), reason, idem, self._now_iso()))

            # charge
            cur.execute("""
                UPDATE users
                SET usdt_balance = usdt_balance - ?
                WHERE tg_id = ?
            """, (float(amount_usdt), int(tg_id)))

            cur.execute("SELECT usdt_balance FROM users WHERE tg_id=?", (int(tg_id),))
            new_bal = float(cur.fetchone()["usdt_balance"] or 0.0)
            conn.commit()
            return True, new_bal, "charged"
        except Exception as e:
            conn.rollback()
            return False, self.get_usdt_balance(tg_id), f"error: {e}"
        finally:
            conn.close()

    # =========================================================
    # ================= REFERRALS (existing) ==================
    # =========================================================

    def process_referral_if_ready(
        self,
        tg_id: int,
        reward_digi: int,
        min_earned: int,
        min_hours: int
    ):
        """
        СТАРАЯ ЛОГИКА. Оставляю как есть для совместимости.
        Потом в handlers/referral.py переведём на "активный реферал = пополнение >= 5 USDT".
        """
        conn = self._connect()
        cur = conn.cursor()

        cur.execute("SELECT * FROM users WHERE tg_id=?", (tg_id,))
        user = cur.fetchone()
        if not user:
            conn.close()
            return

        if not user["referrer_id"]:
            conn.close()
            return

        created = datetime.fromisoformat(user["created_at"])
        hours_passed = datetime.utcnow() - created

        if (
            int(user["earned_digi"] or 0) >= int(min_earned) and
            hours_passed >= timedelta(hours=int(min_hours))
        ):
            referrer_id = int(user["referrer_id"])

            cur.execute("""
            UPDATE users
            SET balance_digi = balance_digi + ?,
                referrals_count = referrals_count + 1
            WHERE tg_id = ?
            """, (int(reward_digi), referrer_id))

            # чтобы не начислять второй раз
            cur.execute("""
            UPDATE users
            SET referrer_id = NULL
            WHERE tg_id = ?
            """, (tg_id,))

            conn.commit()

        conn.close()

    def process_referral_on_topup(
            self,
            referred_tg_id: int,
            active_min_topup_usdt: float,
            reward_free_digi: int,
            reward_vip_digi: int
    ) -> Tuple[bool, str]:
        """
        Новая логика:
        - реферал считается активным, если total_topup_usdt реферала >= active_min_topup_usdt
        - начисляем рефереру DIGI 1 раз
        - награда зависит от тарифа реферера: FREE/VIP
        """
        conn = self._connect()
        cur = conn.cursor()
        try:
            cur.execute("BEGIN IMMEDIATE")

            cur.execute("SELECT tg_id, referrer_id, usdt_locked FROM users WHERE tg_id=?",
                        (int(referred_tg_id),))
            u = cur.fetchone()
            if not u:
                conn.rollback()
                return False, "user not found"

            referrer_id = u["referrer_id"]
            if not referrer_id:
                conn.rollback()
                return False, "no referrer"

            total_topup = float(u["total_topup_usdt"] or 0.0)
            if total_topup + 1e-9 < float(active_min_topup_usdt):
                conn.rollback()
                return False, f"not active yet: {total_topup:.2f} < {active_min_topup_usdt:.2f}"

            # определяем награду по тарифу реферера
            reward = int(reward_vip_digi) if self.is_vip(int(referrer_id)) else int(reward_free_digi)

            cur.execute("""
                UPDATE users
                SET balance_digi = balance_digi + ?,
                    referrals_count = referrals_count + 1,
                    dep_withdraw_blocked = 1
                WHERE tg_id = ?
            """, (int(reward), int(referrer_id)))

            # чтобы не начислять второй раз — очищаем referrer_id у реферала
            cur.execute("UPDATE users SET referrer_id=NULL WHERE tg_id=?", (int(referred_tg_id),))

            conn.commit()
            return True, f"referral rewarded: +{reward} DIGI"
        except Exception as e:
            conn.rollback()
            return False, f"error: {e}"
        finally:
            conn.close()

    # =========================================================
    # ================= OLD TASKS (ADMIN) =====================
    # =========================================================

    def get_tasks(self) -> List[sqlite3.Row]:
        conn = self._connect()
        cur = conn.cursor()
        cur.execute("SELECT * FROM tasks WHERE is_active=1")
        rows = cur.fetchall()
        conn.close()
        return rows

    def add_task(self, title: str, description: str, reward: int):
        conn = self._connect()
        cur = conn.cursor()
        cur.execute("""
        INSERT INTO tasks (title, description, reward_digi, created_at)
        VALUES (?, ?, ?, ?)
        """, (title, description, reward, datetime.utcnow().isoformat()))
        conn.commit()
        conn.close()

    def delete_task(self, task_id: int):
        conn = self._connect()
        cur = conn.cursor()
        cur.execute("DELETE FROM tasks WHERE id=?", (task_id,))
        conn.commit()
        conn.close()

    def add_task_submission(self, user_id: int, task_id: int, file_id: str):
        conn = self._connect()
        cur = conn.cursor()
        cur.execute("""
        INSERT INTO task_submissions (user_id, task_id, screenshot_file_id, status, created_at)
        VALUES (?, ?, ?, 'pending', ?)
        """, (user_id, task_id, file_id, datetime.utcnow().isoformat()))
        conn.commit()
        conn.close()

    # =========================================================
    # ========================= ADS ===========================
    # =========================================================

    def add_ad(self, user_id: int, description: str, link: str, days: int):
        conn = self._connect()
        cur = conn.cursor()

        expires = datetime.utcnow() + timedelta(days=days)

        cur.execute("""
        INSERT INTO ads (user_id, description, link, expires_at, created_at)
        VALUES (?, ?, ?, ?, ?)
        """, (
            user_id,
            description,
            link,
            expires.isoformat(),
            datetime.utcnow().isoformat()
        ))

        conn.commit()
        conn.close()

    def get_active_ads(self) -> List[sqlite3.Row]:
        conn = self._connect()
        cur = conn.cursor()

        now = datetime.utcnow().isoformat()
        cur.execute("""
        SELECT * FROM ads
        WHERE expires_at > ?
        ORDER BY created_at DESC
        """, (now,))

        rows = cur.fetchall()
        conn.close()
        return rows

    # =========================================================
    # ======================= PURCHASES =======================
    # =========================================================

    def add_purchase(self, user_id: int, service: str, amount: int):
        conn = self._connect()
        cur = conn.cursor()
        cur.execute("""
        INSERT INTO purchases (user_id, service, amount_digi, created_at)
        VALUES (?, ?, ?, ?)
        """, (user_id, service, amount, datetime.utcnow().isoformat()))
        conn.commit()
        conn.close()

    # =========================================================
    # =============== MARKET TASKS API (existing) ==============
    # =========================================================

    def market_list_my_active_tasks(self, owner_id: int, limit: int = 50):
        conn = self._connect()
        cur = conn.cursor()
        cur.execute("""
            SELECT *
            FROM market_tasks
            WHERE owner_id = ?
              AND status = 'active'
              AND remaining_qty > 0
            ORDER BY id DESC
            LIMIT ?
        """, (int(owner_id), int(limit)))
        rows = cur.fetchall()
        conn.close()
        return rows

    def market_counts_for_user(self, user_id: int) -> dict:
        conn = self._connect()
        cur = conn.cursor()

        kinds = ["channel", "group", "views", "bot", "react"]
        out = {k: 0 for k in kinds}

        for k in kinds:
            cur.execute("""
                SELECT COUNT(*) AS cnt
                FROM market_tasks mt
                WHERE mt.kind = ?
                  AND mt.status = 'active'
                  AND mt.remaining_qty > 0
                  AND mt.owner_id != ?
                  AND NOT EXISTS (
                    SELECT 1 FROM market_completions mc
                    WHERE mc.task_id = mt.id AND mc.worker_id = ? AND mc.reversed_at IS NULL
                  )
            """, (k, user_id, user_id))
            out[k] = int(cur.fetchone()["cnt"])

        conn.close()
        return out

    def market_count_tasks_for_user(self, kind: str, user_id: int) -> int:
        kind = kind.strip().lower()
        conn = self._connect()
        cur = conn.cursor()
        cur.execute("""
            SELECT COUNT(*) AS cnt
            FROM market_tasks mt
            WHERE mt.kind = ?
              AND mt.status = 'active'
              AND mt.remaining_qty > 0
              AND mt.owner_id != ?
              AND NOT EXISTS (
                SELECT 1 FROM market_completions mc
                WHERE mc.task_id = mt.id AND mc.worker_id = ? AND mc.reversed_at IS NULL
              )
        """, (kind, user_id, user_id))
        cnt = int(cur.fetchone()["cnt"])
        conn.close()
        return cnt

    def market_list_tasks_for_user_paged(self, kind: str, user_id: int, limit: int = 5, offset: int = 0):
        kind = kind.strip().lower()
        conn = self._connect()
        cur = conn.cursor()
        cur.execute("""
            SELECT mt.*
            FROM market_tasks mt
            WHERE mt.kind = ?
              AND mt.status = 'active'
              AND mt.remaining_qty > 0
              AND mt.owner_id != ?
              AND NOT EXISTS (
                SELECT 1 FROM market_completions mc
                WHERE mc.task_id = mt.id AND mc.worker_id = ? AND mc.reversed_at IS NULL
              )
            ORDER BY mt.id DESC
            LIMIT ? OFFSET ?
        """, (kind, user_id, user_id, int(limit), int(offset)))
        rows = cur.fetchall()
        conn.close()
        return rows

    def market_counts(self) -> Dict[str, int]:
        conn = self._connect()
        cur = conn.cursor()
        cur.execute("""
            SELECT kind, COUNT(*) as cnt
            FROM market_tasks
            WHERE status='active' AND remaining_qty > 0
            GROUP BY kind
        """)
        rows = cur.fetchall()
        conn.close()

        out = {"channel": 0, "group": 0, "views": 0, "bot": 0, "react": 0}
        for r in rows:
            out[r["kind"]] = int(r["cnt"])
        return out

    def market_create_task(
                self,
                owner_id: int,
                kind: str,
                url: str,
                price_digi: int,
                total_qty: int,
                title: Optional[str] = None,
                instructions: Optional[str] = None,
                reaction: Optional[str] = None,
                src_chat_id: Optional[int] = None,
                src_message_id: Optional[int] = None,
        ) -> Tuple[bool, str, Optional[int]]:
        kind = (kind or "").strip().lower()
        if kind not in ("channel", "group", "views", "bot", "react"):
            return False, "Неверный тип задания", None

        url = (url or "").strip()

        if int(price_digi) <= 0 or int(total_qty) <= 0:
            return False, "Цена и количество должны быть > 0", None

        # нормализация доп. полей
        title = (title or "").strip()
        title = title[:120] if title else None

        instructions = (instructions or "").strip()
        instructions = instructions[:800] if instructions else None

        reaction = (reaction or "").strip()
        reaction = reaction[:16] if reaction else None

        # логика: instructions только для bot, reaction только для react
        if kind != "bot":
            instructions = None
        if kind != "react":
            reaction = None


        budget = int(price_digi) * int(total_qty)

        conn = self._connect()
        cur = conn.cursor()
        try:
            cur.execute("BEGIN IMMEDIATE")

            cur.execute("SELECT balance_digi FROM users WHERE tg_id=?", (int(owner_id),))
            u = cur.fetchone()
            if not u or int(u["balance_digi"] or 0) < budget:
                conn.rollback()
                return False, "Недостаточно DIGI для создания задания", None

            # списываем бюджет в escrow
            cur.execute("""
                 UPDATE users
                 SET balance_digi = balance_digi - ?,
                     total_spent_digi = total_spent_digi + ?
                 WHERE tg_id = ?
             """, (int(budget), int(budget), int(owner_id)))

            # создаём задание (с instructions/reaction)
            cur.execute("""
                 INSERT INTO market_tasks
                 (owner_id, kind, url, title, instructions, reaction,
                  src_chat_id, src_message_id,
                  price_digi, total_qty, remaining_qty,
                  escrow_total, escrow_remaining,
                  status, created_at)
                 VALUES (?, ?, ?, ?, ?, ?,
                         ?, ?,
                         ?, ?, ?,
                         ?, ?,
                         'active', ?)
             """, (
                int(owner_id), kind, url, title, instructions, reaction,
                int(src_chat_id) if src_chat_id else None,
                int(src_message_id) if src_message_id else None,
                int(price_digi), int(total_qty), int(total_qty),
                int(budget), int(budget),
                datetime.utcnow().isoformat()
            ))

            task_id = int(cur.lastrowid)
            conn.commit()
            return True, f"Задание создано. ID: {task_id}", task_id

        except Exception as e:
            conn.rollback()
            return False, f"Ошибка создания задания: {e}", None
        finally:
            conn.close()

    def market_list_tasks_for_user(self, kind: str, user_id: int, limit: int = 20, admin_id: int | None = None):
        kind = kind.strip().lower()
        conn = self._connect()
        cur = conn.cursor()

        is_admin = (admin_id is not None and int(user_id) == int(admin_id))

        if is_admin:
            cur.execute("""
                SELECT mt.*
                FROM market_tasks mt
                WHERE mt.kind = ?
                  AND mt.status = 'active'
                  AND mt.remaining_qty > 0
                  AND NOT EXISTS (
                    SELECT 1 FROM market_completions mc
                    WHERE mc.task_id = mt.id AND mc.worker_id = ? AND mc.reversed_at IS NULL
                  )
                ORDER BY mt.id DESC
                LIMIT ?
            """, (kind, user_id, int(limit)))
        else:
            cur.execute("""
                SELECT mt.*
                FROM market_tasks mt
                WHERE mt.kind = ?
                  AND mt.status = 'active'
                  AND mt.remaining_qty > 0
                  AND mt.owner_id != ?
                  AND NOT EXISTS (
                    SELECT 1 FROM market_completions mc
                    WHERE mc.task_id = mt.id AND mc.worker_id = ? AND mc.reversed_at IS NULL
                  )
                ORDER BY mt.id DESC
                LIMIT ?
            """, (kind, user_id, user_id, int(limit)))

        rows = cur.fetchall()
        conn.close()
        return rows

    def market_get_task(self, task_id: int) -> Optional[sqlite3.Row]:
        conn = self._connect()
        cur = conn.cursor()
        cur.execute("SELECT * FROM market_tasks WHERE id=?", (int(task_id),))
        row = cur.fetchone()
        conn.close()
        return row

    def market_has_completed(self, task_id: int, worker_id: int) -> bool:
        conn = self._connect()
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM market_completions WHERE task_id=? AND worker_id=?",
                    (int(task_id), int(worker_id)))
        ok = cur.fetchone() is not None
        conn.close()
        return ok

    def market_complete_task_and_pay(self, task_id: int, worker_id: int) -> Tuple[bool, str]:
        conn = self._connect()
        cur = conn.cursor()
        try:
            cur.execute("BEGIN IMMEDIATE")

            cur.execute("SELECT * FROM market_tasks WHERE id=?", (int(task_id),))
            t = cur.fetchone()
            if not t:
                conn.rollback()
                return False, "Задание не найдено"
            if t["status"] != "active" or int(t["remaining_qty"] or 0) <= 0:
                conn.rollback()
                return False, "Задание уже недоступно"
            if int(t["owner_id"]) == int(worker_id):
                conn.rollback()
                return False, "Нельзя выполнять своё задание"

            cur.execute("SELECT 1 FROM market_completions WHERE task_id=? AND worker_id=?",
                        (int(task_id), int(worker_id)))
            if cur.fetchone():
                conn.rollback()
                return False, "Вы уже выполняли это задание"

            price = int(t["price_digi"])
            if int(t["escrow_remaining"] or 0) < price:
                conn.rollback()
                return False, "Недостаточно средств в бюджете задания"

            cur.execute("""
                INSERT INTO market_completions (task_id, worker_id, created_at)
                VALUES (?, ?, ?)
            """, (int(task_id), int(worker_id), datetime.utcnow().isoformat()))

            new_remaining = int(t["remaining_qty"]) - 1
            new_escrow = int(t["escrow_remaining"]) - price

            new_status = "active" if new_remaining > 0 else "completed"

            cur.execute("""
                UPDATE market_tasks
                SET remaining_qty = ?,
                    escrow_remaining = ?,
                    status = ?
                WHERE id = ?
            """, (new_remaining, new_escrow, new_status, int(task_id)))

            cur.execute("""
                UPDATE users
                SET balance_digi = balance_digi + ?,
                    earned_digi = earned_digi + ?
                WHERE tg_id = ?
            """, (price, price, int(worker_id)))

            conn.commit()
            return True, f"✅ Выполнено! Начислено {price} DIGI"
        except sqlite3.IntegrityError:
            conn.rollback()
            return False, "Вы уже выполняли это задание"
        except Exception as e:
            conn.rollback()
            return False, f"Ошибка: {e}"
        finally:
            conn.close()

    def market_list_owner_tasks(self, owner_id: int, limit: int = 30) -> List[sqlite3.Row]:
        conn = self._connect()
        cur = conn.cursor()
        cur.execute("""
            SELECT *
            FROM market_tasks
            WHERE owner_id = ?
            ORDER BY id DESC
            LIMIT ?
        """, (int(owner_id), int(limit)))
        rows = cur.fetchall()
        conn.close()
        return rows

    def market_cancel_task_and_refund(self, task_id: int, owner_id: int) -> Tuple[bool, str, int]:
        conn = self._connect()
        cur = conn.cursor()
        try:
            cur.execute("BEGIN IMMEDIATE")

            cur.execute("SELECT * FROM market_tasks WHERE id=?", (int(task_id),))
            t = cur.fetchone()
            if not t:
                conn.rollback()
                return False, "Задание не найдено", 0
            if int(t["owner_id"]) != int(owner_id):
                conn.rollback()
                return False, "Это не ваше задание", 0
            if t["status"] != "active":
                conn.rollback()
                return False, "Задание уже не активно", 0

            refund = int(t["escrow_remaining"] or 0)

            cur.execute("""
                UPDATE market_tasks
                SET status='canceled', escrow_remaining=0, remaining_qty=0
                WHERE id=?
            """, (int(task_id),))

            if refund > 0:
                cur.execute("""
                    UPDATE users
                    SET balance_digi = balance_digi + ?
                    WHERE tg_id = ?
                """, (refund, int(owner_id)))

            conn.commit()
            return True, f"✅ Отменено. Возврат: {refund} DIGI", refund
        except Exception as e:
            conn.rollback()
            return False, f"Ошибка: {e}", 0
        finally:
            conn.close()

    def market_tasks_migrate_posts(self):
        conn = self._connect()
        cur = conn.cursor()
        cur.execute("PRAGMA table_info(market_tasks)")
        cols = [r["name"] for r in cur.fetchall()]

        if "src_chat_id" not in cols:
            cur.execute("ALTER TABLE market_tasks ADD COLUMN src_chat_id INTEGER")
        if "src_message_id" not in cols:
            cur.execute("ALTER TABLE market_tasks ADD COLUMN src_message_id INTEGER")

        conn.commit()
        conn.close()

    # (manual submissions) — оставляю как у тебя, без изменений
    def market_manual_init(self):
        conn = self._connect()
        cur = conn.cursor()
        cur.execute("""
         CREATE TABLE IF NOT EXISTS market_manual_submissions (
             id INTEGER PRIMARY KEY AUTOINCREMENT,
             task_id INTEGER NOT NULL,
             worker_id INTEGER NOT NULL,
             screenshot_file_id TEXT NOT NULL,
             status TEXT NOT NULL DEFAULT 'pending', -- pending/approved/rejected
             created_at TEXT NOT NULL,
             updated_at TEXT,
             UNIQUE(task_id, worker_id)
         )
         """)
        conn.commit()
        conn.close()

    def market_manual_upsert_pending(self, task_id: int, worker_id: int, file_id: str) -> Tuple[bool, str, int]:
        self.market_manual_init()
        conn = self._connect()
        cur = conn.cursor()
        try:
            cur.execute("SELECT id, status FROM market_manual_submissions WHERE task_id=? AND worker_id=?",
                        (int(task_id), int(worker_id)))
            row = cur.fetchone()
            if row:
                sub_id = int(row["id"])
                cur.execute("""
                     UPDATE market_manual_submissions
                     SET screenshot_file_id=?, status='pending', updated_at=datetime('now')
                     WHERE id=?
                 """, (file_id, sub_id))
                conn.commit()
                return True, "✅ Заявку оновлено і відправлено на перевірку.", sub_id

            cur.execute("""
                 INSERT INTO market_manual_submissions (task_id, worker_id, screenshot_file_id, status, created_at)
                 VALUES (?, ?, ?, 'pending', datetime('now'))
             """, (int(task_id), int(worker_id), file_id))
            sub_id = int(cur.lastrowid)
            conn.commit()
            return True, "✅ Заявка відправлена на перевірку.", sub_id
        except Exception as e:
            conn.rollback()
            return False, f"❌ Помилка: {e}", 0
        finally:
            conn.close()

    def market_manual_get(self, submission_id: int) -> Optional[Dict[str, Any]]:
        self.market_manual_init()
        conn = self._connect()
        cur = conn.cursor()
        cur.execute("SELECT * FROM market_manual_submissions WHERE id=?", (int(submission_id),))
        row = cur.fetchone()
        conn.close()
        return row

    def market_manual_set_status(self, sub_id: int, status: str) -> bool:
        conn = self._connect()
        cur = conn.cursor()
        try:
            try:
                cur.execute("PRAGMA table_info(market_manual_submissions)")
                cols = [r["name"] for r in cur.fetchall()]
                if "updated_at" not in cols:
                    cur.execute("ALTER TABLE market_manual_submissions ADD COLUMN updated_at TEXT")
            except Exception:
                pass

            cur.execute("""
                UPDATE market_manual_submissions
                SET status = ?, updated_at = datetime('now')
                WHERE id = ?
            """, (status, int(sub_id)))

            conn.commit()
            return cur.rowcount > 0
        except Exception:
            conn.rollback()
            return False
        finally:
            conn.close()

    def adjust_digi_allow_negative(self, tg_id: int, delta_digi: int) -> None:
        conn = self._connect()
        cur = conn.cursor()
        cur.execute("""
            UPDATE users
            SET balance_digi = COALESCE(balance_digi, 0) + ?
            WHERE tg_id = ?
        """, (int(delta_digi), int(tg_id)))
        conn.commit()
        conn.close()

    def get_digi_balance(self, tg_id: int) -> int:
        conn = self._connect()
        cur = conn.cursor()
        cur.execute("SELECT balance_digi FROM users WHERE tg_id=?", (int(tg_id),))
        row = cur.fetchone()
        conn.close()
        return int(row["balance_digi"] or 0) if row else 0

    def is_debtor(self, tg_id: int) -> bool:
        return self.get_digi_balance(tg_id) < 0

    # =========================================================
    # =================== STATUS SYSTEM =======================
    # =========================================================

    def get_status(self, tg_id: int) -> str:
        conn = self._connect()
        cur = conn.cursor()
        cur.execute("SELECT status FROM users WHERE tg_id=?", (int(tg_id),))
        row = cur.fetchone()
        conn.close()
        if not row:
            return "newbie"
        return str(row["status"] or "newbie")

    def increment_tasks_completed(self, tg_id: int):
        conn = self._connect()
        cur = conn.cursor()
        cur.execute("""
            UPDATE users
            SET tasks_completed_total = tasks_completed_total + 1
            WHERE tg_id = ?
        """, (int(tg_id),))
        conn.commit()
        conn.close()

    def increment_tasks_created(self, tg_id: int):
        conn = self._connect()
        cur = conn.cursor()
        cur.execute("""
            UPDATE users
            SET tasks_created_total = tasks_created_total + 1
            WHERE tg_id = ?
        """, (int(tg_id),))
        conn.commit()
        conn.close()

    def add_ref_balance(self, tg_id: int, amount: float):
        conn = self._connect()
        cur = conn.cursor()
        cur.execute("""
            UPDATE users
            SET usdt_balance = usdt_balance + ?
            WHERE tg_id = ?
        """, (float(amount), int(tg_id)))
        conn.commit()
        conn.close()

    def subtract_ref_balance(self, tg_id: int, amount: float) -> bool:
        conn = self._connect()
        cur = conn.cursor()

        cur.execute("SELECT usdt_balance FROM users WHERE tg_id=?", (int(tg_id),))
        row = cur.fetchone()

        if not row or float(row["usdt_balance"] or 0) < float(amount):
            conn.close()
            return False

        cur.execute("""
            UPDATE users
            SET usdt_balance = usdt_balance - ?
            WHERE tg_id = ?
        """, (float(amount), int(tg_id)))

        conn.commit()
        conn.close()
        return True

    def try_activate_user(self, tg_id: int) -> bool:
        """
        Активирует пользователя если:
        - total_topup_usdt >= 5
        - tasks_completed_total >= 7
        - tasks_created_total >= 7
        """

        conn = self._connect()
        cur = conn.cursor()

        cur.execute("""
            SELECT total_topup_usdt,
                   tasks_completed_total,
                   tasks_created_total,
                   status
            FROM users
            WHERE tg_id = ?
        """, (int(tg_id),))

        row = cur.fetchone()
        if not row:
            conn.close()
            return False

        if row["status"] == "active":
            conn.close()
            return False

        total_topup = float(row["total_topup_usdt"] or 0)
        completed = int(row["tasks_completed_total"] or 0)
        created = int(row["tasks_created_total"] or 0)

        if total_topup >= 10 and completed >= 7 and created >= 7:
            cur.execute("""
                UPDATE users
                SET status='active'
                WHERE tg_id = ?
            """, (int(tg_id),))
            conn.commit()
            conn.close()
            return True

        conn.close()
        return False

    def leader_progress(self, tg_id: int, min_topup_usdt: float = 10.0) -> int:
        """
        Сколько приглашённых (invited_by) сделали пополнение total_topup_usdt >= 10
        """
        conn = self._connect()
        cur = conn.cursor()
        cur.execute("""
            SELECT COUNT(*) AS cnt
            FROM users
            WHERE invited_by = ?
              AND COALESCE(total_topup_usdt, 0) >= ?
        """, (int(tg_id), float(min_topup_usdt)))
        row = cur.fetchone()
        conn.close()
        return int(row["cnt"] or 0) if row else 0

    def try_grant_leader(self, tg_id: int, need_refs: int = 10, min_topup_usdt: float = 10.0,
                         bonus_usdt: float = 10.0) -> bool:
        """
        Даёт статус leader если выполнено:
          - invited_by count (total_topup_usdt >= 10) >= 10
        При выдаче: начисляет +10 USDT ОДИН РАЗ (leader_bonus_given)
        """
        conn = self._connect()
        cur = conn.cursor()
        try:
            cur.execute("BEGIN IMMEDIATE")

            cur.execute("SELECT status, leader_bonus_given FROM users WHERE tg_id=?", (int(tg_id),))
            u = cur.fetchone()
            if not u:
                conn.rollback()
                return False

            status = str(u["status"] or "newbie")
            bonus_given = int(u["leader_bonus_given"] or 0)

            # если уже лидер — ничего
            if status == "leader":
                conn.rollback()
                return False

            cur.execute("""
                SELECT COUNT(*) AS cnt
                FROM users
                WHERE invited_by = ?
                  AND COALESCE(total_topup_usdt, 0) >= ?
            """, (int(tg_id), float(min_topup_usdt)))
            cnt = int((cur.fetchone() or {})["cnt"] or 0)

            if cnt < int(need_refs):
                conn.rollback()
                return False

            # выдаём статус leader
            cur.execute("UPDATE users SET status='leader' WHERE tg_id=?", (int(tg_id),))

            # бонус 10 USDT один раз
            if bonus_given == 0:
                cur.execute("""
                    UPDATE users
                    SET usdt_balance = COALESCE(usdt_balance, 0) + ?,
                        leader_bonus_given = 1
                    WHERE tg_id = ?
                """, (float(bonus_usdt), int(tg_id)))

            conn.commit()
            return True

        except Exception:
            conn.rollback()
            return False
        finally:
            conn.close()
