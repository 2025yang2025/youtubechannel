from __future__ import annotations

import logging
from urllib.parse import unquote

from googleapiclient.discovery import build


class YouTubeAPIError(RuntimeError):
    pass


def _service(key: str):
    return build("youtube", "v3", developerKey=key, cache_discovery=False)


def _handle(value: str) -> str:
    value = unquote((value or "").strip())
    if not value:
        return ""
    return value if value.startswith("@") else f"@{value}"


def _normalise_handle(value: str) -> str:
    return _handle(value).lstrip("@").strip().lower()


def _extract_channel_id(item: dict) -> str:
    """Handle both channels.list and search.list response shapes.

    channels.list usually returns id as a string. search.list also returns
    id as a string (the previous code incorrectly assumed id was always a dict).
    """
    item_id = item.get("id", "")
    if isinstance(item_id, dict):
        return str(
            item_id.get("channelId")
            or item_id.get("videoId")
            or item_id.get("playlistId")
            or ""
        ).strip()
    return str(item_id or "").strip()


def resolve_channel_id(api_key: str, channel) -> str:
    """Resolve a configured channel_id or @handle into a real channel ID."""
    configured_id = (getattr(channel, "channel_id", "") or "").strip()
    if configured_id and not configured_id.startswith("UC_REPLACE"):
        return configured_id

    handle = _handle(getattr(channel, "handle", ""))
    if not handle:
        raise YouTubeAPIError(f"頻道沒有 channel_id/handle: {channel.name}")

    yt = _service(api_key)

    # Preferred method: channels.list supports forHandle.
    try:
        response = (
            yt.channels()
            .list(part="snippet,contentDetails", forHandle=handle[1:], maxResults=1)
            .execute()
        )
        items = response.get("items", []) or []
        if items:
            cid = _extract_channel_id(items[0])
            if cid:
                logging.info("Resolved channel: %s -> %s", handle, cid)
                return cid
    except Exception as exc:
        logging.warning("forHandle lookup failed %s: %s", handle, str(exc).splitlines()[0][:200])

    # Fallback: search.list returns searchResult.id as a STRING.
    # Select the closest handle/title match instead of blindly taking items[0].
    response = (
        yt.search()
        .list(part="snippet", q=handle, type="channel", maxResults=10)
        .execute()
    )
    items = response.get("items", []) or []
    wanted = _normalise_handle(handle)

    best_id = ""
    best_score = -1
    for item in items:
        cid = _extract_channel_id(item)
        snippet = item.get("snippet", {}) or {}
        title = str(snippet.get("title", "")).strip()
        custom_url = str(snippet.get("customUrl", "")).strip()
        score = 0
        if _normalise_handle(custom_url) == wanted:
            score += 100
        if _normalise_handle(title) == wanted:
            score += 80
        if wanted and wanted in _normalise_handle(title):
            score += 20
        if cid and score > best_score:
            best_score = score
            best_id = cid

    if best_id:
        logging.info("Resolved channel by search: %s -> %s", handle, best_id)
        return best_id

    raise YouTubeAPIError(f"找不到頻道: {channel.name} ({handle})")


def get_latest_videos(api_key: str, channel, max_videos: int = 1) -> list[dict]:
    yt = _service(api_key)
    cid = resolve_channel_id(api_key, channel)

    response = (
        yt.channels()
        .list(part="contentDetails,snippet", id=cid, maxResults=1)
        .execute()
    )
    items = response.get("items", []) or []
    if not items:
        raise YouTubeAPIError(f"找不到頻道: {channel.name} ({cid})")

    uploads = (
        items[0]
        .get("contentDetails", {})
        .get("relatedPlaylists", {})
        .get("uploads", "")
    )
    if not uploads:
        raise YouTubeAPIError(f"找不到頻道上傳清單: {channel.name}")

    count = max(1, min(int(max_videos), 10))
    response = (
        yt.playlistItems()
        .list(
            part="snippet,contentDetails",
            playlistId=uploads,
            maxResults=count,
        )
        .execute()
    )

    out: list[dict] = []
    for item in response.get("items", []) or []:
        snippet = item.get("snippet", {}) or {}
        resource = snippet.get("resourceId", {}) or {}
        video_id = str(resource.get("videoId", "")).strip()
        if not video_id:
            continue

        out.append(
            {
                "video_id": video_id,
                "channel_id": cid,
                "channel_name": channel.name,
                "title": str(snippet.get("title", "")).strip(),
                "description": str(snippet.get("description", "")).strip(),
                "published_at": str(snippet.get("publishedAt", "")).strip(),
                "url": f"https://www.youtube.com/watch?v={video_id}",
            }
        )

    logging.info("Found %s videos: %s", len(out), channel.name)
    return out
