from __future__ import annotations

import json
import re
from urllib import error
from urllib import request


def _extract_json(text: str) -> dict:

    text = text.strip()

    text = re.sub(
        r"^```json",
        "",
        text,
        flags=re.IGNORECASE,
    )

    text = re.sub(
        r"^```",
        "",
        text,
    )

    text = re.sub(
        r"```$",
        "",
        text,
    )

    text = text.strip()

    start = text.find("{")
    end = text.rfind("}")

    if start >= 0 and end > start:

        text = text[
            start:end + 1
        ]

    return json.loads(text)


def analyze_gemini(
    api_key: str,
    model: str,
    video: dict,
    text: str,
    max_chars: int = 50000,
) -> dict:

    text = text[:max_chars]

    title = video.get(
        "title",
        "",
    )

    channel_name = video.get(
        "channel_name",
        "",
    )

    prompt = f"""
你是一個台股 YouTube 影片分析助手。

請分析下面的 YouTube 影片內容。

頻道：
{channel_name}

影片標題：
{title}

影片內容：
{text}

你的任務非常單純：

1. 找出影片真正有討論、分析或強調的個股。
2. 股票必須盡量提供：
   - 中文公司名稱
   - 4位數股票代號
3. 不要把單純出現在 hashtag、網址、宣傳文字中的股票算進去。
4. 不要把影片只是順帶提到的股票列為主要個股。
5. 每一檔個股整理 1～3 個最重要的影片觀點。
6. 如果影片沒有明確分析個股，就整理影片最重要的 3～5 個重點。
7. 不要提供投資建議。
8. 不要自行推測影片沒有說的事情。
9. 不要輸出「後續發展」。
10. 不要輸出「評分理由」。
11. 不要輸出長篇摘要。
12. 忽略招生、加入群組、Line、Telegram、網址等宣傳內容。

請只輸出 JSON：

{{
  "score": 0,
  "summary": "一句話整理影片核心內容",
  "key_points": [
    "影片最重要重點",
    "影片第二重要重點",
    "影片第三重要重點"
  ],
  "mentioned_stocks": [
    {{
      "code": "2330",
      "name": "台積電",
      "points": [
        "影片對台積電的第一個重點",
        "影片對台積電的第二個重點"
      ]
    }}
  ]
}}

注意：

如果無法確認股票代號，不要亂填。
如果只知道公司名稱，可以填 code 為空字串。
"""

    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "text": prompt
                    }
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.2,
            "responseMimeType": "application/json",
        },
    }

    url = (
        "https://generativelanguage.googleapis.com/"
        "v1beta/models/"
        f"{model}:generateContent"
        f"?key={api_key}"
    )

    data = json.dumps(
        payload,
        ensure_ascii=False,
    ).encode("utf-8")

    req = request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:

        with request.urlopen(
            req,
            timeout=60,
        ) as response:

            raw = response.read().decode(
                "utf-8"
            )

    except error.HTTPError as exc:

        body = exc.read().decode(
            "utf-8",
            errors="replace",
        )

        raise RuntimeError(
            f"Gemini API {exc.code}: {body}"
        ) from exc

    except Exception as exc:

        raise RuntimeError(
            f"Gemini request failed: {exc}"
        ) from exc

    result = json.loads(raw)

    candidates = result.get(
        "candidates",
        [],
    )

    if not candidates:
        raise RuntimeError(
            "Gemini 沒有回傳 candidates"
        )

    parts = (
        candidates[0]
        .get("content", {})
        .get("parts", [])
    )

    generated = ""

    for part in parts:

        if "text" in part:
            generated += part["text"]

    if not generated:
        raise RuntimeError(
            "Gemini 沒有回傳文字"
        )

    analysis = _extract_json(
        generated
    )

    # 確保欄位存在
    analysis.setdefault(
        "score",
        50,
    )

    analysis.setdefault(
        "summary",
        "",
    )

    analysis.setdefault(
        "key_points",
        [],
    )

    analysis.setdefault(
        "mentioned_stocks",
        [],
    )

    # 限制股票數量
    analysis["mentioned_stocks"] = (
        analysis["mentioned_stocks"][:8]
    )

    for stock in analysis[
        "mentioned_stocks"
    ]:

        stock.setdefault(
            "code",
            "",
        )

        stock.setdefault(
            "name",
            "",
        )

        stock.setdefault(
            "points",
            [],
        )

        stock["points"] = stock[
            "points"
        ][:3]

    return analysis
