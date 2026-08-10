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


ASSET_PATTERNS = [

    r"\b\d{4}\b",

    r"台積電",

    r"聯發科",

    r"鴻海",

    r"廣達",

    r"緯穎",

    r"台達電",

    r"日月光",

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

            for keyword
            in keywords

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


    for pattern in ASSET_PATTERNS:

        found.extend(
            re.findall(
                pattern,
                text
            )
        )


    result = []

    seen = set()


    for item in found:

        if item in seen:

            continue

        seen.add(item)

        result.append(item)


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


    for word in important:

        if word.lower() in text.lower():

            score += 4


    for word in keywords:

        if word.lower() in text.lower():

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

    title: str,

    description: str,

    transcript: str,

    keywords: list[str],

) -> dict:

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

        score = 0


        if "%" in sentence:

            score += 4


        if re.search(
            r"\d{2,}",
            sentence
        ):

            score += 3


        for key in keywords:

            if key.lower() in sentence.lower():

                score += 3


        for category in CATEGORY_KEYWORDS:

            for word in CATEGORY_KEYWORDS[
                category
            ]:

                if word.lower() in sentence.lower():

                    score += 1


        ranked.append(
            (
                score,
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


        seen.add(sentence)

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

            "%" in sentence

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
            assets,

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
