import os
import time
import requests
import yt_dlp
from youtube_transcript_api import YouTubeTranscriptApi
from google import genai
from tenacity import retry, stop_after_attempt, wait_exponential

# ================= 1. 環境變數讀取 =================
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# ================= 2. 欲整合分析的目標清單 (調整為各 1 支) =================
TARGETS = [
    {
        "name": "請支援輸贏",
        "url": "https://www.youtube.com/playlist?list=PL6XmsUWSei7yjLRhblIP1QxCCrwQlsdI4",
        "fetch_count": 1
    },
    {
        "name": "總編當莊",
        "url": "https://www.youtube.com/channel/UCg4sI1KkI3W7N5K6dOAnxKw/videos",
        "fetch_count": 1
    },
    {
        "name": "陳威良 股市全威 (考股學家)",
        "url": "https://www.youtube.com/channel/UCccS6U6vRkB3UjJ9oJ54E3w/videos",
        "fetch_count": 1
    },
    {
        "name": "《產經希引力》從趨勢找好產業",
        "url": "https://www.youtube.com/playlist?list=PLj52IfHdKHFdwnebZKoWGaBVcCRpWV7Ju",
        "fetch_count": 1
    },
]

# ================= 3. 核心與輔助函式 =================
def fetch_videos_info(target):
    """使用 yt-dlp 抓取頻道或播放清單最新的影片資訊與逐字稿"""
    fetch_count = target.get("fetch_count", 1)
    target_url = target.get("url")

    print(f"🚀 正在獲取 [{target['name']}] 最新 {fetch_count} 支影片...")

    ydl_opts = {
        'extract_flat': True,
        'playlistend': fetch_count,
        'quiet': True,
        'no_warnings': True,
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    }

    videos_data = []
    yt_api = YouTubeTranscriptApi()

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(target_url, download=False)
            entries = info.get('entries', [])

            for entry in entries:
                if not entry:
                    continue
                video_id = entry.get('id')
                title = entry.get('title', '無標題影片')
                link = f"https://www.youtube.com/watch?v={video_id}"

                # 抓取字幕/逐字稿
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

    except Exception as e:
        print(f"⚠️ 讀取影片清單失敗 [{target['name']}]: {e}")

    return videos_data

# 使用 gemini-2.0-flash-lite，並設置自動重試與退避時間
@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=5, min=20, max=60),
    reraise=True
)
def call_gemini_api(client, prompt):
    return client.models.generate_content(
        model='gemini-2.0-flash-lite',
        contents=prompt,
    )

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
        # 單支影片截取精華 1500 字
        context_text += f"逐字稿內容：{v['transcript'][:1500]}\n"

    prompt = f"""
你是一名專業的財經數據與產業內容分析師。請針對【{target_name}】最新發布的影片內容進行重點摘要與投資分析報告。

分析素材如下：
{context_text}

請以繁體中文回覆，報告結構需包含：
1. 🎯 **核心主題與總體脈絡**：這支影片探討的主要議題、市場趨勢或核心邏輯是什麼？
2. 💡 **關鍵分析結果**：
   - 影片提出的重點觀察、提及的重點公司/產業與數據分析。
3. 📌 **總結與可行性建議**：給投資人/觀看者的核心總結建議與觀察指標。

請保持內容結構清晰、重點突出，適合在手機通訊軟體上閱讀。
"""

    try:
        response = call_gemini_api(client, prompt)
        return response.text
    except Exception as e:
        return f"⚠️ 綜合分析生成失敗：{e}"

def send_telegram(target_name, videos_data, analysis_result):
    """將整合分析報告發送至 Telegram"""
    video_links_str = "\n".join([f"• [{v['title']}]({v['link']})" for v in videos_data])

    message = f"📊 *【{target_name}】最新影片精華分析報告*\n\n"
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
        # Markdown 格式發送失敗時備援改用純文字
        payload["parse_mode"] = ""
        requests.post(url, json=payload, timeout=20)

# ================= 4. 主流程 =================
def main():
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        raise ValueError("請先至 GitHub Secrets 設定 TELEGRAM_BOT_TOKEN 與 TELEGRAM_CHAT_ID！")

    for idx, target in enumerate(TARGETS):
        target_name = target.get("name", "頻道/播放清單")
        
        videos_data = fetch_videos_info(target)
        if not videos_data:
            print(f"ℹ️ [{target_name}] 未抓取到任何影片。")
            continue

        print(f"🤖 正在呼叫 Gemini AI 進行分析...")
        analysis_result = generate_combined_analysis(target_name, videos_data)

        print(f"📤 正在發送分析報告至 Telegram...")
        send_telegram(target_name, videos_data, analysis_result)
        print(f"✅ [{target_name}] 分析報告發送完成！\n")

        # 每個目標之間間隔 25 秒，保護 API 不衝過頭
        if idx < len(TARGETS) - 1:
            print("⏳ 等待 25 秒後繼續下一個頻道...")
            time.sleep(25)

if __name__ == "__main__":
    main()
