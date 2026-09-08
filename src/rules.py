from __future__ import annotations

import re

COMPANIES = {
    "2330": "台積電", "2454": "聯發科", "2317": "鴻海", "2382": "廣達", "6669": "緯穎",
    "2308": "台達電", "3711": "日月光投控", "2379": "瑞昱", "3034": "聯詠", "2303": "聯電",
    "2408": "南亞科", "2344": "華邦電", "3037": "欣興", "8046": "南電", "3017": "奇鋐",
    "3324": "雙鴻", "3231": "緯創", "2356": "英業達", "2376": "技嘉", "2357": "華碩",
    "2383": "台光電", "2059": "川湖", "2301": "光寶科", "3008": "大立光", "2603": "長榮",
    "2609": "陽明", "2615": "萬海", "6179": "亞通", "6770": "力積電", "2327": "國巨",
    "3605": "宏致", "2049": "上銀", "8299": "群聯", "3260": "威剛", "2451": "創見",
    "4967": "十銓", "8271": "宇瞻", "8150": "南茂", "6239": "力成", "2449": "京元電子",
    "6257": "矽格", "3105": "穩懋", "3019": "亞光", "3406": "玉晶光", "1301": "台塑",
    "1303": "南亞", "1326": "台化", "2002": "中鋼", "6505": "台塑化", "1101": "台泥",
    "1216": "統一", "1402": "遠東新", "2412": "中華電", "2886": "兆豐金", "2881": "富邦金",
    "2882": "國泰金", "2885": "元大金", "2891": "中信金",
}


def clean(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def _is_noise(sentence: str) -> bool:
    s = clean(sentence)
    if len(s) < 20:
        return True
    if re.search(r"https?://|www\.|加入會員|訂閱|按讚|留言|點擊|家族|line|telegram", s, re.I):
        return True
    letters = len(re.findall(r"[A-Za-z\u4e00-\u9fff]", s))
    digits = len(re.findall(r"\d", s))
    return letters < 12 or digits > max(letters * 2, 24)


def _sentences(text: str) -> list[str]:
    parts = re.split(r"[。！？!?；;\n]+", text or "")
    return [clean(x) for x in parts if not _is_noise(x)]


def _assets(text: str) -> list[dict[str, str]]:
    result: list[dict[str, str]] = []
    for code, name in COMPANIES.items():
        if re.search(rf"(?<!\d){re.escape(code)}(?!\d)", text) or name in text:
            result.append({"name": name, "code": code})
        if len(result) >= 12:
            break
    return result


def analyze_rules(title: str, description: str, transcript: str, keywords: list[str]) -> dict:
    # 規則模式永遠不使用標題產生重點，避免把標題複製成 Telegram 訊息。
    text = clean(f"{description}\n{transcript}")
    sentences = _sentences(text)
    important = [
        "營收", "獲利", "EPS", "訂單", "需求", "報價", "價格", "展望", "法說", "產能",
        "AI", "半導體", "記憶體", "突破", "轉強", "轉弱", "成長", "下滑", "毛利", "法人",
        "外資", "投信", "景氣", "供應鏈", "市占", "庫存", "出貨", "接單", "漲價", "跌價",
        "政策", "成本", "利多", "利空", "獲利率", "現金流", "資本支出",
    ]

    def score(sentence: str) -> int:
        value = sum(2 for w in important if w.lower() in sentence.lower())
        value += sum(1 for w in keywords if w.lower() in sentence.lower())
        if re.search(r"\d+(?:\.\d+)?%", sentence):
            value += 3
        if re.search(r"(?<!\d)\d{4}(?!\d)", sentence):
            value += 2
        if any(name in sentence for name in COMPANIES.values()):
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
        points.append(sentence[:160])
        if len(points) >= 4:
            break

    assets = _assets(text)
    if not points:
        raise RuntimeError("規則模式也未找到足夠的實質內容")
    return {"key_points": points, "mentioned_assets": assets}
