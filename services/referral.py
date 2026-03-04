# services/referral.py
from __future__ import annotations

from dataclasses import dataclass

from config import Config
from database import Database


@dataclass(frozen=True)
class ReferralInfo:
    link: str
    reward_digi: int
    cond_earned_digi: int
    cond_hours: int


class ReferralService:
    def __init__(self, db: Database, cfg: Config):
        self.db = db
        self.cfg = cfg

    def build_ref_link(self, bot_username: str, referrer_tg_id: int) -> str:
        bot_username = (bot_username or "").lstrip("@")
        return f"https://t.me/{bot_username}?start=ref_{referrer_tg_id}"

    def get_info(self, bot_username: str, referrer_tg_id: int) -> ReferralInfo:
        return ReferralInfo(
            link=self.build_ref_link(bot_username, referrer_tg_id),
            reward_digi=self.cfg.REF_REWARD_DIGI,
            cond_earned_digi=self.cfg.REF_CONDITION_EARN_DIGI,
            cond_hours=self.cfg.REF_CONDITION_HOURS,
        )

    def try_payout_for_user(self, referral_user_tg_id: int) -> None:
        """
        Пытается начислить награду рефереру, если реферал выполнил условия:
        - earned_digi >= REF_CONDITION_EARN_DIGI
        - прошло >= REF_CONDITION_HOURS часов с created_at
        """
        self.db.process_referral_if_ready(
            tg_id=referral_user_tg_id,
            reward_digi=self.cfg.REF_REWARD_DIGI,
            min_earned=self.cfg.REF_CONDITION_EARN_DIGI,
            min_hours=self.cfg.REF_CONDITION_HOURS,
        )

    def pretty_rules_text(self) -> str:
        return (
            "✅ <b>Условия начисления:</b>\n"
            f"1) Реферал должен заработать <b>{self.cfg.REF_CONDITION_EARN_DIGI:,} DGR</b>\n"
            f"2) Реферал должен быть в боте <b>{self.cfg.REF_CONDITION_HOURS} часа</b>\n"
            f"🎁 Награда: <b>{self.cfg.REF_REWARD_DIGI:,} DGR</b>"
        )
