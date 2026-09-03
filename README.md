# YouTube → Gemini → Telegram

免費優先的 YouTube 頻道摘要測試版。

目前四個頻道：關我什麼事、鈔錢部署、Catch大錢潮、MoneyDJ理財網。

Telegram 只顯示「影片重點」與「提及個股 / 公司」，不顯示原影片連結、評分、分類、評分理由、後續發展或大量關鍵字。

Gemini 改用目前 Google GenAI Python SDK。若 Gemini 失敗，自動回退 Rules。

GitHub Secrets：YOUTUBE_API_KEY、TELEGRAM_BOT_TOKEN、TELEGRAM_CHAT_ID、GEMINI_API_KEY、GEMINI_MODEL（可選）。

測試期間 config/settings.yaml 的 test_mode=true；確認正常後改成 false。
