from __future__ import annotations
import logging
from urllib.parse import unquote
from googleapiclient.discovery import build
class YouTubeAPIError(RuntimeError): pass
def _service(key): return build("youtube","v3",developerKey=key,cache_discovery=False)
def _handle(h):
    h=unquote((h or "").strip())
    return h if h.startswith("@") else ("@"+h if h else "")
def resolve_channel_id(api_key, channel):
    if channel.channel_id and not channel.channel_id.startswith("UC_REPLACE"): return channel.channel_id
    h=_handle(channel.handle)
    if not h: raise YouTubeAPIError(f"頻道沒有 channel_id/handle: {channel.name}")
    yt=_service(api_key)
    r=yt.channels().list(part="snippet,contentDetails",forHandle=h[1:],maxResults=1).execute()
    items=r.get("items",[])
    if not items:
        r=yt.search().list(part="snippet",q=h,type="channel",maxResults=5).execute(); items=r.get("items",[])
    if not items: raise YouTubeAPIError(f"找不到頻道: {channel.name} ({h})")
    cid=items[0].get("id",{}).get("channelId") or items[0].get("id")
    if not cid: raise YouTubeAPIError(f"找不到 channel_id: {channel.name}")
    return cid
def get_latest_videos(api_key, channel, max_videos=1):
    yt=_service(api_key); cid=resolve_channel_id(api_key,channel)
    r=yt.channels().list(part="contentDetails",id=cid,maxResults=1).execute()
    if not r.get("items"): raise YouTubeAPIError(f"找不到頻道: {channel.name}")
    uploads=r["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
    r=yt.playlistItems().list(part="snippet,contentDetails",playlistId=uploads,maxResults=max(1,min(max_videos,10))).execute()
    out=[]
    for i in r.get("items",[]):
        s=i.get("snippet",{}); vid=s.get("resourceId",{}).get("videoId")
        if vid: out.append({"video_id":vid,"channel_id":cid,"channel_name":channel.name,"title":s.get("title","").strip(),"description":s.get("description","").strip(),"published_at":s.get("publishedAt","")})
    logging.info("Found %s videos: %s",len(out),channel.name); return out
