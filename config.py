# config.py
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

# Загружаем .env (если есть)
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent


def _get_env(name: str, default: str | None = None) -> str:
    val = os.getenv(name, default)
    if val is None or val == "":
        raise RuntimeError(f"Missing required environment variable: {name}")
    return val


@dataclass(frozen=True)
class Config:
    # Telegram
    BOT_TOKEN: str

    # Admin
    ADMIN_ID: int  # доступ к Админ Панели
    SUPPORT_USERNAME: str  # кнопка "Администратор" -> @username

    AUTO_APPROVE_HOURS = 24
    AUTO_APPROVE_CHECK_INTERVAL_SEC = 120

    STARS_MIN = 20  # мінімум зірок
    DIGI_PER_STAR = 50  # 1⭐ = 50 DIGI

    UNFOLLOW_PENALTY_DAYS = 10
    UNFOLLOW_CHECK_INTERVAL_SEC = 300

    # CryptoBot
    CRYPTOBOT_TOKEN: str
    CRYPTOBOT_API_BASE: str

    # Рефералы (USDT, 2 уровня):
    # - реферал засчитывается, когда приглашённый пополнит суммарно >= REF_MIN_TOPUP_USDT
    # - 1 уровень (прямой): REF_L1_REWARD_USDT
    # - 2 уровень (реферал вашего реферала): REF_L2_REWARD_USDT
    REF_MIN_TOPUP_USDT: float
    REF_L1_REWARD_USDT: float
    REF_L2_REWARD_USDT: float

    # ---------------------------
    # Business settings (старые)
    # ---------------------------
    DIGI_RATE_USDT: float  # 1 DIGI = 0.001 USDT (старое, оставляем для совместимости)
    TOPUP_MIN_USDT: float  # минимум пополнения USDT

    # Старая рефералка (оставляем, но новая логика в handlers/referral.py не использует эти поля)
    REF_REWARD_DIGI: int
    REF_CONDITION_EARN_DIGI: int
    REF_CONDITION_HOURS: int

    ADS_PRICE_PER_DAY_DIGI: int  # реклама

    # Digi links (старое, для подписанных ссылок)
    DIGI_SHARED_SECRET: str
    DIGI_LINK_TTL_MIN: int

    # Links
    WEBSITE_URL: str

    # Storage
    DB_PATH: Path
    MEDIA_DIR: Path

    # ---------------------------
    # Новая экономика / Wallet
    # ---------------------------

    # Конвертация DIGI -> USDT
    DIGI_PER_1_USDT: int  # 5000 DIGI = 1 USDT

    # Key linking (одноразовый ключ)
    WALLET_LINK_KEY_TTL_SEC: int  # 5 минут = 300 сек

    # Лимиты выполнения задач в день
    FREE_TASKS_LIMIT_PER_DAY: int
    VIP_TASKS_LIMIT_PER_DAY: int

    # Рефералы: активность = пополнение >= X USDT
    REF_ACTIVE_MIN_TOPUP_USDT: float
    FREE_REF_REWARD_DIGI: int
    VIP_REF_REWARD_DIGI: int

    # VIP тариф
    VIP_PRICE_USDT: float
    VIP_DURATION_DAYS: int
    VIP_DAILY_BONUS_DIGI: int

    # Вывод USDT (только VIP)
    VIP_WITHDRAW_MIN_USDT: float
    VIP_WITHDRAW_MAX_USDT_PER_DAY: float

    # (опционально) Wallet API server settings (если будем поднимать HTTP внутри DigiBot)
    WALLET_API_ENABLED: bool
    WALLET_API_HOST: str
    WALLET_API_PORT: int
    WALLET_API_TOKEN: str

    WEBAPP_URL: str
    WEBAPP_HOST: str
    WEBAPP_PORT: int

def load_config() -> Config:
    return Config(
        # Telegram
        BOT_TOKEN=_get_env("BOT_TOKEN"),

        # Admin
        ADMIN_ID=int(_get_env("ADMIN_ID", "7447763153")),
        SUPPORT_USERNAME=os.getenv("SUPPORT_USERNAME", "@illy228"),

        # CryptoBot
        CRYPTOBOT_TOKEN=_get_env("CRYPTOBOT_TOKEN"),
        CRYPTOBOT_API_BASE=os.getenv("CRYPTOBOT_API_BASE", "https://pay.crypt.bot/api"),

        # ---------------------------
        # Business settings (старые)
        # ---------------------------
        DIGI_RATE_USDT=float(os.getenv("DIGI_RATE_USDT", "0.001")),
        TOPUP_MIN_USDT=float(os.getenv("TOPUP_MIN_USDT", "5")),

        REF_REWARD_DIGI=int(os.getenv("REF_REWARD_DIGI", "2000")),
        REF_CONDITION_EARN_DIGI=int(os.getenv("REF_CONDITION_EARN_DIGI", "1000")),
        REF_CONDITION_HOURS=int(os.getenv("REF_CONDITION_HOURS", "24")),

        ADS_PRICE_PER_DAY_DIGI=int(os.getenv("ADS_PRICE_PER_DAY_DIGI", "500")),

        # Links
        WEBSITE_URL=os.getenv("WEBSITE_URL", "https://example.com"),

        # Storage
        DB_PATH=Path(os.getenv("DB_PATH", str(BASE_DIR / "digital.sqlite3"))),
        MEDIA_DIR=Path(os.getenv("MEDIA_DIR", str(BASE_DIR / "media"))),

        # Digi links (старое)
        DIGI_SHARED_SECRET=_get_env("DIGI_SHARED_SECRET"),
        DIGI_LINK_TTL_MIN=int(os.getenv("DIGI_LINK_TTL_MIN", "30")),

        # ---------------------------
        # Новая экономика / Wallet
        # ---------------------------
        DIGI_PER_1_USDT=int(os.getenv("DIGI_PER_1_USDT", "5000")),

        WALLET_LINK_KEY_TTL_SEC=int(os.getenv("WALLET_LINK_KEY_TTL_SEC", "300")),

        FREE_TASKS_LIMIT_PER_DAY=int(os.getenv("FREE_TASKS_LIMIT_PER_DAY", "1000")),
        VIP_TASKS_LIMIT_PER_DAY=int(os.getenv("VIP_TASKS_LIMIT_PER_DAY", "1000")),
        # новая рефералка (USDT)
        REF_MIN_TOPUP_USDT=float(os.getenv("REF_MIN_TOPUP_USDT", "10")),
        REF_L1_REWARD_USDT=float(os.getenv("REF_L1_REWARD_USDT", "4")),
        REF_L2_REWARD_USDT=float(os.getenv("REF_L2_REWARD_USDT", "2")),

        REF_ACTIVE_MIN_TOPUP_USDT=float(os.getenv("REF_ACTIVE_MIN_TOPUP_USDT", "10")),
        FREE_REF_REWARD_DIGI=int(os.getenv("FREE_REF_REWARD_DIGI", "5000")),
        VIP_REF_REWARD_DIGI=int(os.getenv("VIP_REF_REWARD_DIGI", "10000")),

        VIP_PRICE_USDT=float(os.getenv("VIP_PRICE_USDT", "35")),
        VIP_DURATION_DAYS=int(os.getenv("VIP_DURATION_DAYS", "45")),
        VIP_DAILY_BONUS_DIGI=int(os.getenv("VIP_DAILY_BONUS_DIGI", "300")),

        VIP_WITHDRAW_MIN_USDT=float(os.getenv("VIP_WITHDRAW_MIN_USDT", "20")),
        VIP_WITHDRAW_MAX_USDT_PER_DAY=float(os.getenv("VIP_WITHDRAW_MAX_USDT_PER_DAY", "100")),

        WALLET_API_ENABLED=os.getenv("WALLET_API_ENABLED", "0") in ("1", "true", "True", "yes", "YES"),
        WALLET_API_HOST=os.getenv("WALLET_API_HOST", "127.0.0.1"),
        WALLET_API_PORT=int(os.getenv("WALLET_API_PORT", "8088")),
        WALLET_API_TOKEN=os.getenv("WALLET_API_TOKEN", "change_me_wallet_api_token"),

        WEBAPP_URL=os.getenv("WEBAPP_URL", "https://your-domain.com/miniapp/"),
        WEBAPP_HOST=os.getenv("WEBAPP_HOST", "0.0.0.0"),
        WEBAPP_PORT=int(os.getenv("WEBAPP_PORT") or os.getenv("PORT") or "8080")

    )



