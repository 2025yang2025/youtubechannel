from __future__ import annotations

import json
import logging
import re
from typing import Any

from google import genai
from google.genai import types


SYSTEM_INSTRUCTION = r"""
你是台灣財經影片內容整理助手。
你的工作只有一件事：從「影片實際文字內容」中，整理真正有資訊量的重點。

【非常重要】
1. 絕對不能把影片標題改寫後當成影片重點。
2. 如果輸入只有標題、短句、網址、標籤或宣傳文案，請回傳空的 key_points，不要猜測。
3. 只整理輸入文字中「有明確內容」的陳述，例如：公司營收、獲利、訂單、產能、需求、價格、產業趨勢、法人動向、財報、政策影響、個股表現與主持人/來賓明確提出的觀點。
4. 不要自行補充輸入沒有提到的資料。
5. 不要提供投資建議、買賣建議或自行推測未來價格。
6. 最多 4 個重點，每點 1~2 句，盡量 25~80 個中文字，避免空泛句子。
7. 個股/公司請盡量輸出公司名稱；如果文字中有台股 4 位數代號，同時輸出代號與公司名稱。
8. 如果只有公司名稱而沒有代號，不要自行捏造代號。
9. 不要輸出時間碼、網址、電話、會員連結、純數字、雜訊。
10. key_points 必須是「內容摘要」，不能只是標題中的關鍵字排列。

只輸出 JSON：
{
  "key_points": ["..."],
  "mentioned_assets": [
    {"name": "台積電", "code": "2330"}
  ]
}
"""


COMPANY_CODES = {
    "台積電": "2330", "聯發科": "2454", "鴻海": "2317", "廣達": "2382",
    "緯穎": "6669", "台達電": "2308", "日月光投控": "3711", "瑞昱": "2379",
    "聯詠": "3034", "聯電": "2303", "南亞科": "2408", "華邦電": "2344",
    "欣興": "3037", "南電": "8046", "奇鋐": "3017", "雙鴻": "3324",
    "緯創": "3231", "英業達": "2356", "技嘉": "2376", "華碩": "2357",
    "台光電": "2383", "川湖": "2059", "光寶科": "2301", "大立光": "3008",
    "長榮": "2603", "陽明": "2609", "萬海": "2615", "亞通": "6179",
}


def _clean_json_text(raw: str) -> str:
    text = (raw or "").strip()
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.I)
    text = re.sub(r"\s*```$", "", text)
    match = re.search(r"\{.*\}", text, flags=re.S)
    if not match:
        raise ValueError("Gemini 沒有回傳有效 JSON")
    return match.group(0)


def _normalise_assets(items: Any) -> list[dict[str, str]]:
    result: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()

    if not isinstance(items, list):
        return result

    for item in items:
        if isinstance(item, str):
            name = item.strip()
            code = COMPANY_CODES.get(name, "")
        elif isinstance(item, dict):
            name = str(item.get("name", "")).strip()
            code = str(item.get("code", "")).strip()
        else:
            continue

        if not name and not code:
            continue
        if code and not re.fullmatch(r"\d{4}", code):
            code = ""
        if not name and code:
            name = next((n for n, c in COMPANY_CODES.items() if c == code), "")
        if name and not code:
            code = COMPANY_CODES.get(name, "")

        key = (name, code)
        if key not in seen:
            seen.add(key)
            result.append({"name": name, "code": code})

    return result[:12]


def _normalise_points(items: Any) -> list[str]:
    if not isinstance(items, list):
        return []

    result: list[str] = []
    seen: set[str] = set()
    bad_patterns = (
        r"^\d+$", r"^n\s*\d+$", r"^https?://", r"^www\.",
        r"^#", r"^影片重點$", r"^重點整理$"
    )

    for item in items:
        text = re.sub(r"\s+", " ", str(item or "")).strip(" •-\t\n")
        if not text or len(text) < 18 or len(text) > 160:
            continue
        if any(re.search(p, text, flags=re.I) for p in bad_patterns):
            continue
        letters = len(re.findall(r"[A-Za-z\u4e00-\u9fff]", text))
        if letters < 12:
            continue
        # 避免把整個標題原樣回傳。
        if text in seen:
            continue
        seen.add(text)
        result.append(text)
        if len(result) >= 4:
            break

    return result


def analyze_gemini(
    api_key: str,
    model: str,
    video: dict,
    text: str,
    max_chars: int = 45000,
    max_output_tokens: int = 900,
) -> dict:
    text = (text or "").strip()
    title = str(video.get("title", "")).strip()

    if len(re.sub(r"\s+", "", text)) < 80:
        raise RuntimeError("影片內容太短，無法進行可靠分析")

    # 明確告訴模型標題只是辨識資訊，不可拿來當摘要。
    prompt = f"""
頻道：{video.get('channel_name', '')}
影片標題（僅供辨識，禁止直接改寫成重點）：{title}

以下是可用的影片實際文字內容：
---
{text[:max_chars]}
---

請只根據上述文字內容整理重點。
如果上述內容不足以支持至少一個實質重點，key_points 請回傳空陣列。
"""

    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            temperature=0.1,
            max_output_tokens=max_output_tokens,
            response_mime_type="application/json",
        ),
    )

    raw = _clean_json_text(getattr(response, "text", ""))
    data = json.loads(raw)

    points = _normalise_points(data.get("key_points", []))
    assets = _normalise_assets(data.get("mentioned_assets", []))

    if not points:
        raise RuntimeError("Gemini 未找到足夠的實質影片重點")

    logging.info("Gemini analysis complete: %s | points=%s | assets=%s", video.get("video_id", ""), len(points), len(assets))
    return {"key_points": points, "mentioned_assets": assets}
