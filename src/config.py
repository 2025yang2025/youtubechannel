from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import yaml
from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[1]

load_dotenv(ROOT / ".env")


@dataclass
class Channel:
    name: str
    channel_id: str
    handle: str
    enabled: bool
    keywords: list[str]
    min_score: int


def load_settings() -> dict:
    path = ROOT / "config" / "settings.yaml"

    with open(
        path,
        "r",
        encoding="utf-8",
    ) as f:
        return yaml.safe_load(f) or {}


def load_channels() -> list[Channel]:
    path = ROOT / "config" / "channels.yaml"

    with open(
        path,
        "r",
        encoding="utf-8",
    ) as f:
        raw = yaml.safe_load(f) or {}

    channels = []

    for item in raw.get("channels", []):
        channels.append(
            Channel(
                name=str(item.get("name", "")).strip(),
                channel_id=str(
                    item.get("channel_id", "")
                ).strip(),
                handle=str(
                    item.get("handle", "")
                ).strip(),
                enabled=bool(
                    item.get("enabled", True)
                ),
                keywords=[
                    str(x).strip()
                    for x in item.get(
                        "keywords",
                        [],
                    )
                ],
                min_score=int(
                    item.get(
                        "min_score",
                        50,
                    )
                ),
            )
        )

    return channels


def get_env(
    name: str,
    default: str = "",
) -> str:
    return os.getenv(
        name,
        default,
    ).strip()


def required_env(name: str) -> str:
    value = get_env(name)

    if not value:
        raise RuntimeError(
            f"Missing required environment variable: {name}"
        )

    return value
