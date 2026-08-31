from __future__ import annotations

import re


STOCK_NAMES = {
    "2330": "台積電",
    "2303": "聯電",
    "2454": "聯發科",
    "2317": "鴻海",
    "2382": "廣達",
    "6669": "緯穎",
    "2308": "台達電",
    "3711": "日月光投控",
    "3231": "緯創",
    "2357": "華碩",
    "2376": "技嘉",
    "3037": "欣興",
    "3044": "健鼎",
    "2344": "華邦電",
    "2408": "南亞科",
    "8299": "群聯",
    "3006": "晶豪科",
    "6239": "力成",
    "6770": "力積電",
    "3715": "定穎投控",
    "3017": "奇鋐",
    "3324": "雙鴻",
    "3661": "世芯-KY",
    "3443": "創意",
    "3665": "貿聯-KY",
    "3034": "聯詠",
    "3035": "智原",
    "2379": "瑞昱",
    "3529": "力旺",
    "5274": "信驊",
    "6669": "緯穎",
    "2383": "台光電",
    "8046": "南電",
    "3533": "嘉澤",
    "2059": "川湖",
    "6415": "矽力*-KY",
    "2353": "宏碁",
    "2356": "英業達",
    "2324": "仁寶",
    "3036": "文曄",
    "2301": "光寶科",
    "2377": "微星",
    "2376": "技嘉",
}


NAME_ALIASES = {
    "台積": "台積電",
    "TSMC": "台積電",
    "TSM": "台積電",
    "NVIDIA": "輝達",
    "Nvidia": "輝達",
    "AMD": "超微",
    "Intel": "英特爾",
    "聯發": "聯發科",
    "南亞科": "南亞科",
    "華邦": "華邦電",
}


IMPORTANT_WORDS = [
    "營收",
    "獲利",
    "EPS",
    "毛利",
    "毛利率",
    "訂單",
    "接單",
    "需求",
    "展望",
    "成長",
    "下滑",
    "增加",
    "減少",
    "突破",
    "轉強",
    "轉弱",
    "上漲",
    "下跌",
    "利多",
    "利空",
    "題材",
    "漲價",
    "降價",
    "擴產",
    "產能",
    "庫存",
    "AI",
    "HBM",
    "CoWoS",
    "先進製程",
    "法說",
    "財報",
    "本益比",
    "殖利率",
]


def _clean_text(text: str) -> str:
    if not text:
        return ""

    text = re.sub(
        r"https?://\S+",
        "",
        text,
    )

    text = re.sub(
        r"www\.\S+",
        "",
        text,
    )

    text = re.sub(
        r"#[^\s#]+",
        "",
        text,
    )

    text = re.sub(
        r"\s+",
        " ",
        text,
    )

    return text.strip()


def _sentences(text: str) -> list[str]:
    text = _clean_text(text)

    raw = re.split(
        r"[。！？!?；;\n]",
        text,
    )

    result = []

    for item in raw:
        item = item.strip()

        if len(item) < 8:
            continue

        result.append(item)

    return result


def _find_stock_mentions(
    text: str,
) -> list[dict]:

    found = []

    # 股票代號
    for code in re.findall(
        r"(?<!\d)(\d{4})(?!\d)",
        text,
    ):
        if code in STOCK_NAMES:
            found.append(
                {
                    "code": code,
                    "name": STOCK_NAMES[code],
                }
            )

    # 公司名稱
    for name in set(
        STOCK_NAMES.values()
    ):
        if name in text:
            code = next(
                (
                    k
                    for k, v
                    in STOCK_NAMES.items()
                    if v == name
                ),
                "",
            )

            found.append(
                {
                    "code": code,
                    "name": name,
                }
            )

    # 別名
    for alias, name in NAME_ALIASES.items():
        if alias.lower() in text.lower():
            code = next(
                (
                    k
                    for k, v
                    in STOCK_NAMES.items()
                    if v == name
                ),
                "",
            )

            found.append(
                {
                    "code": code,
                    "name": name,
                }
            )

    result = []
    seen = set()

    for item in found:
        key = (
            item["code"],
            item["name"],
        )

        if key in seen:
            continue

        seen.add(key)
        result.append(item)

    return result[:12]


def _stock_points(
    text: str,
    stock: dict,
) -> list[str]:

    name = stock["name"]
    code = stock["code"]

    keywords = [
        name,
    ]

    if code:
        keywords.append(code)

    sentences = _sentences(text)

    scored = []

    for sentence in sentences:

        if not any(
            key.lower()
            in sentence.lower()
            for key in keywords
        ):
            continue

        score = 5

        for word in IMPORTANT_WORDS:
            if word.lower() in sentence.lower():
                score += 2

        if re.search(
            r"\d+(?:\.\d+)?%",
            sentence,
        ):
            score += 3

        if re.search(
            r"\d{2,}",
            sentence,
        ):
            score += 1

        scored.append(
            (
                score,
                sentence,
            )
        )

    scored.sort(
        key=lambda x: x[0],
        reverse=True,
    )

    result = []
    seen = set()

    for _, sentence in scored:
        sentence = sentence.strip()

        if sentence in seen:
            continue

        seen.add(sentence)
        result.append(sentence[:180])

        if len(result) >= 3:
            break

    return result


def _category(text: str) -> str:

    categories = {
        "台股": [
            "台股",
            "加權",
            "櫃買",
            "上市",
            "上櫃",
        ],
        "AI": [
            "AI",
            "人工智慧",
            "GPU",
            "伺服器",
        ],
        "半導體": [
            "半導體",
            "晶圓",
            "先進製程",
            "封裝",
            "HBM",
        ],
        "記憶體": [
            "記憶體",
            "DRAM",
            "NAND",
            "HBM",
        ],
        "總經": [
            "FED",
            "聯準會",
            "降息",
            "升息",
            "CPI",
            "GDP",
        ],
    }

    scores = {}

    for category, words in categories.items():
        scores[category] = sum(
            text.lower().count(
                word.lower()
            )
            for word in words
        )

    best = max(
        scores,
        key=scores.get,
    )

    if scores[best] <= 0:
        return "其他"

    return best


def _score(
    text: str,
    keywords: list[str],
) -> int:

    score = 30

    for word in IMPORTANT_WORDS:
        if word.lower() in text.lower():
            score += 3

    for word in keywords:
        if word.lower() in text.lower():
            score += 2

    stocks = _find_stock_mentions(text)

    score += min(
        len(stocks) * 4,
        20,
    )

    if "%" in text:
        score += 5

    return max(
        0,
        min(
            100,
            score,
        ),
    )


def analyze_rules(
    title: str,
    description: str,
    transcript: str,
    keywords: list[str],
) -> dict:

    text = "\n".join(
        [
            title or "",
            description or "",
            transcript or "",
        ]
    )

    text = _clean_text(text)

    stocks = _find_stock_mentions(
        text
    )

    stock_analysis = []

    for stock in stocks:

        points = _stock_points(
            text,
            stock,
        )

        if not points:
            continue

        stock_analysis.append(
            {
                "code": stock["code"],
                "name": stock["name"],
                "points": points,
            }
        )

    # 如果找不到已知股票，
    # 再找影片中可能的四位數代號
    if not stocks:

        codes = re.findall(
            r"(?<!\d)(\d{4})(?!\d)",
            text,
        )

        seen_codes = set()

        for code in codes:

            if code in seen_codes:
                continue

            seen_codes.add(code)

            stock_analysis.append(
                {
                    "code": code,
                    "name": f"股票 {code}",
                    "points": [
                        "影片中提及此股票代號，但目前無法確認公司名稱。"
                    ],
                }
            )

            if len(stock_analysis) >= 8:
                break

    key_points = []

    sentences = _sentences(text)

    ranked = []

    for sentence in sentences:

        score = 0

        for word in IMPORTANT_WORDS:
            if word.lower() in sentence.lower():
                score += 2

        if "%" in sentence:
            score += 3

        if re.search(
            r"\d{2,}",
            sentence,
        ):
            score += 1

        if any(
            stock["name"] in sentence
            or (
                stock["code"]
                and stock["code"] in sentence
            )
            for stock in stocks
        ):
            score += 5

        if score > 0:
            ranked.append(
                (
                    score,
                    sentence,
                )
            )

    ranked.sort(
        key=lambda x: x[0],
        reverse=True,
    )

    seen = set()

    for _, sentence in ranked:

        if sentence in seen:
            continue

        seen.add(sentence)
        key_points.append(
            sentence[:180]
        )

        if len(key_points) >= 5:
            break

    return {
        "score": _score(
            text,
            keywords,
        ),
        "category": _category(text),
        "summary": (
            key_points[0]
            if key_points
            else title[:180]
        ),
        "key_points": key_points,
        "mentioned_stocks": stock_analysis,
    }
