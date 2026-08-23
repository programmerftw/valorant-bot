import json
from typing import Any

from config import GUILDS_FILE


def _load() -> dict[str, Any]:
    if not GUILDS_FILE.exists():
        return {}
    with GUILDS_FILE.open(encoding="utf-8") as f:
        return json.load(f)


def _save(data: dict[str, Any]) -> None:
    with GUILDS_FILE.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def get_guild_config(guild_id: int) -> dict[str, Any]:
    data = _load()
    key = str(guild_id)
    if key not in data:
        data[key] = {
            "news_channel_id": None,
            "live_channel_id": None,
            "upcoming_channel_id": None,
            "results_channel_id": None,
            "posted_news": [],
            "posted_upcoming": [],
            "posted_results": [],
            "live_messages": {},
        }
        _save(data)
    return data[key]


def update_guild_config(guild_id: int, **kwargs: Any) -> dict[str, Any]:
    data = _load()
    key = str(guild_id)
    config = data.get(key, get_guild_config(guild_id))
    config.update(kwargs)
    data[key] = config
    _save(data)
    return config


def all_configured_guilds() -> dict[str, dict[str, Any]]:
    return _load()
