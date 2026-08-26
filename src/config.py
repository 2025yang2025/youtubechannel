from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml
from dotenv import load_dotenv


# ============================================================
# 專案根目錄
# ============================================================

ROOT = Path(__file__).resolve().parents[1]

# 載入 .env
load_dotenv(ROOT / ".env")


# ============================================================
# Channel 資料結構
# ============================================================

@dataclass
class Channel:
    name: str

    # 可以只使用 handle，不一定需要 channel_id
    channel_id: str = ""

    handle: str = ""

    enabled: bool = True

    keywords: list[str] = field(default_factory=list)

    min_score: int = 50


# ============================================================
# Settings
# ============================================================

def load_settings() -> dict:
    path = ROOT / "config" / "settings.yaml"

    if not path.exists():
        return {}

    with open(
        path,
        "r",
        encoding="utf-8",
    ) as f:
        return yaml.safe_load(f) or {}


# ============================================================
# Channels
# ============================================================

def load_channels() -> list[Channel]:

    path = ROOT / "config" / "channels.yaml"

    if not path.exists():
        raise FileNotFoundError(
            f"找不到頻道設定檔: {path}"
        )

    with open(
        path,
        "r",
        encoding="utf-8",
    ) as f:

        raw = yaml.safe_load(f) or {}

    result: list[Channel] = []

    for item in raw.get("channels", []):

        if not isinstance(item, dict):
            continue

        name = str(
            item.get(
                "name",
                ""
            )
        ).strip()

        channel_id = str(
            item.get(
                "channel_id",
                ""
            )
        ).strip()

        handle = str(
            item.get(
                "handle",
                ""
            )
        ).strip()

        enabled = bool(
            item.get(
                "enabled",
                True
            )
        )

        keywords = [
            str(x).strip()
            for x in item.get(
                "keywords",
                []
            )
            if str(x).strip()
        ]

        min_score = int(
            item.get(
                "min_score",
                50
            )
        )

        # ----------------------------------------------------
        # 沒有 channel_id 也沒關係，只要有 handle 即可
        # ----------------------------------------------------

        if enabled and not channel_id and not handle:

            print(
                f"WARNING: Channel '{name}' "
                f"沒有 channel_id 或 handle，將由上層跳過。"
            )

        result.append(
            Channel(
                name=name,
                channel_id=channel_id,
                handle=handle,
                enabled=enabled,
                keywords=keywords,
                min_score=min_score,
            )
        )

    return result


# ============================================================
# Environment
# ============================================================

def get_env(
    name: str,
    default: str = "",
) -> str:

    return os.getenv(
        name,
        default
    ).strip()


def required_env(
    name: str,
) -> str:

    value = get_env(name)

    if not value:

        raise RuntimeError(
            f"Missing required environment variable: {name}"
        )

    return value
