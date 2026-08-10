from __future__ import annotations

import json

from google import genai


PROMPT = r"""
你是 YouTube 財經/科技影片摘要助手。

請忠實整理提供的影片內容，
不要自行捏造資料。

只輸出 JSON。

格式：

{
  "score": 0,
  "category": "台股|美股|AI|半導體|總經|其他",
  "summary": "100字內",
  "key_points": ["...", "..."],
  "facts": ["...", "..."],
  "mentioned_assets": ["...", "..."],
  "outlook": "整理影片作者觀點",
  "risks": ["..."],
  "reason": "評分理由"
}

score 是 0~100 的資訊重要度，
不是預測漲跌的機率。
"""


def _json(
    text: str
) -> dict:

    text = text.strip()


    if "```" in text:

        text = text.replace(
            "```json",
            ""
        )

        text = text.replace(
            "```",
            ""
        )


    start = text.find(
        "{"
    )

    end = text.rfind(
        "}"
    )


    if (
        start < 0
        or end < 0
    ):

        raise ValueError(
            "Gemini 沒有回傳 JSON"
        )


    return json.loads(
        text[
            start:
            end + 1
        ]
    )


def analyze_gemini(

    api_key: str,

    model: str,

    video: dict,

    text: str,

    max_chars: int,

) -> dict:

    client = genai.Client(
        api_key=api_key
    )


    prompt = f"""

{PROMPT}

頻道：

{video['channel_name']}

標題：

{video['title']}

網址：

{video['url']}

影片描述：

{video['description'][:5000]}

字幕：

{text[:max_chars]}
"""


    response = client.models.generate_content(

        model=model,

        contents=prompt,
    )


    return _json(
        response.text
    )
