from __future__ import annotations
import logging,re
from youtube_transcript_api import YouTubeTranscriptApi
def _clean(s): return re.sub(r"\s+"," ",s or "").strip()
def usable_text(text, minimum=80):
    t=_clean(text)
    if len(t)<minimum: return False
    letters=len(re.findall(r"[A-Za-z\u4e00-\u9fff]",t)); digits=len(re.findall(r"\d",t)); urls=len(re.findall(r"https?://|www\.",t,re.I))
    return letters>=25 and digits<=letters*3 and urls<4
def get_transcript(video_id,languages):
    try:
        api=YouTubeTranscriptApi(); fetched=api.fetch(video_id,languages=languages)
        text=_clean(" ".join(getattr(x,"text",str(x)) for x in fetched))
        if text: return text,"transcript"
    except Exception as e: logging.warning("字幕取得失敗 %s: %s",video_id,str(e).splitlines()[0][:250])
    return "","none"
