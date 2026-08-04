import os
import json
import requests
import feedparser
from youtube_transcript_api import YouTubeTranscriptApi
import google.generativeai as genai

# ================= 1. 環境變數讀取 =================
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# 欲監控的 YouTube 頻道 RSS 清單 (可填寫多個)
CHANNELS = [
    {"name": "頻道 A", "rss": "https://www.youtube.com/feeds/videos.xml?channel_id=UCX6OQ3DkcsbYNE6H8uQQuVA"},
]

DB_FILE = "processed_videos.json"

# ================= 2. 輔助功能函式 =================
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
        print(f"無法獲取字幕 (Video ID: {video_id}): {e}")
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
    
    res = requests.post(url, json=payload)
    if res.status_code != 200:
        print(f"Telegram 發送失敗: {res.text}")

# ================= 3. 主流程 =================
def main():
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        raise ValueError("請先至 GitHub Secrets 設定 TELEGRAM_BOT_TOKEN 與 TELEGRAM_CHAT_ID！")

    processed_ids = load_processed_ids()
    has_new_video = False

    for ch in CHANNELS:
        video = get_latest_video(ch["rss"])
        if not video:
            continue

        video_id = video["id"]

        # 檢查是否已處理過
        if video_id in processed_ids:
            print(f"影片 [{video['title']}] 已發送過，跳過。")
            continue

        print(f"發現新影片：{video['title']}，開始處理...")

        # 抓取字幕並摘要
        transcript = fetch_transcript(video_id)
        if transcript:
            summary = generate_summary(video["title"], transcript)
        else:
            summary = "（此影片暫無字幕可供 AI 摘要分析）"

        # 發送 Telegram 訊息
        send_telegram(video["title"], video["link"], summary)

        # 記錄 ID
        processed_ids.add(video_id)
        has_new_video = True

    # 儲存紀錄檔
    if has_new_video:
        save_processed_ids(processed_ids)
        print("已更新發送紀錄檔案。")

if __name__ == "__main__":
    main()
