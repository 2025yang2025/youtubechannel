from __future__ import annotations

import re


CATEGORY_KEYWORDS = {
    "台股": [
        "台股",
        "加權",
        "櫃買",
        "上市",
        "上櫃",
        "台積電",
    ],

    "美股": [
        "美股",
        "NASDAQ",
        "那斯達克",
        "S&P",
        "標普",
        "道瓊",
    ],

    "AI": [
        "AI",
        "人工智慧",
        "GPU",
        "大模型",
        "LLM",
    ],

    "半導體": [
        "半導體",
        "晶圓",
        "先進製程",
        "封裝",
        "HBM",
        "記憶體",
    ],

    "總經": [
        "FED",
        "聯準會",
        "降息",
        "升息",
        "通膨",
        "CPI",
        "GDP",
    ],
}


# ============================================================
# 股票代號 → 中文名稱
#
# 先建立常見台股對照表。
# 如果影片只有出現代號，Telegram 仍會顯示中文名稱。
# ============================================================

STOCK_NAMES = {
    "1101": "台泥",
    "1216": "統一",
    "1301": "台塑",
    "1303": "南亞",
    "1402": "遠東新",
    "1476": "儒鴻",
    "1590": "亞德客-KY",
    "1605": "華新",
    "2002": "中鋼",
    "2207": "和泰車",
    "2301": "光寶科",
    "2303": "聯電",
    "2308": "台達電",
    "2317": "鴻海",
    "2327": "國巨",
    "2330": "台積電",
    "2344": "華邦電",
    "2345": "智邦",
    "2357": "華碩",
    "2368": "金像電",
    "2376": "技嘉",
    "2377": "微星",
    "2382": "廣達",
    "2383": "台光電",
    "2395": "研華",
    "2408": "南亞科",
    "2412": "中華電",
    "2454": "聯發科",
    "2458": "義隆",
    "2474": "可成",
    "3034": "聯詠",
    "3037": "欣興",
    "3044": "健鼎",
    "3231": "緯創",
    "3260": "威剛",
    "3443": "創意",
    "3533": "嘉澤",
    "3661": "世芯-KY",
    "3711": "日月光投控",
    "4904": "遠傳",
    "4958": "臻鼎-KY",
    "5269": "祥碩",
    "5274": "信驊",
    "5483": "中美晶",
    "5871": "中租-KY",
    "6239": "力成",
    "6669": "緯穎",
    "6672": "騰輝電子-KY",
    "6770": "力積電",
    "6805": "富世達",
    "8046": "南電",
    "8299": "群聯",
    "8996": "高力",
}


# ============================================================
# 公司名稱 → 股票代號
#
# 讓「台積電」也可以反查成 2330。
# ============================================================

NAME_TO_STOCK = {
    name: code
    for code, name in STOCK_NAMES.items()
}


ASSET_PATTERNS = [
    r"\b\d{4}\b",

    r"台積電",
    r"聯發科",
    r"鴻海",
    r"廣達",
    r"緯穎",
    r"台達電",
    r"聯電",
    r"日月光",
    r"南亞科",
    r"國巨",
    r"欣興",
    r"南電",
    r"力積電",
    r"華邦電",
    r"群聯",
    r"威剛",
    r"AMD",
    r"NVIDIA",
    r"輝達",
    r"Intel",
]


def _sentences(
    text: str
) -> list[str]:

    raw = re.split(
        r"[。！？!?；;\n]",
        text
    )

    return [
        s.strip()
        for s in raw
        if len(
            s.strip()
        ) >= 12
    ]


def _category(
    text: str
) -> str:

    scores = {
        name:
        sum(
            text.lower().count(
                keyword.lower()
            )
            for keyword in keywords
        )
        for name, keywords
        in CATEGORY_KEYWORDS.items()
    }

    best = max(
        scores,
        key=scores.get
    )

    if scores[best] <= 0:
        return "其他"

    return best


def _assets(
    text: str
) -> list[str]:

    found = []

    # --------------------------------------------------------
    # 先找四位數股票代號
    # --------------------------------------------------------

    codes = re.findall(
        r"(?<!\d)\d{4}(?!\d)",
        text
    )

    for code in codes:

        found.append(
            code
        )

    # --------------------------------------------------------
    # 再找公司名稱
    # --------------------------------------------------------

    names = [
        "台積電",
        "聯發科",
        "鴻海",
        "廣達",
        "緯穎",
        "台達電",
        "聯電",
        "日月光",
        "南亞科",
        "國巨",
        "欣興",
        "南電",
        "力積電",
        "華邦電",
        "群聯",
        "威剛",
        "AMD",
        "NVIDIA",
        "輝達",
        "Intel",
    ]

    for name in names:

        if name.lower() in text.lower():

            found.append(
                name
            )

    # --------------------------------------------------------
    # 去除重複
    # --------------------------------------------------------

    result = []

    seen = set()

    for item in found:

        if item in seen:
            continue

        seen.add(item)

        result.append(
            item
        )

    return result[:20]


def _asset_display_name(
    asset: str
) -> str:

    # 四位數代號
    if re.fullmatch(
        r"\d{4}",
        asset
    ):

        name = STOCK_NAMES.get(
            asset
        )

        if name:

            return (
                f"{asset} {name}"
            )

        return asset


    # 公司名稱
    code = NAME_TO_STOCK.get(
        asset
    )

    if code:

        return (
            f"{code} {asset}"
        )

    return asset


def _assets_with_names(
    assets: list[str]
) -> list[str]:

    result = []

    seen = set()

    for asset in assets:

        display = _asset_display_name(
            asset
        )

        if display in seen:
            continue

        seen.add(
            display
        )

        result.append(
            display
        )

    return result[:15]


def _score(
    text: str,
    keywords: list[str],
) -> int:

    score = 25

    important = [
        "重大",
        "財報",
        "營收",
        "獲利",
        "EPS",
        "降息",
        "升息",
        "關稅",
        "法說",
        "展望",
        "訂單",
        "AI",
        "台積電",
        "半導體",
        "記憶體",
        "突破",
        "創高",
    ]

    text_lower = text.lower()

    for word in important:

        if word.lower() in text_lower:

            score += 4

    for word in keywords:

        if word.lower() in text_lower:

            score += 3

    if "%" in text:

        score += 5

    if re.search(
        r"\d{2,}",
        text
    ):

        score += 5

    return max(
        0,
        min(
            100,
            score
        )
    )


def analyze_rules(
    title: str = "",
    description: str = "",
    transcript: str = "",
    keywords: list[str] | None = None,
    video: dict | None = None,
) -> dict:

    # --------------------------------------------------------
    # 相容 main.py
    #
    # main.py 現在會傳：
    #
    # analyze_rules(
    #     video=video,
    #     title=...,
    #     description=...,
    #     transcript=...,
    #     keywords=...
    # )
    #
    # 所以這裡同時支援 video。
    # --------------------------------------------------------

    if keywords is None:

        keywords = []


    if video:

        if not title:

            title = str(
                video.get(
                    "title",
                    ""
                )
            )

        if not description:

            description = str(
                video.get(
                    "description",
                    ""
                )
            )


    text = (
        f"{title}\n"
        f"{description}\n"
        f"{transcript}"
    )


    sentences = _sentences(
        text
    )


    ranked = []


    for sentence in sentences:

        sentence_score = 0


        if "%" in sentence:

            sentence_score += 4


        if re.search(
            r"\d{2,}",
            sentence
        ):

            sentence_score += 3


        for key in keywords:

            if key.lower() in sentence.lower():

                sentence_score += 3


        for category in CATEGORY_KEYWORDS:

            for word in CATEGORY_KEYWORDS[
                category
            ]:

                if word.lower() in sentence.lower():

                    sentence_score += 1


        ranked.append(
            (
                sentence_score,
                sentence
            )
        )


    ranked.sort(
        key=lambda x: x[0],
        reverse=True
    )


    key_points = []

    seen = set()


    for _, sentence in ranked:

        if sentence in seen:

            continue


        seen.add(
            sentence
        )


        key_points.append(
            sentence
        )


        if len(
            key_points
        ) >= 6:

            break


    if not key_points:

        key_points = [
            title
        ]


    facts = []


    for sentence in key_points:

        if (
            "%"
            in sentence

            or re.search(
                r"\d{2,}",
                sentence
            )
        ):

            facts.append(
                sentence
            )


    if not facts:

        facts = key_points[:3]


    category = _category(
        text
    )


    assets = _assets(
        text
    )


    assets_display = _assets_with_names(
        assets
    )


    score = _score(
        text,
        keywords
    )


    return {

        "score":
            score,

        "category":
            category,

        "summary":
            key_points[0][:180],

        "key_points":
            key_points[:6],

        "facts":
            facts[:5],

        "mentioned_assets":
            assets_display,

        "outlook":
            (
                "此版本使用規則式整理，"
                "未使用 AI 生成投資判斷。"
            ),

        "risks":
            [
                "規則式分析可能無法理解上下文。",
                "股票代號/公司名稱可能需要人工確認。",
            ],

        "reason":
            (
                "依影片關鍵字、數字、"
                "百分比與重要詞彙計分。"
            ),
    }
