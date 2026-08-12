from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml
from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[1]

load_dotenv(
    ROOT / ".env"
)


@dataclass
class Channel:
    """
    YouTube 頻道設定。

    可以使用：
        channel_id: UCxxxxxxxx
    或：
        handle: "@example"
    """

    name: str

    channel_id: str = ""

    handle: str = ""

    enabled: bool = True

    keywords: list[str] = field(
        default_factory=list
    )

    min_score: int = 50


@dataclass
class Playlist:
    """
    YouTube Playlist 設定。
    """

    name: str

    playlist_id: str

    enabled: bool = True

    keywords: list[str] = field(
        default_factory=list
    )

    min_score: int = 50


def load_settings() -> dict:
    """
    載入 config/settings.yaml
    """

    path = (
        ROOT
        / "config"
        / "settings.yaml"
    )

    with open(
        path,
        "r",
        encoding="utf-8",
    ) as f:

        return yaml.safe_load(f) or {}


def load_channels() -> list[Channel]:
    """
    載入 YouTube Channels。

    支援：

        channels:

          - name: "總編當莊"
            handle: "@berich888"

          - name: "陳威良"
            handle: "@ccstock888"

    也支援舊格式：

          - name: "xxx"
            channel_id: "UCxxxxxxxx"
    """

    path = (
        ROOT
        / "config"
        / "channels.yaml"
    )

    with open(
        path,
        "r",
        encoding="utf-8",
    ) as f:

        raw = yaml.safe_load(f) or {}

    channels: list[Channel] = []

    for item in raw.get(
        "channels",
        [],
    ):

        name = str(
            item.get(
                "name",
                "Unnamed Channel",
            )
        )

        channel_id = str(
            item.get(
                "channel_id",
                "",
            )
            or ""
        ).strip()

        handle = str(
            item.get(
                "handle",
                "",
            )
            or ""
        ).strip()

        enabled = bool(
            item.get(
                "enabled",
                True,
            )
        )

        keywords = [
            str(x)
            for x in item.get(
                "keywords",
                [],
            )
        ]

        min_score = int(
            item.get(
                "min_score",
                50,
            )
        )

        # -----------------------------------------------------
        # 至少要有 channel_id 或 handle
        # -----------------------------------------------------

        if not channel_id and not handle:

            # 不直接讓整個程式崩潰，
            # 交給 main.py 顯示 warning。
            print(
                f"WARNING: Channel '{name}' "
                f"沒有 channel_id 或 handle，"
                f"將由上層跳過。"
            )

        channels.append(
            Channel(
                name=name,
                channel_id=channel_id,
                handle=handle,
                enabled=enabled,
                keywords=keywords,
                min_score=min_score,
            )
        )

    return channels


def load_playlists() -> list[Playlist]:
    """
    載入 YouTube Playlists。

    例如：

        playlists:

          - name: "請支援輸贏"
            playlist_id: "PLxxxxxxxx"
            enabled: true
    """

    path = (
        ROOT
        / "config"
        / "channels.yaml"
    )

    with open(
        path,
        "r",
        encoding="utf-8",
    ) as f:

        raw = yaml.safe_load(f) or {}

    playlists: list[Playlist] = []

    for item in raw.get(
        "playlists",
        [],
    ):

        name = str(
            item.get(
                "name",
                "Unnamed Playlist",
            )
        )

        playlist_id = str(
            item.get(
                "playlist_id",
                "",
            )
            or ""
        ).strip()

        enabled = bool(
            item.get(
                "enabled",
                True,
            )
        )

        keywords = [
            str(x)
            for x in item.get(
                "keywords",
                [],
            )
        ]

        min_score = int(
            item.get(
                "min_score",
                50,
            )
        )

        if not playlist_id:

            print(
                f"WARNING: Playlist '{name}' "
                f"沒有 playlist_id，"
                f"將由上層跳過。"
            )

            continue

        playlists.append(
            Playlist(
                name=name,
                playlist_id=playlist_id,
                enabled=enabled,
                keywords=keywords,
                min_score=min_score,
            )
        )

    return playlists


def get_env(
    name: str,
    default: str = "",
) -> str:
    """
    取得環境變數。
    """

    return os.getenv(
        name,
        default,
    ).strip()


def required_env(
    name: str,
) -> str:
    """
    取得必要環境變數。

    如果不存在，直接拋出錯誤。
    """

    value = get_env(
        name
    )

    if not value:

        raise RuntimeError(
            "Missing required environment variable: "
            f"{name}"
        )

    return value
