import os
from typing import Optional


class Settings:
    SLA_WARNING_THRESHOLD_HOURS: int = int(os.getenv("SLA_WARNING_THRESHOLD_HOURS", "24"))
    SLA_ALLOW_PAST_DEADLINE: bool = os.getenv("SLA_ALLOW_PAST_DEADLINE", "false").lower() == "true"

    _instance: Optional["Settings"] = None

    @classmethod
    def get_instance(cls) -> "Settings":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance


def get_settings() -> Settings:
    return Settings.get_instance()
