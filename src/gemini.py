from __future__ import annotations

import json
import logging
import re
from typing import Any

from google import genai
from google.genai import types


SYSTEM_INSTRUCTION = r"""
你是台灣財經 YouTube 影片的「重點整理助手」。

任務：直接閱讀公開 YouTube 影片的實際內容（語音、字幕、畫面文字與畫面資訊），整理真正有資訊量的內容。

嚴格規則：
1. 絕對不要把影片標題、Hashtag、頻道名稱或 Description 宣傳文案改寫成重點。
2. 每一個 key_point 都必須是影片實際談到的內容；不能只列出「某公司值得關注」「某族群很有機會」這種空話。
3. 優先抓主持人/來賓「明確講出」的：公司/個股、產業、營收、獲利、訂單、需求、價格、產能、庫存、法人動向、政策影響、財報、公司策略、競爭優勢、風險，以及對個股/產業的具體判斷。
4. 若影片明確談到某家公司，重點中盡量寫「公司名稱」；若影片也明確說出 4 位數台股代號，寫「公司名稱（代號）」。
5. 只有公司名稱、沒有代號時，不得猜代號。
6. 不得自行查資料、補資料、猜測公司代號或創造影片沒有說的數字。
7. 不要輸出時間碼、網址、電話、會員連結、Hashtag、純數字、亂碼。
8. 最多 4 個 key_points，每點 25~90 個中文字，內容要有具體資訊。
9. 如果影片實際內容無法讀取，或只有標題/宣傳文字，請回傳空 key_points；不要硬湊。
10. 不要提供買進、賣出、停損、目標價等投資建議。

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
    "力積電": "6770", "國巨": "2327", "宏致": "3605", "上銀": "2049",
    "群聯": "8299", "威剛": "3260", "創見": "2451", "十銓": "4967",
    "宇瞻": "8271", "南茂": "8150", "力成": "6239", "日月光": "3711",
    "京元電子": "2449", "矽格": "6257", "穩懋": "3105", "聯電": "2303",
    "亞光": "3019", "玉晶光": "3406", "台塑": "1301", "南亞": "1303",
    "台化": "1326", "中鋼": "2002", "台塑化": "6505", "台泥": "1101",
    "統一": "1216", "遠東新": "1402", "中華電": "2412", "兆豐金": "2886",
    "富邦金": "2881", "國泰金": "2882", "元大金": "2885", "中信金": "2891",
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

    reverse = {v: k for k, v in COMPANY_CODES.items()}
    for item in items:
        if isinstance(item, str):
            name, code = item.strip(), ""
        elif isinstance(item, dict):
            name = str(item.get("name", "")).strip()
            code = str(item.get("code", "")).strip()
        else:
            continue

        name = re.sub(r"\s+", " ", name)
        if code and not re.fullmatch(r"\d{4}", code):
            code = ""
        if not name and code:
            name = reverse.get(code, "")
        if name and not code:
            code = COMPANY_CODES.get(name, "")
        if not name and not code:
            continue

        key = (name, code)
        if key not in seen:
            seen.add(key)
            result.append({"name": name, "code": code})
        if len(result) >= 12:
            break
    return result


def _title_tokens(title: str) -> set[str]:
    tokens = re.findall(r"[A-Za-z]{2,}|[\u4e00-\u9fff]{2,}", title or "")
    stop = {"關我什麼事", "鈔錢部署", "Catch大錢潮", "MoneyDJ理財網", "直播", "主持"}
    return {x for x in tokens if x not in stop and len(x) >= 2}


def _looks_like_real_point(point: str, title: str) -> bool:
    p = re.sub(r"\s+", " ", str(point or "")).strip(" •-\t\n")
    if len(p) < 20 or len(p) > 180:
        return False
    if re.search(r"https?://|www\.|加入會員|訂閱|按讚|留言|點擊|家族", p, re.I):
        return False
    if re.fullmatch(r"[\d\s._-]+", p):
        return False
    if re.search(r"^n\s*\d+$", p, re.I):
        return False

    # 若重點幾乎只是標題改寫，拒絕。
    title_tokens = _title_tokens(title)
    point_tokens = set(re.findall(r"[A-Za-z]{2,}|[\u4e00-\u9fff]{2,}", p))
    if title_tokens and point_tokens:
        overlap = len(title_tokens & point_tokens) / max(1, len(point_tokens))
        if overlap >= 0.85 and not re.search(
            r"營收|獲利|EPS|訂單|需求|價格|報價|產能|庫存|法人|外資|投信|財報|市占|出貨|接單|政策|成本|毛利|景氣|供應|漲|跌|成長|下滑|轉強|轉弱|利多|利空",
            p,
        ):
            return False
    return True


def _normalise_points(items: Any, title: str) -> list[str]:
    if not isinstance(items, list):
        return []
    result: list[str] = []
    seen: set[str] = set()
    for item in items:
        point = re.sub(r"\s+", " ", str(item or "")).strip(" •-\t\n")
        if not _looks_like_real_point(point, title):
            continue
        key = re.sub(r"[^A-Za-z0-9\u4e00-\u9fff]", "", point)
        if key in seen:
            continue
        seen.add(key)
        result.append(point)
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
    use_youtube_url: bool = True,
) -> dict:
    """Analyze actual YouTube content, using transcript/description only as backup context."""
    title = str(video.get("title", "")).strip()
    description = str(video.get("description", "") or "").strip()
    video_id = str(video.get("video_id", "")).strip()
    video_url = str(video.get("url", "") or "").strip()
    if not video_url and video_id:
        video_url = f"https://www.youtube.com/watch?v={video_id}"

    text = (text or "").strip()
    client = genai.Client(api_key=api_key)

    prompt = f"""
頻道：{video.get('channel_name', '')}

影片標題（只用來辨識影片，絕對不能直接改寫成重點）：
{title}

請分析這支影片「實際播放內容」。優先理解主持人與來賓說話內容、字幕與畫面文字。

你要找的是：影片中真正被解釋、比較、強調的資訊，而不是標題。
尤其注意：
- 被明確點名且有實質說明的公司/個股/ETF/產業
- 公司發生什麼事、營收/獲利/訂單/需求/價格/產能/庫存等
- 主持人或來賓提出的具體市場觀點與理由
- 若同一家公司只是標題或 hashtag 提到、影片沒有實質談到，請不要列入重點

【Description／字幕輔助資料】
這些資料可能不完整或只有宣傳文案，只能拿來輔助核對，不能把它當成影片重點：
{(description[:12000] + '\n' + text[:max_chars])[:max_chars]}

輸出最多 4 個重點。
每個重點必須是完整中文句子，具體說明「發生什麼事 / 為什麼被強調 / 有什麼數據或觀點」。
如果你只能看到標題、Hashtag、會員宣傳或雜訊，請輸出空 key_points。
"""

    if use_youtube_url and video_url:
        # Google 官方支援把公開 YouTube URL 直接當 video input。
        contents = types.Content(
            parts=[
                types.Part(text=prompt),
                types.Part(file_data=types.FileData(file_uri=video_url)),
            ]
        )
        mode = "youtube_video"
    else:
        if len(re.sub(r"\s+", "", text)) < 80:
            raise RuntimeError("沒有足夠文字內容可分析")
        contents = prompt
        mode = "text"

    # Gemini 3.x 已不建議使用 temperature 等舊 sampling 參數，因此不傳入。
    response = client.models.generate_content(
        model=model,
        contents=contents,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            max_output_tokens=max_output_tokens,
            response_mime_type="application/json",
        ),
    )

    raw = _clean_json_text(getattr(response, "text", ""))
    data = json.loads(raw)
    points = _normalise_points(data.get("key_points", []), title)
    assets = _normalise_assets(data.get("mentioned_assets", []))

    if not points:
        raise RuntimeError("Gemini 未找到足夠的實質影片重點")

    logging.info(
        "Gemini analysis complete: %s | mode=%s | points=%s | assets=%s",
        video_id, mode, len(points), len(assets),
    )
    return {"key_points": points, "mentioned_assets": assets}
