import os
import re
import json
import requests
import feedparser
from youtube_transcript_api import YouTubeTranscriptApi
import google.generativeai as genai

# ================= 1. 環境變數讀取 =================
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# ================= 2. 頻道設定 (可自由替換或新增頻道網址) =================
# 你可以直接填寫頻道網址 (url) 或標準 RSS 網址 (rss)
CHANNELS = [
     {
        "name": "請支援輸贏",
        "url": "https://www.youtube.com/playlist?list=PL6XmsUWSei7yjLRhblIP1QxCCrwQlsdI4"
    },
    # 範例：若想新增頻道，只需像下面這樣繼續增加：
    # {
    #     "name": "頻道名稱",
    #     "url": "https://www.youtube.com/@頻道Handle"
    # },
]

DB_FILE = "processed_videos.json"

# ================= 3. 核心與輔助功能函式 =================
def load_processed_ids():
    """載入已發送過的影片 ID 記錄"""
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                return set(json.load(f))
        except Exception:
            return set()
    return set()

def save_processed_ids(processed_ids):
    """保存已發送過的影片 ID 記錄"""
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(list(processed_ids), f, ensure_ascii=False, indent=2)

def get_rss_by_youtube_url(url):
    """將一般 YouTube 頻道網址自動轉為 RSS Feed 網址"""
    if not url:
        return None
    if "channel_id=" in url:
        return url  # 本身已經是 RSS 網址

    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        res = requests.get(url, headers=headers, timeout=10)
        match = re.search(r'channel_id=([a-zA-Z0-9_-]{24})', res.text)
        if match:
            channel_id = match.group(1)
            return f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
    except Exception as e:
        print(f"⚠️ 解析頻道網址失敗 [{url}]: {e}")
    return None

def get_latest_video(rss_url):
    """從 RSS 獲取最新一支影片資訊"""
    feed = feedparser.parse(rss_url)
    if feed.entries:
        latest = feed.entries[0]
        video_id = latest.yt_videoid if hasattr(latest, 'yt_videoid') else latest.link.split("v=")[-1]
        return {
            "title": latest.title,
            "link": latest.link,
            "id": video_id
        }
    return None

def fetch_transcript(video_id):
    """取得影片字幕，優先抓取繁中/簡中/英文"""
    try:
        transcript_list = YouTubeTranscriptApi.get_transcript(
            video_id, 
            languages=['zh-TW', 'zh-Hant', 'zh', 'en']
        )
        full_text = " ".join([t['text'] for t in transcript_list])
        return full_text
    except Exception as e:
        print(f"ℹ️ 無法獲取字幕 (Video ID: {video_id}): {e}")
        return None

def generate_summary(title, transcript_text):
    """呼叫 Gemini AI 進行重點摘要"""
    if not GEMINI_API_KEY:
        return "⚠️ 未設定 GEMINI_API_KEY，跳過 AI 摘要。"

    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash')

    prompt = f"""
你是一個專業的內容摘要助手。請針對以下 YouTube 影片的標題與逐字稿，用繁體中文整理出 3 至 5 個核心重點摘要與總結。

影片標題：{title}
影片逐字稿內容：
{transcript_text[:5000]}
"""
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"⚠️ AI 摘要生成失敗：{e}"

def send_telegram(title, link, summary):
    """發送訊息至 Telegram"""
    message = f"🎬 *{title}*\n🔗 {link}\n\n🤖 *AI 內容重點摘要：*\n{summary}"
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown",
        "disable_web_page_preview": False
    }
    
    res = requests.post(url, json=payload, timeout=10)
    if res.status_code != 200:
        print(f"❌ Telegram 發送失敗: {res.text}")

# ================= 4. 主流程 =================
def main():
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        raise ValueError("請先至 GitHub Secrets 設定 TELEGRAM_BOT_TOKEN 與 TELEGRAM_CHAT_ID！")

    processed_ids = load_processed_ids()
    has_new_video = False

    for ch in CHANNELS:
        ch_name = ch.get("name", "未命名頻道")
        rss_url = ch.get("rss") or get_rss_by_youtube_url(ch.get("url"))

        if not rss_url:
            print(f"❌ 無法獲取 [{ch_name}] 的 RSS Feed，跳過處理。")
            continue

        video = get_latest_video(rss_url)
        if not video:
            print(f"ℹ️ [{ch_name}] 暫無最新影片。")
            continue

        video_id = video["id"]

        # 檢查是否已發送過
        if video_id in processed_ids:
            print(f"▶️ 頻道 [{ch_name}] 的影片 [{video['title']}] 已發送過，跳過。")
            continue

        print(f"🚀 發現 [{ch_name}] 的新影片：{video['title']}，開始處理...")

        # 抓取字幕並摘要
        transcript = fetch_transcript(video_id)
        if transcript:
            summary = generate_summary(video["title"], transcript)
        else:
            summary = "（此影片暫無官方/自動字幕可供 AI 摘要分析）"

        # 發送 Telegram 訊息
        send_telegram(video["title"], video["link"], summary)

        # 記錄 ID
        processed_ids.add(video_id)
        has_new_video = True

    # 儲存紀錄檔
    if has_new_video:
        save_processed_ids(processed_ids)
        print("✅ 已更新 processed_videos.json 歷史發送紀錄。")
    else:
        print("✅ 檢查完畢，無新影片需推送。")

if __name__ == "__main__":
    main()
