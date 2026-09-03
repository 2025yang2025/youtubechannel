from __future__ import annotations

import re

COMPANIES = {
    "2330": "台積電", "2454": "聯發科", "2317": "鴻海", "2382": "廣達", "6669": "緯穎",
    "2308": "台達電", "3711": "日月光投控", "2379": "瑞昱", "3034": "聯詠", "2303": "聯電",
    "2408": "南亞科", "2344": "華邦電", "3037": "欣興", "8046": "南電", "3017": "奇鋐",
    "3324": "雙鴻", "3231": "緯創", "2356": "英業達", "2376": "技嘉", "2357": "華碩",
    "2383": "台光電", "2059": "川湖", "2301": "光寶科", "3008": "大立光", "2603": "長榮",
    "2609": "陽明", "2615": "萬海", "6179": "亞通",
}


def clean(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def _is_noise(sentence: str) -> bool:
    s = clean(sentence)
    if len(s) < 18:
        return True
    if re.search(r"https?://|www\.|加入會員|訂閱|按讚|留言|點擊|家族", s, re.I):
        return True
    letters = len(re.findall(r"[A-Za-z\u4e00-\u9fff]", s))
    digits = len(re.findall(r"\d", s))
    return letters < 12 or digits > max(letters * 2, 20)


def _sentences(text: str) -> list[str]:
    parts = re.split(r"[。！？!?；;\n]+", text or "")
    return [clean(x) for x in parts if not _is_noise(x)]


def _assets(text: str) -> list[dict[str, str]]:
    result: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()

    for code, name in COMPANIES.items():
        if re.search(rf"(?<!\d){re.escape(code)}(?!\d)", text) or name in text:
            key = (name, code)
            if key not in seen:
                seen.add(key)
                result.append({"name": name, "code": code})

    return result[:12]


def analyze_rules(title: str, description: str, transcript: str, keywords: list[str]) -> dict:
    # 規則模式不使用標題作為重點來源，避免出現「複製標題」問題。
    text = clean(f"{description}\n{transcript}")
    sentences = _sentences(text)

    important = [
        "營收", "獲利", "EPS", "訂單", "需求", "報價", "價格", "展望", "法說", "產能",
        "AI", "半導體", "記憶體", "突破", "轉強", "轉弱", "成長", "下滑", "毛利", "法人",
        "外資", "投信", "景氣", "供應鏈", "市占", "庫存", "出貨", "接單", "漲價", "跌價",
    ]

    def score(sentence: str) -> int:
        value = sum(2 for w in important if w.lower() in sentence.lower())
        value += sum(1 for w in keywords if w.lower() in sentence.lower())
        if re.search(r"\d+(?:\.\d+)?%", sentence):
            value += 3
        if re.search(r"\b\d{4}\b", sentence):
            value += 2
        return value

    ranked = sorted(sentences, key=score, reverse=True)
    points: list[str] = []
    seen: set[str] = set()

    for sentence in ranked:
        if score(sentence) <= 0:
            continue
        key = re.sub(r"[^A-Za-z\u4e00-\u9fff0-9]", "", sentence)
        if key in seen:
            continue
        seen.add(key)
        points.append(sentence[:150])
        if len(points) >= 4:
            break

    assets = _assets(text)
    if not points:
        raise RuntimeError("規則模式也未找到足夠的實質內容")

    return {"key_points": points, "mentioned_assets": assets}
