from __future__ import annotations

import re


# ---------------------------------------------------------
# 股票 / 公司名稱對照
# ---------------------------------------------------------

STOCK_MAP = {
    "台積電": "2330",
    "聯電": "2303",
    "聯發科": "2454",
    "鴻海": "2317",
    "廣達": "2382",
    "緯穎": "6669",
    "台達電": "2308",
    "日月光投控": "3711",
    "日月光": "3711",
    "南亞": "1303",
    "南亞科": "2408",
    "華邦電": "2344",
    "旺宏": "2337",
    "力積電": "6770",
    "群聯": "8299",
    "威剛": "3260",
    "創見": "2451",
    "國巨": "2327",
    "華新科": "2492",
    "南電": "8046",
    "欣興": "3037",
    "景碩": "3189",
    "川湖": "2059",
    "上銀": "2049",
    "宏致": "3605",
    "亞通": "6179",
    "聯詠": "3034",
    "瑞昱": "2379",
    "世芯-KY": "3661",
    "祥碩": "5269",
    "信驊": "5274",
    "奇鋐": "3017",
    "雙鴻": "3324",
    "健策": "3653",
    "台光電": "2383",
    "金像電": "2368",
    "智邦": "2345",
    "英業達": "2356",
    "緯創": "3231",
    "技嘉": "2376",
    "微星": "2377",
    "華碩": "2357",
    "大立光": "3008",
    "鴻準": "2354",
    "台塑": "1301",
    "台化": "1326",
    "台玻": "1802",
    "中鋼": "2002",
}


FOREIGN_STOCKS = {
    "輝達": "NVDA",
    "NVIDIA": "NVDA",
    "超微": "AMD",
    "AMD": "AMD",
    "英特爾": "INTC",
    "Intel": "INTC",
    "美光": "MU",
    "Micron": "MU",
    "博通": "AVGO",
    "Broadcom": "AVGO",
    "高通": "QCOM",
    "Qualcomm": "QCOM",
    "台積電": "2330",
    "海力士": None,
    "SK海力士": None,
}


# ---------------------------------------------------------
# 雜訊
# ---------------------------------------------------------

NOISE_PATTERNS = [
    r"https?://\S+",
    r"www\.\S+",
    r"#\S+",
    r"加入.*?家族",
    r"訂閱.*?",
    r"按讚.*?",
    r"記得.*?訂閱",
    r"歡迎.*?訂閱",
    r"點擊.*?",
    r"點↓↓↓.*",
]


def clean_text(text: str) -> str:
    """清除影片 Description 常見宣傳雜訊。"""

    if not text:
        return ""

    result = text

    for pattern in NOISE_PATTERNS:
        result = re.sub(
            pattern,
            " ",
            result,
            flags=re.IGNORECASE,
        )

    # 清除多餘空白
    result = re.sub(
        r"[ \t]+",
        " ",
        result,
    )

    result = re.sub(
        r"\n{3,}",
        "\n\n",
        result,
    )

    return result.strip()


# ---------------------------------------------------------
# 句子
# ---------------------------------------------------------

def _sentences(text: str) -> list[str]:

    text = clean_text(text)

    if not text:
        return []

    raw = re.split(
        r"[。！？!?；;\n]",
        text,
    )

    result = []

    for item in raw:

        sentence = item.strip()

        if len(sentence) < 10:
            continue

        # 太像標籤 / hashtag 的內容不要
        if sentence.count("#") >= 2:
            continue

        result.append(sentence)

    return result


# ---------------------------------------------------------
# 股票名稱
# ---------------------------------------------------------

def _extract_assets(text: str) -> list[str]:

    if not text:
        return []

    result = []
    seen = set()

    # -----------------------------
    # 台股公司
    # -----------------------------

    for name, code in STOCK_MAP.items():

        if name not in text:
            continue

        display = (
            f"{name}（{code}）"
            if code
            else name
        )

        if display not in seen:

            seen.add(display)
            result.append(display)

    # -----------------------------
    # 美股 / 外國公司
    # -----------------------------

    for name, code in FOREIGN_STOCKS.items():

        if name not in text:
            continue

        display = (
            f"{name}（{code}）"
            if code
            else name
        )

        if display not in seen:

            seen.add(display)
            result.append(display)

    # -----------------------------
    # 從文字找四位數股票代號
    # -----------------------------

    codes = re.findall(
        r"(?<!\d)(\d{4})(?!\d)",
        text,
    )

    for code in codes:

        # 避免把年份、時間當股票
        number = int(code)

        if 1900 <= number <= 2100:
            continue

        if code in {"0000", "1111", "2222"}:
            continue

        # 如果沒有名稱，不直接亂配
        # 只有在對照表中才顯示
        for name, mapped_code in STOCK_MAP.items():

            if mapped_code == code:

                display = f"{name}（{code}）"

                if display not in seen:
                    seen.add(display)
                    result.append(display)

                break

    return result[:15]


# ---------------------------------------------------------
# 判斷一句話是不是有內容
# ---------------------------------------------------------

IMPORTANT_WORDS = [
    "營收",
    "獲利",
    "EPS",
    "毛利",
    "訂單",
    "接單",
    "需求",
    "產能",
    "擴產",
    "財報",
    "法說",
    "展望",
    "成長",
    "衰退",
    "價格",
    "漲價",
    "跌價",
    "突破",
    "轉強",
    "轉弱",
    "法人",
    "外資",
    "投信",
    "主力",
    "買超",
    "賣超",
    "資金",
    "AI",
    "伺服器",
    "半導體",
    "記憶體",
    "封裝",
    "晶圓",
    "先進製程",
    "機器人",
    "能源",
    "綠能",
    "電動車",
]


def _sentence_score(
    sentence: str,
    keywords: list[str],
) -> int:

    score = 0

    lower = sentence.lower()

    # 重要關鍵詞
    for word in IMPORTANT_WORDS:

        if word.lower() in lower:
            score += 3

    # 使用者指定關鍵字
    for word in keywords:

        if word and word.lower() in lower:
            score += 2

    # 公司名稱
    for name in STOCK_MAP:

        if name in sentence:
            score += 4

    for name in FOREIGN_STOCKS:

        if name in sentence:
            score += 4

    # 數字
    if re.search(r"\d+", sentence):
        score += 1

    # 百分比
    if "%" in sentence:
        score += 2

    return score


# ---------------------------------------------------------
# Rules 分析
# ---------------------------------------------------------

def analyze_rules(
    title: str = "",
    description: str = "",
    transcript: str = "",
    keywords: list[str] | None = None,
    text: str | None = None,
    channel=None,
    video=None,
) -> dict:

    keywords = keywords or []

    # -----------------------------------------------------
    # 相容舊版 main.py
    # -----------------------------------------------------

    if text:
        source_text = text

    else:
        source_text = "\n".join(
            [
                title or "",
                description or "",
                transcript or "",
            ]
        )

    source_text = clean_text(source_text)

    sentences = _sentences(source_text)

    # -----------------------------------------------------
    # 如果沒有內容
    # -----------------------------------------------------

    if not sentences:

        return {
            "summary": "目前沒有取得足夠的影片文字內容。",
            "key_points": [],
            "mentioned_assets": [],
        }

    # -----------------------------------------------------
    # 排序重要句子
    # -----------------------------------------------------

    ranked = []

    for sentence in sentences:

        score = _sentence_score(
            sentence,
            keywords,
        )

        ranked.append(
            (
                score,
                sentence,
            )
        )

    ranked.sort(
        key=lambda item: item[0],
        reverse=True,
    )

    # -----------------------------------------------------
    # 去除太相似內容
    # -----------------------------------------------------

    key_points = []
    seen_words = []

    for score, sentence in ranked:

        if score <= 0:
            continue

        # 避免太短
        if len(sentence) < 15:
            continue

        # 避免標題本身
        if title:

            title_clean = clean_text(title)

            if sentence.strip() == title_clean.strip():
                continue

        # 避免重複句
        duplicate = False

        current_words = set(
            re.findall(
                r"[\u4e00-\u9fffA-Za-z0-9]+",
                sentence,
            )
        )

        for previous in seen_words:

            if not current_words:
                continue

            overlap = (
                len(current_words & previous)
                / max(
                    1,
                    len(current_words),
                )
            )

            if overlap >= 0.75:

                duplicate = True
                break

        if duplicate:
            continue

        key_points.append(sentence)
        seen_words.append(current_words)

        if len(key_points) >= 5:
            break

    # -----------------------------------------------------
    # 如果沒有找到有效句子
    # -----------------------------------------------------

    if not key_points:

        # 不再把標題當成影片重點
        key_points = [
            sentence
            for sentence in sentences[:3]
            if sentence != title
        ]

    # -----------------------------------------------------
    # 個股
    # -----------------------------------------------------

    assets = _extract_assets(
        source_text
    )

    return {
        "summary": (
            key_points[0][:220]
            if key_points
            else "目前沒有足夠內容可整理。"
        ),

        "key_points": key_points[:5],

        "mentioned_assets": assets,
    }