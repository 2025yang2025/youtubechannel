from __future__ import annotations
from datetime import datetime, timezone
import requests

class YouTubeAPIError(RuntimeError):
    pass

API_ROOT = "https://www.googleapis.com/youtube/v3"

def _get(endpoint, params):
    r = requests.get(f"{API_ROOT}/{endpoint}", params=params, timeout=20)
    if r.status_code != 200:
        try: detail = r.json()
        except Exception: detail = r.text
        raise YouTubeAPIError(f"YouTube API {r.status_code}: {detail}")
    return r.json()

def resolve_channel(api_key, channel):
    cid = str(getattr(channel, "channel_id", "") or "").strip()
    if cid: return cid
    handle = str(getattr(channel, "handle", "") or "").strip().lstrip("@")
    if not handle:
        raise YouTubeAPIError(f"頻道 {getattr(channel,'name','')} 沒有 channel_id 或 handle。")
    data = _get("channels", {"part":"id,snippet,contentDetails","forHandle":handle,"key":api_key})
    items = data.get("items", [])
    if not items: raise YouTubeAPIError(f"找不到 YouTube 頻道 handle: @{handle}")
    return items[0]["id"]

def get_upload_playlist(api_key, channel):
    cid = resolve_channel(api_key, channel)
    data = _get("channels", {"part":"contentDetails","id":cid,"key":api_key})
    items = data.get("items", [])
    if not items: raise YouTubeAPIError(f"找不到頻道: {cid}")
    return items[0]["contentDetails"]["relatedPlaylists"]["uploads"]

def get_latest_videos(api_key, channel, max_videos=1):
    playlist = get_upload_playlist(api_key, channel)
    data = _get("playlistItems", {
        "part":"snippet,contentDetails","playlistId":playlist,
        "maxResults":min(max(max_videos*2,5),50),"key":api_key
    })
    candidates = []
    for item in data.get("items", []):
        sn = item.get("snippet", {})
        vid = item.get("contentDetails", {}).get("videoId") or sn.get("resourceId", {}).get("videoId")
        if vid:
            candidates.append({"video_id":vid,"title":sn.get("title",""),"description":sn.get("description",""),
                               "published_at":sn.get("publishedAt",""),"channel_name":getattr(channel,"name",""),
                               "channel_id":sn.get("channelId",""),"handle":getattr(channel,"handle",""),
                               "url":f"https://www.youtube.com/watch?v={vid}"})
    if not candidates: return []
    ids = ",".join(v["video_id"] for v in candidates)
    detail = _get("videos", {"part":"snippet,liveStreamingDetails,status","id":ids,"key":api_key})
    dm = {x["id"]:x for x in detail.get("items",[])}
    now = datetime.now(timezone.utc)
    result = []
    for v in candidates:
        d = dm.get(v["video_id"], {})
        sn = d.get("snippet", {})
        live = d.get("liveStreamingDetails", {})
        v["live_broadcast_content"] = sn.get("liveBroadcastContent","none")
        v["scheduled_start_time"] = live.get("scheduledStartTime","")
        if v["scheduled_start_time"] and v["live_broadcast_content"] == "upcoming":
            try:
                dt = datetime.fromisoformat(v["scheduled_start_time"].replace("Z","+00:00"))
                if dt > now: continue
            except Exception: pass
        if sn.get("title"): v["title"] = sn["title"]
        if "description" in sn: v["description"] = sn["description"]
        result.append(v)
        if len(result) >= max_videos: break
    return result
