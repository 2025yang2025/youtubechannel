# YouTube AI → Telegram V2（免費優先）

目標：

盡可能使用免費資源，
自動監控 YouTube 頻道、
取得字幕、
分析重點，
再推送到 Telegram。


## 免費優先架構

1. GitHub Actions
2. YouTube Data API
3. youtube-transcript-api
4. Gemini（可選）
5. 規則式分析
6. Telegram Bot API
7. GitHub state.json


## 流程

YouTube
→ 新影片偵測
→ 字幕
→ Gemini
→ AI 不可用時規則式摘要
→ 重要度評分
→ Telegram


## GitHub Secrets

必要：

YOUTUBE_API_KEY

TELEGRAM_BOT_TOKEN

TELEGRAM_CHAT_ID


可選：

GEMINI_API_KEY

GEMINI_MODEL


## 頻道設定

config/channels.yaml


例如：

channels:

  - name: 我的財經頻道

    channel_id: UCxxxxxxxxxxxxxxxxxxxx

    enabled: true

    keywords:
      - 台股
      - 台積電
      - AI
      - 半導體

    min_score: 50


## 第一次執行

預設：

mark_existing_as_processed: true


第一次只建立已處理影片清單。


## 完全免費模式

如果沒有 GEMINI_API_KEY：

系統仍然可以：

- 找新影片
- 取得字幕
- 擷取關鍵句
- 擷取數字
- 擷取百分比
- 關鍵字分析
- 分類
- 重要度評分
- Telegram 推播


## Gemini 模式

如果設定 GEMINI_API_KEY：

優先使用 Gemini。


如果 Gemini 失敗：

自動回到規則式分析。


## GitHub Actions

每 30 分鐘執行一次。


## 後續功能

- 每日總結
- 多頻道交叉分析
- 股票代號辨識
- 台股/美股/AI/半導體分類
- Telegram Topic
- SQLite
- Web 管理頁面
