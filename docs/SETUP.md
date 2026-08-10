# V2 免費優先設定

## 必要 Secrets

YOUTUBE_API_KEY

TELEGRAM_BOT_TOKEN

TELEGRAM_CHAT_ID


## 可選 Secret

GEMINI_API_KEY

GEMINI_MODEL


沒有 Gemini：

YouTube
→ 字幕
→ 規則式分析
→ Telegram


有 Gemini：

YouTube
→ 字幕
→ Gemini
→ Telegram


Gemini 發生錯誤：

Gemini
↓
規則式分析
↓
Telegram


## Telegram

建立 Bot 後，
把 Bot 加入你的目標群組或頻道，
再設定 Chat ID。


## YouTube

取得 API Key 後，
修改：

config/channels.yaml


## 測試策略

第一次：

mark_existing_as_processed: true


確認 workflow 正常。


之後：

mark_existing_as_processed: false


測試新影片。


## 注意

免費額度、API quota、模型可用性會隨服務商政策變動，
所以本專案不把任何單一 AI 服務設為必要條件。
