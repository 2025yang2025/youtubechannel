from __future__ import annotations

import json
import re

import requests


def _extract_json(
    text: str,
) -> dict:

    if not text:
        return {}

    text = text.strip()

    # ---------------------------------------------------------
    # 直接 JSON
    # ---------------------------------------------------------

    try:

        return json.loads(
            text
        )

    except Exception:
        pass

    # ---------------------------------------------------------
    # ```json ... ```
    # ---------------------------------------------------------

    match = re.search(
        r"```(?:json)?\s*(.*?)\s*```",
        text,
        re.DOTALL | re.IGNORECASE,
    )

    if match:

        try:

            return json.loads(
                match.group(1)
            )

        except Exception:
            pass

    # ---------------------------------------------------------
    # 找第一個 { 到最後一個 }
    # ---------------------------------------------------------

    start = text.find(
        "{"
    )

    end = text.rfind(
        "}"
    )

    if (
        start >= 0
        and end > start
    ):

        try:

            return json.loads(
                text[start:end + 1]
            )

        except Exception:
            pass

    return {}


def _normalize_analysis(
    data: dict,
) -> dict:

    if not isinstance(
        data,
        dict,
    ):

        data = {}

    # ---------------------------------------------------------
    # score
    # ---------------------------------------------------------

    try:

        score = int(
            data.get(
                "score",
                0,
            )
        )

    except (
        TypeError,
        ValueError,
    ):

        score = 0

    score = max(
        0,
        min(
            100,
            score,
        ),
    )

    # ---------------------------------------------------------
    # core points
    # ---------------------------------------------------------

    core_points = data.get(
        "core_points",
        [],
    )

    if not isinstance(
        core_points,
        list,
    ):

        core_points = []

    core_points = [
        str(x).strip()
        for x in core_points
        if str(x).strip()
    ]

    # ---------------------------------------------------------
    # stocks
    # ---------------------------------------------------------

    stocks = data.get(
        "stocks",
        [],
    )

    if not isinstance(
        stocks,
        list,
    ):

        stocks = []

    normalized_stocks = []

    for item in stocks:

        if isinstance(
            item,
            dict,
        ):

            code = str(
                item.get(
                    "code",
                    "",
                )
            ).strip()

        else:

            code = str(
                item
            ).strip()

        # 只接受 4 位股票代號
        if re.fullmatch(
            r"\d{4}",
            code,
        ):

            if code not in [
                x.get(
                    "code"
                )
                for x
                in normalized_stocks
            ]:

                normalized_stocks.append(
                    {
                        "code": code
                    }
                )

    # ---------------------------------------------------------
    # industries
    # ---------------------------------------------------------

    industries = data.get(
        "industries",
        [],
    )

    if not isinstance(
        industries,
        list,
    ):

        industries = []

    industries = [
        str(x).strip()
        for x in industries
        if str(x).strip()
    ]

    # ---------------------------------------------------------
    # timeline
    # ---------------------------------------------------------

    timeline = data.get(
        "timeline",
        [],
    )

    if not isinstance(
        timeline,
        list,
    ):

        timeline = []

    normalized_timeline = []

    for item in timeline:

        if isinstance(
            item,
            dict,
        ):

            time = str(
                item.get(
                    "time",
                    "",
                )
            ).strip()

            topic = str(
                item.get(
                    "topic",
                    "",
                )
            ).strip()

            if time and topic:

                normalized_timeline.append(
                    {
                        "time": time,
                        "topic": topic,
                    }
                )

    return {
        "score": score,
        "core_points": core_points[:6],
        "stocks": normalized_stocks[:15],
        "industries": industries[:8],
        "timeline": normalized_timeline[:6],
    }


def analyze_gemini(
    api_key: str,
    model: str,
    video: dict,
    text: str,
    max_chars: int = 50000,
) -> dict:

    if not api_key:

        raise RuntimeError(
            "GEMINI_API_KEY 未設定"
        )

    text = str(
        text or ""
    )

    if len(text) > max_chars:

        text = text[
            :max_chars
        ]

    title = str(
        video.get(
            "title",
            "",
        )
    )

    channel_name = (
        video.get(
            "channel_name"
        )
        or video.get(
            "channel_title"
        )
        or "YouTube"
    )

    prompt = f"""
你是一個「台股 YouTube 影片情報整理助手」。

你的工作不是提供投資建議，而是把影片內容整理成
適合 Telegram 閱讀的精簡情報。

頻道：
{channel_name}

影片標題：
{title}

影片內容：
{text}

請嚴格按照以下 JSON 格式輸出：

{{
  "score": 0,
  "core_points": [
    "核心結論1",
    "核心結論2",
    "核心結論3"
  ],
  "stocks": [
    {{
      "code": "2330"
    }}
  ],
  "industries": [
    "半導體",
    "記憶體"
  ],
  "timeline": [
    {{
      "time": "00:00",
      "topic": "台股季線與大盤觀察"
    }}
  ]
}}

規則：

1. score 為 0～100 的內容重要度。
2. core_points 最多 6 點。
3. 每一點必須是完整中文句子。
4. 不要輸出 hashtag。
5. 不要重複影片標題。
6. 不要把影片 Description 原文整段複製。
7. stocks 只放「影片明確提及」的股票代號。
8. 股票代號必須是 4 位數字。
9. 不確定是不是股票代號就不要列。
10. 不要自行猜股票名稱。
11. industries 最多 8 個。
12. timeline 最多 6 個。
13. timeline 沒有明確時間就不要自行創造時間。
14. 不要提供買進、賣出、目標價等投資建議。
15. 只整理影片內容。
16. 只輸出 JSON，不要 Markdown。
"""

    url = (
        "https://generativelanguage.googleapis.com/"
        "v1beta/models/"
        f"{model}:generateContent"
    )

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

    response = requests.post(
        url,
        params={
            "key": api_key
        },
        json=payload,
        timeout=60,
    )

    if response.status_code != 200:

        raise RuntimeError(
            "Gemini API "
            f"{response.status_code}: "
            f"{response.text}"
        )

    data = response.json()

    candidates = data.get(
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

    if not parts:

        raise RuntimeError(
            "Gemini 沒有回傳內容"
        )

    raw_text = str(
        parts[0].get(
            "text",
            "",
        )
    )

    result = _extract_json(
        raw_text
    )

    if not result:

        raise RuntimeError(
            "Gemini 回傳內容不是有效 JSON"
        )

    result = _normalize_analysis(
        result
    )

    result[
        "analysis_source"
    ] = "gemini"

    return result
