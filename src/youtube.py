from __future__ import annotations

from typing import Any, Dict, List, Optional

import requests


YOUTUBE_API_BASE = "https://www.googleapis.com/youtube/v3"


class YouTubeAPIError(RuntimeError):
    """YouTube API related error."""


def _request(
    endpoint: str,
    params: Dict[str, Any],
    timeout: int = 30,
) -> Dict[str, Any]:
    """
    呼叫 YouTube Data API v3。
    """

    url = f"{YOUTUBE_API_BASE}/{endpoint}"

    try:
        response = requests.get(
            url,
            params=params,
            timeout=timeout,
        )

    except requests.RequestException as exc:

        raise YouTubeAPIError(
            f"YouTube API 網路連線失敗: {exc}"
        ) from exc

    # ---------------------------------------------------------
    # HTTP error
    # ---------------------------------------------------------

    if response.status_code != 200:

        try:
            data = response.json()

        except Exception:
            data = {}

        error = data.get(
            "error",
            {},
        )

        message = (
            error.get("message")
            or response.text
            or f"HTTP {response.status_code}"
        )

        raise YouTubeAPIError(
            f"YouTube API HTTP "
            f"{response.status_code}: "
            f"{message}"
        )

    # ---------------------------------------------------------
    # JSON
    # ---------------------------------------------------------

    try:

        return response.json()

    except Exception as exc:

        raise YouTubeAPIError(
            "YouTube API 回傳資料不是有效 JSON"
        ) from exc


# =============================================================
# Channel
# =============================================================

def get_channel_by_id(
    api_key: str,
    channel_id: str,
) -> Optional[Dict[str, Any]]:
    """
    使用 Channel ID 查詢頻道。
    """

    if not channel_id:

        return None

    data = _request(
        "channels",
        {
            "part": "snippet,contentDetails",
            "id": channel_id,
            "key": api_key,
        },
    )

    items = data.get(
        "items",
        [],
    )

    if not items:

        return None

    return items[0]


def get_channel_by_handle(
    api_key: str,
    handle: str,
) -> Optional[Dict[str, Any]]:
    """
    使用 YouTube @handle 查詢頻道。

    例如：

        @berich888
        @ccstock888
    """

    if not handle:

        return None

    clean_handle = str(
        handle
    ).strip()

    # ---------------------------------------------------------
    # 如果傳入完整 URL
    # ---------------------------------------------------------

    if clean_handle.startswith(
        "https://www.youtube.com/"
    ):

        clean_handle = (
            clean_handle
            .rstrip("/")
            .split("/")[-1]
        )

    # ---------------------------------------------------------
    # 確保 @
    # ---------------------------------------------------------

    if not clean_handle.startswith("@"):

        clean_handle = (
            "@"
            + clean_handle
        )

    data = _request(
        "channels",
        {
            "part": "snippet,contentDetails",
            "forHandle": clean_handle,
            "key": api_key,
        },
    )

    items = data.get(
        "items",
        [],
    )

    if not items:

        return None

    return items[0]


def resolve_channel(
    api_key: str,
    channel_id: Optional[str] = None,
    handle: Optional[str] = None,
) -> Dict[str, Any]:
    """
    將 Channel ID 或 @handle
    解析成完整 YouTube 頻道資料。
    """

    # ---------------------------------------------------------
    # 優先使用 Channel ID
    # ---------------------------------------------------------

    if channel_id:

        channel = get_channel_by_id(
            api_key,
            channel_id,
        )

        if channel is not None:

            return channel

    # ---------------------------------------------------------
    # 再使用 @handle
    # ---------------------------------------------------------

    if handle:

        channel = get_channel_by_handle(
            api_key,
            handle,
        )

        if channel is not None:

            return channel

    identifier = (
        channel_id
        or handle
        or "(未提供)"
    )

    raise YouTubeAPIError(
        f"找不到頻道: {identifier}"
    )


# =============================================================
# Upload Playlist
# =============================================================

def get_upload_playlist(
    api_key: str,
    channel_id: str,
) -> str:
    """
    取得 YouTube 頻道的 uploads playlist ID。
    """

    channel = get_channel_by_id(
        api_key,
        channel_id,
    )

    if channel is None:

        raise YouTubeAPIError(
            f"找不到頻道: {channel_id}"
        )

    content_details = channel.get(
        "contentDetails",
        {},
    )

    related_playlists = (
        content_details.get(
            "relatedPlaylists",
            {},
        )
    )

    uploads_playlist = (
        related_playlists.get(
            "uploads"
        )
    )

    if not uploads_playlist:

        raise YouTubeAPIError(
            f"頻道 {channel_id} "
            f"找不到 uploads playlist"
        )

    return uploads_playlist


# =============================================================
# Playlist videos
# =============================================================

def get_latest_videos_from_playlist(
    api_key: str,
    playlist_id: str,
    max_results: int = 10,
) -> List[Dict[str, Any]]:
    """
    從指定 Playlist 取得最新影片。
    """

    if not playlist_id:

        raise YouTubeAPIError(
            "playlist_id 不可為空"
        )

    max_results = max(
        1,
        min(
            int(max_results),
            50,
        ),
    )

    data = _request(
        "playlistItems",
        {
            "part": (
                "snippet,"
                "contentDetails"
            ),
            "playlistId": playlist_id,
            "maxResults": max_results,
            "key": api_key,
        },
    )

    items = data.get(
        "items",
        [],
    )

    results: List[
        Dict[str, Any]
    ] = []

    for item in items:

        snippet = item.get(
            "snippet",
            {},
        )

        content_details = item.get(
            "contentDetails",
            {},
        )

        resource = snippet.get(
            "resourceId",
            {},
        )

        video_id = (
            content_details.get(
                "videoId"
            )
            or resource.get(
                "videoId"
            )
        )

        if not video_id:

            continue

        thumbnails = (
            snippet.get(
                "thumbnails",
                {},
            )
        )

        high_thumbnail = (
            thumbnails
            .get(
                "high",
                {},
            )
            .get(
                "url"
            )
        )

        results.append(
            {
                "video_id": video_id,

                "title": snippet.get(
                    "title",
                    "",
                ),

                "description": snippet.get(
                    "description",
                    "",
                ),

                "published_at": snippet.get(
                    "publishedAt",
                ),

                "channel_id": snippet.get(
                    "channelId",
                ),

                "channel_title": snippet.get(
                    "channelTitle",
                    "",
                ),

                "thumbnail": high_thumbnail,

                "url": (
                    "https://www.youtube.com/watch?v="
                    + video_id
                ),
            }
        )

    return results


# =============================================================
# Channel latest videos
# =============================================================

def get_latest_videos(
    api_key: str,
    channel,
    max_results: int = 10,
) -> List[Dict[str, Any]]:
    """
    取得指定 Channel 最新影片。

    支援：

        Channel.channel_id

    或：

        Channel.handle

    main.py 現在會直接把 Channel object 傳進來，
    所以這裡會自動解析。
    """

    # ---------------------------------------------------------
    # 取得 channel_id
    # ---------------------------------------------------------

    channel_id = getattr(
        channel,
        "channel_id",
        "",
    )

    # ---------------------------------------------------------
    # 取得 handle
    # ---------------------------------------------------------

    handle = getattr(
        channel,
        "handle",
        "",
    )

    # ---------------------------------------------------------
    # 如果不是 Channel object，
    # 也相容字串 channel_id
    # ---------------------------------------------------------

    if isinstance(
        channel,
        str,
    ):

        channel_id = channel
        handle = ""

    # ---------------------------------------------------------
    # 移除舊版 placeholder
    # ---------------------------------------------------------

    if channel_id and channel_id.startswith(
        "UC_REPLACE"
    ):

        channel_id = ""

    # ---------------------------------------------------------
    # 如果只有 handle，
    # 自動解析成真正 Channel ID
    # ---------------------------------------------------------

    resolved = resolve_channel(
        api_key=api_key,
        channel_id=channel_id or None,
        handle=handle or None,
    )

    resolved_channel_id = (
        resolved.get("id")
    )

    if not resolved_channel_id:

        identifier = (
            channel_id
            or handle
            or "(未提供)"
        )

        raise YouTubeAPIError(
            f"YouTube API 無法取得 "
            f"Channel ID: {identifier}"
        )

    # ---------------------------------------------------------
    # 取得 uploads playlist
    # ---------------------------------------------------------

    playlist_id = get_upload_playlist(
        api_key,
        resolved_channel_id,
    )

    # ---------------------------------------------------------
    # 取得最新影片
    # ---------------------------------------------------------

    return get_latest_videos_from_playlist(
        api_key,
        playlist_id,
        max_results,
    )


# =============================================================
# Compatibility helper
# =============================================================

def get_channel_latest_videos(
    api_key: str,
    channel_id: Optional[str] = None,
    handle: Optional[str] = None,
    max_results: int = 10,
) -> List[Dict[str, Any]]:
    """
    另一種呼叫方式。

    例如：

        get_channel_latest_videos(
            api_key,
            handle="@berich888",
        )
    """

    class SimpleChannel:

        def __init__(
            self,
            channel_id: str,
            handle: str,
        ):
            self.channel_id = channel_id
            self.handle = handle

    channel = SimpleChannel(
        channel_id or "",
        handle or "",
    )

    return get_latest_videos(
        api_key,
        channel,
        max_results,
    )


# =============================================================
# Playlist helper
# =============================================================

def get_playlist_latest_videos(
    api_key: str,
    playlist_id: str,
    max_results: int = 10,
) -> List[Dict[str, Any]]:
    """
    取得 Playlist 最新影片。
    """

    return get_latest_videos_from_playlist(
        api_key,
        playlist_id,
        max_results,
    )
