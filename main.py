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

# 欲整合分析的目標（頻道網址、播放清單網址皆可）
TARGETS = [
    {
        "name": "請支援輸贏",
        "url": "https://www.youtube.com/playlist?list=PL6XmsUWSei7yjLRhblIP1QxCCrwQlsdI4",
        "fetch_count": 3  # 設定每次整合分析最近幾支影片
    },
    {
        "name": "總編當莊",
        "url": "https://www.youtube.com/@berich888/featured",
        "fetch_count": 3  # 設定每次整合分析最近幾支影片
    },
    {
        "name": "陳威良 股市全威 (考股學家)",
        "url": "https://www.youtube.com/@ccstock888",
        "fetch_count": 3  # 設定每次整合分析最近幾支影片
    },
     {
        "name": "《產經希引力》從趨勢找好產業",
        "url": "https://www.youtube.com/playlist?list=PLj52IfHdKHFdwnebZKoWGaBVcCRpWV7Ju",
        "fetch_count": 3  # 設定每次整合分析最近幾支影片
    },
]

# ================= 2. 輔助函式 =================
def get_rss_url(url):
    """將頻道或播放清單網址轉為 RSS 網址"""
    if not url:
        return None
    if "channel_id=" in url or "playlist_id=" in url:
        return url
    if "list=" in url:
        match = re.search(r'list=([a-zA-Z0-9_-]+)', url)
        if match:
            return f"https://www.youtube.com/feeds/videos.xml?playlist_id={match.group(1)}"
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(url, headers=headers, timeout=10)
        match = re.search(r'channel_id=([a-zA-Z0-9_-]{24})', res.text)
        if match:
            return f"https://www.youtube.com/feeds/videos.xml?channel_id={match.group(1)}"
    except Exception as e:
        print(f"⚠️ 解析網址失敗 [{url}]: {e}")
    return None

def fetch_videos_info(rss_url, count=3):
    """讀取最新的 N 支影片資訊與逐字稿"""
    feed = feedparser.parse(rss_url)
    videos_data = []
    
    for entry in feed.entries[:count]:
        if hasattr(entry, 'yt_videoid'):
            video_id = entry.yt_videoid
        else:
            match = re.search(r'v=([a-zA-Z0-9_-]+)', entry.link)
            video_id = match.group(1) if match else entry.link.split("/")[-1]
            
        title = entry.title
        link = f"https://www.youtube.com/watch?v={video_id}"
        
        # 抓取逐字稿
        transcript_text = ""
        try:
            transcript_list = YouTubeTranscriptApi.get_transcript(
                video_id, languages=['zh-TW', 'zh-Hant', 'zh', 'en']
            )
            transcript_text = " ".join([t['text'] for t in transcript_list])
        except Exception:
            transcript_text = "（無法取得字幕）"

        videos_data.append({
            "id": video_id,
            "title": title,
            "link": link,
            "transcript": transcript_text
        })
        
    return videos_data

def generate_combined_analysis(target_name, videos_data):
    """將多支影片資訊整合後，呼叫 Gemini 進行綜合分析報告」"""
    if not GEMINI_API_KEY:
        return "⚠️ 未設定 GEMINI_API_KEY，無法進行 AI 整合分析。"

    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-2.0-flash')

    # 組合多支影片的文本 context
    context_text = ""
    for idx, v in enumerate(videos_data, 1):
        context_text += f"\n--- 影片 {idx} ---\n"
        context_text += f"標題：{v['title']}\n"
        context_text += f"連結：{v['link']}\n"
        context_text += f"逐字稿內容摘要：{v['transcript'][:2000]}\n"

    prompt = f"""
你是一名專業的數據與內容分析師。請針對【{target_name}】最近發布的 {len(videos_data)} 支 YouTube 影片內容進行「跨影片綜合整合分析報告」。

分析素材如下：
{context_text}

請以繁體中文回覆，報告結構需包含：
1. 🎯 **核心主題與總體脈絡**：這幾支影片共同探討的主要議題或核心邏輯是什麼？
2. 💡 **關鍵整合與分析結果**：
   - 綜合多支影片提出的重點觀察與數據分析。
   - 影片之間是否有前後呼應、遞進關係或立場對比？
3. 📌 **總結與可行性建議**：給觀看者的核心總結建議。

請保持內容結構清晰、重點突出，適合在手機通訊軟體上閱讀。
"""

    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"⚠️ 綜合分析生成失敗：{e}"

def send_telegram(target_name, videos_data, analysis_result):
    """將整合分析報告發送至 Telegram"""
    # 建立影片清單區塊
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
        # 如果因為 Markdown 格式解析失敗，退回純文字發送
        payload["parse_mode"] = ""
        requests.post(url, json=payload, timeout=20)

# ================= 3. 主流程 =================
def main():
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        raise ValueError("請先至 GitHub Secrets 設定 TELEGRAM_BOT_TOKEN 與 TELEGRAM_CHAT_ID！")

    for target in TARGETS:
        target_name = target.get("name", "頻道/播放清單")
        rss_url = get_rss_url(target.get("url"))

        if not rss_url:
            print(f"❌ 無法讀取 [{target_name}] 的 RSS Feed。")
            continue

        fetch_count = target.get("fetch_count", 3)
        print(f"🚀 正在讀取 [{target_name}] 最近 {fetch_count} 支影片資訊與逐字稿...")
        
        videos_data = fetch_videos_info(rss_url, count=fetch_count)
        if not videos_data:
            print(f"ℹ️ [{target_name}] 未抓取到任何影片。")
            continue

        print(f"🤖 正在呼叫 AI 進行跨影片整合分析...")
        analysis_result = generate_combined_analysis(target_name, videos_data)

        print(f"📤 正在發送整合分析報告至 Telegram...")
        send_telegram(target_name, videos_data, analysis_result)
        print("✅ 完成發送！")

if __name__ == "__main__":
    main()
