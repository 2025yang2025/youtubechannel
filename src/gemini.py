from __future__ import annotations

import json
import re

from google import genai

from .rules import STOCK_MAP, FOREIGN_STOCKS


def _extract_json(text: str) -> dict:

    if not text:
        raise ValueError(
            "Gemini 沒有返回內容"
        )

    text = text.strip()

    # 移除 markdown code block
    text = re.sub(
        r"^```json\s*",
        "",
        text,
        flags=re.IGNORECASE,
    )

    text = re.sub(
        r"^```\s*",
        "",
        text,
    )

    text = re.sub(
        r"\s*```$",
        "",
        text,
    )

    text = text.strip()

    try:
        return json.loads(text)

    except json.JSONDecodeError:

        match = re.search(
            r"\{.*\}",
            text,
            flags=re.DOTALL,
        )

        if not match:
            raise ValueError(
                "Gemini 回傳不是有效 JSON"
            )

        return json.loads(
            match.group(0)
        )


def _normalize_assets(
    assets,
) -> list[str]:

    if not isinstance(assets, list):
        return []

    result = []
    seen = set()

    for item in assets:

        if isinstance(item, dict):

            name = str(
                item.get(
                    "name",
                    "",
                )
            ).strip()

            code = str(
                item.get(
                    "code",
                    "",
                )
            ).strip()

        else:

            name = str(item).strip()
            code = ""

        if not name:
            continue

        # -------------------------------------------------
        # 如果 AI 沒提供代號，嘗試使用內建對照
        # -------------------------------------------------

        if not code:

            if name in STOCK_MAP:

                code = STOCK_MAP[name] or ""

            elif name in FOREIGN_STOCKS:

                code = FOREIGN_STOCKS[name] or ""

        if code:

            display = (
                f"{name}（{code}）"
            )

        else:

            display = name

        if display in seen:
            continue

        seen.add(display)
        result.append(display)

    return result[:15]


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

    if not text or len(text.strip()) < 20:

        raise RuntimeError(
            "影片內容太短，無法進行分析"
        )

    client = genai.Client(
        api_key=api_key
    )

    content = text[:max_chars]

    title = video.get(
        "title",
        "",
    )

    prompt = f"""
你是一個台灣股市影片摘要助手。

你的任務不是預測股價，也不是提供投資建議。

請嚴格根據「影片文字內容」整理影片。

影片標題：
{title}

影片內容：
{content}

請完成兩件事情：

1. 找出影片真正談到的 3～5 個重要重點。
2. 找出影片內容「實際提及」的公司、股票或產業。

非常重要：

- 不可以只把影片標題改寫成重點。
- 如果影片內容沒有支持某個結論，不可以自行推測。
- 不可以把影片 Description 的宣傳文案當成影片重點。
- 不要加入自己的投資判斷。
- 不要產生「後續發展」。
- 不要產生風險分析。
- 不要產生評分。
- 不要產生分類。
- 不要產生 Hashtag。
- 不要產生網址。
- 公司如果有股票代號，請提供股票代號。
- 如果只有公司名稱而無法確認股票代號，就只保留公司名稱。
- 絕對不要猜股票代號。
- 台股格式：台積電（2330）
- 美股格式：輝達（NVDA）
- 如果內容只是提到公司名稱，也可以只寫公司名稱。

請只返回 JSON：

{{
  "key_points": [
    "重點1",
    "重點2",
    "重點3"
  ],
  "mentioned_assets": [
    {{
      "name": "公司名稱",
      "code": "股票代號，無法確認則留空"
    }}
  ]
}}
"""

    response = client.models.generate_content(
        model=model,
        contents=prompt,
    )

    raw = getattr(
        response,
        "text",
        None,
    )

    if not raw:

        raise RuntimeError(
            "Gemini 沒有返回分析結果"
        )

    data = _extract_json(
        raw
    )

    points = data.get(
        "key_points",
        [],
    )

    if not isinstance(points, list):
        points = []

    cleaned_points = []

    for point in points:

        point = str(point).strip()

        if len(point) < 8:
            continue

        # 避免 AI 再次只輸出標題
        if title:

            title_clean = re.sub(
                r"\s+",
                "",
                title,
            )

            point_clean = re.sub(
                r"\s+",
                "",
                point,
            )

            if point_clean == title_clean:
                continue

        cleaned_points.append(
            point
        )

    assets = _normalize_assets(
        data.get(
            "mentioned_assets",
            [],
        )
    )

    if not cleaned_points:

        raise RuntimeError(
            "Gemini 沒有產生有效影片重點"
        )

    return {
        "key_points": cleaned_points[:5],
        "mentioned_assets": assets,
    }