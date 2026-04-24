import os
from typing import Optional
from functools import lru_cache


def get_sla_warning_threshold_hours() -> int:
    return int(os.getenv("SLA_WARNING_THRESHOLD_HOURS", "24"))


def get_sla_allow_past_deadline() -> bool:
    return os.getenv("SLA_ALLOW_PAST_DEADLINE", "false").lower() == "true"


class Settings:
    @property
    def SLA_WARNING_THRESHOLD_HOURS(self) -> int:
        return get_sla_warning_threshold_hours()

    @property
    def SLA_ALLOW_PAST_DEADLINE(self) -> bool:
        return get_sla_allow_past_deadline()

    _instance: Optional["Settings"] = None

    @classmethod
    def get_instance(cls) -> "Settings":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance


@lru_cache
def get_settings() -> Settings:
    return Settings.get_instance()
