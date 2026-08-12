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

    if response.status_code != 200:
        try:
            data = response.json()
        except Exception:
            data = {}

        error_message = (
            data.get("error", {})
            .get("message")
            or response.text
            or f"HTTP {response.status_code}"
        )

        raise YouTubeAPIError(
            f"YouTube API HTTP {response.status_code}: "
            f"{error_message}"
        )

    try:
        return response.json()
    except Exception as exc:
        raise YouTubeAPIError(
            "YouTube API 回傳資料不是有效 JSON"
        ) from exc


def get_channel_by_id(
    api_key: str,
    channel_id: str,
) -> Optional[Dict[str, Any]]:
    """
    使用 Channel ID 查詢頻道。
    """

    data = _request(
        "channels",
        {
            "part": "snippet,contentDetails",
            "id": channel_id,
            "key": api_key,
        },
    )

    items = data.get("items", [])

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

    clean_handle = handle.strip()

    if clean_handle.startswith("https://www.youtube.com/"):
        clean_handle = clean_handle.rstrip("/").split("/")[-1]

    if not clean_handle.startswith("@"):
        clean_handle = f"@{clean_handle}"

    # YouTube Data API v3 channels.list 支援 forHandle。
    data = _request(
        "channels",
        {
            "part": "snippet,contentDetails",
            "forHandle": clean_handle,
            "key": api_key,
        },
    )

    items = data.get("items", [])

    if not items:
        return None

    return items[0]


def resolve_channel(
    api_key: str,
    channel_id: Optional[str] = None,
    handle: Optional[str] = None,
) -> Dict[str, Any]:
    """
    將 Channel ID 或 @handle 解析成完整頻道資料。
    """

    channel = None

    if channel_id:
        channel = get_channel_by_id(
            api_key,
            channel_id,
        )

        if channel is not None:
            return channel

    if handle:
        channel = get_channel_by_handle(
            api_key,
            handle,
        )

        if channel is not None:
            return channel

    identifier = channel_id or handle or "(未提供)"

    raise YouTubeAPIError(
        f"找不到 YouTube 頻道: {identifier}\n"
        f"請確認頻道網址、@handle 或 Channel ID 是否正確。"
    )


def get_upload_playlist(
    api_key: str,
    channel_id: str,
) -> str:
    """
    取得頻道的 uploads playlist ID。
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

    related_playlists = content_details.get(
        "relatedPlaylists",
        {},
    )

    uploads_playlist = related_playlists.get(
        "uploads"
    )

    if not uploads_playlist:
        raise YouTubeAPIError(
            f"頻道 {channel_id} 找不到 uploads playlist"
        )

    return uploads_playlist


def get_latest_videos_from_playlist(
    api_key: str,
    playlist_id: str,
    max_results: int = 10,
) -> List[Dict[str, Any]]:
    """
    從指定 Playlist 取得最新影片。
    """

    data = _request(
        "playlistItems",
        {
            "part": "snippet,contentDetails",
            "playlistId": playlist_id,
            "maxResults": min(max_results, 50),
            "key": api_key,
        },
    )

    items = data.get("items", [])

    results: List[Dict[str, Any]] = []

    for item in items:
        snippet = item.get("snippet", {})
        content_details = item.get(
            "contentDetails",
            {},
        )

        video_id = (
            content_details.get("videoId")
            or snippet.get("resourceId", {}).get("videoId")
        )

        if not video_id:
            continue

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
                "thumbnail": (
                    snippet.get("thumbnails", {})
                    .get("high", {})
                    .get("url")
                ),
                "url": (
                    f"https://www.youtube.com/watch?v={video_id}"
                ),
            }
        )

    return results


def get_latest_videos(
    api_key: str,
    channel_id: str,
    max_results: int = 10,
) -> List[Dict[str, Any]]:
    """
    取得指定頻道最新影片。
    """

    playlist_id = get_upload_playlist(
        api_key,
        channel_id,
    )

    return get_latest_videos_from_playlist(
        api_key,
        playlist_id,
        max_results,
    )


def get_channel_latest_videos(
    api_key: str,
    channel_id: Optional[str] = None,
    handle: Optional[str] = None,
    max_results: int = 10,
) -> List[Dict[str, Any]]:
    """
    使用 Channel ID 或 @handle 取得頻道最新影片。
    """

    channel = resolve_channel(
        api_key=api_key,
        channel_id=channel_id,
        handle=handle,
    )

    resolved_channel_id = channel.get("id")

    if not resolved_channel_id:
        raise YouTubeAPIError(
            "YouTube 頻道資料缺少 channel ID"
        )

    return get_latest_videos(
        api_key,
        resolved_channel_id,
        max_results,
    )


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
