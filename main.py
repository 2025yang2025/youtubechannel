import os
import re
import requests
import feedparser
from youtube_transcript_api import YouTubeTranscriptApi
from google import genai

# ================= 1. 環境變數讀取 =================
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# ================= 2. 欲整合分析的目標清單 (已更新正確 RSS ID) =================
TARGETS = [
    {
        "name": "請支援輸贏",
        "rss": "https://www.youtube.com/feeds/videos.xml?playlist_id=PL6XmsUWSei7yjLRhblIP1QxCCrwQlsdI4",
        "fetch_count": 3
    },
    {
        "name": "總編當莊",
        "rss": "https://www.youtube.com/feeds/videos.xml?channel_id=UCg4sI1KkI3W7N5K6dOAnxKw",
        "fetch_count": 3
    },
    {
        "name": "陳威良 股市全威 (考股學家)",
        "rss": "https://www.youtube.com/feeds/videos.xml?channel_id=UCccS6U6vRkB3UjJ9oJ54E3w",
        "fetch_count": 3
    },
    {
        "name": "《產經希引力》從趨勢找好產業",
        "rss": "https://www.youtube.com/feeds/videos.xml?playlist_id=PLj52IfHdKHFdwnebZKoWGaBVcCRpWV7Ju",
        "fetch_count": 3
    },
]

# ================= 3. 核心與輔助函式 =================
def fetch_rss_feed(rss_url):
    """帶上 Header 發送 Request，若失敗則降級直接使用 feedparser 解析"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "application/xml,text/xml,*/*;q=0.9"
    }
    try:
        response = requests.get(rss_url, headers=headers, timeout=15)
        if response.status_code == 200:
            return feedparser.parse(response.content)
        else:
            print(f"⚠️ HTTP 狀態碼 ({response.status_code})，切換至 Direct Feed Parsing...")
    except Exception as e:
        print(f"⚠️ Request 發生例外 ({e})，切換至 Direct Feed Parsing...")

    # Fallback 直接交給 feedparser
    return feedparser.parse(rss_url)

def fetch_videos_info(rss_url, count=3):
    """讀取最新的 N 支影片資訊與逐字稿"""
    feed = fetch_rss_feed(rss_url)
    if not feed or not feed.entries:
        print(f"⚠️ RSS 解析結果為空: {rss_url}")
        return []

    videos_data = []
    yt_api = YouTubeTranscriptApi()

    for entry in feed.entries[:count]:
        if hasattr(entry, 'yt_videoid'):
            video_id = entry.yt_videoid
        else:
            match = re.search(r'v=([a-zA-Z0-9_-]+)', entry.link)
            video_id = match.group(1) if match else entry.link.split("/")[-1]

        title = entry.title
        link = f"https://www.youtube.com/watch?v={video_id}"

        # 抓取逐字稿 (優先抓繁中/簡中/英文，支援自動生成字幕)
        transcript_text = ""
        try:
            transcript_list = yt_api.list_transcripts(video_id)
            try:
                transcript = transcript_list.find_transcript(['zh-TW', 'zh-Hant', 'zh', 'en'])
            except Exception:
                transcript = transcript_list.find_generated_transcript(['zh-TW', 'zh-Hant', 'zh', 'en'])
            
            fetched_data = transcript.fetch()
            transcript_text = " ".join([t['text'] for t in fetched_data])
        except Exception:
            transcript_text = "（無法取得字幕或該影片無提供字幕）"

        videos_data.append({
            "id": video_id,
            "title": title,
            "link": link,
            "transcript": transcript_text
        })

    return videos_data

def generate_combined_analysis(target_name, videos_data):
    """呼叫 Google GenAI SDK 進行綜合分析報告"""
    if not GEMINI_API_KEY:
        return "⚠️ 未設定 GEMINI_API_KEY，無法進行 AI 整合分析。"

    client = genai.Client(api_key=GEMINI_API_KEY)

    context_text = ""
    for idx, v in enumerate(videos_data, 1):
        context_text += f"\n--- 影片 {idx} ---\n"
        context_text += f"標題：{v['title']}\n"
        context_text += f"連結：{v['link']}\n"
        context_text += f"逐字稿內容：{v['transcript'][:3000]}\n"

    prompt = f"""
你是一名專業的財經數據與產業內容分析師。請針對【{target_name}】最近發布的 {len(videos_data)} 支 YouTube 影片內容進行「跨影片綜合整合分析報告」。

分析素材如下：
{context_text}

請以繁體中文回覆，報告結構需包含：
1. 🎯 **核心主題與總體脈絡**：這幾支影片共同探討的主要議題、市場趨勢或核心邏輯是什麼？
2. 💡 **關鍵整合與分析結果**：
   - 綜合多支影片提出的重點觀察、提及的重點公司/產業與數據分析。
   - 影片之間是否有前後呼應、遞進關係或重點對比？
3. 📌 **總結與可行性建議**：給投資人/觀看者的核心總結建議與觀察指標。

請保持內容結構清晰、重點突出，適合在手機通訊軟體上閱讀。
"""

    try:
        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=prompt,
        )
        return response.text
    except Exception as e:
        return f"⚠️ 綜合分析生成失敗：{e}"

def send_telegram(target_name, videos_data, analysis_result):
    """將整合分析報告發送至 Telegram"""
    video_links_str = "\n".join([f"• [{v['title']}]({v['link']})" for v in videos_data])

    message = f"📊 *【{target_name}】跨影片綜合整合分析報告*\n\n"
    message += f"🎬 *分析影片來源 ({len(videos_data)} 支)：*\n{video_links_str}\n\n"
    message += f"-----------------------------------\n\n"
    message += analysis_result

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True
    }

    res = requests.post(url, json=payload, timeout=20)
    if res.status_code != 200:
        payload["parse_mode"] = ""
        requests.post(url, json=payload, timeout=20)

# ================= 4. 主流程 =================
def main():
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        raise ValueError("請先至 GitHub Secrets 設定 TELEGRAM_BOT_TOKEN 與 TELEGRAM_CHAT_ID！")

    for target in TARGETS:
        target_name = target.get("name", "頻道/播放清單")
        rss_url = target.get("rss")

        fetch_count = target.get("fetch_count", 3)
        print(f"🚀 正在讀取 [{target_name}] 最近 {fetch_count} 支影片資訊與逐字稿...")

        videos_data = fetch_videos_info(rss_url, count=fetch_count)
        if not videos_data:
            print(f"ℹ️ [{target_name}] 未抓取到任何影片。")
            continue

        print(f"🤖 正在呼叫 Gemini AI 進行跨影片整合分析...")
        analysis_result = generate_combined_analysis(target_name, videos_data)

        print(f"📤 正在發送整合分析報告至 Telegram...")
        send_telegram(target_name, videos_data, analysis_result)
        print(f"✅ [{target_name}] 分析報告發送完成！\n")

if __name__ == "__main__":
    main()
