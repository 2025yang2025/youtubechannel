from __future__ import annotations

import re
from typing import Any


# ============================================================
# 分類關鍵字
# ============================================================

CATEGORY_KEYWORDS = {
    "台股": [
        "台股",
        "加權",
        "櫃買",
        "上市",
        "上櫃",
        "台積電",
        "聯電",
        "聯發科",
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

    "綠能": [
        "綠能",
        "太陽能",
        "光電",
        "風電",
        "再生能源",
        "儲能",
        "能源",
    ],

    "機器人": [
        "機器人",
        "Robot",
        "人形機器人",
        "自動化",
    ],
}


# ============================================================
# 股票代號 → 中文名稱
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
    "6179": "亞通",
    "6239": "力成",
    "6669": "緯穎",
    "6672": "騰輝電子-KY",
    "6770": "力積電",
    "6805": "富世達",
    "8046": "南電",
    "8299": "群聯",
    "8996": "高力",
}


NAME_TO_STOCK = {
    name: code
    for code, name in STOCK_NAMES.items()
}


# ============================================================
# 常見公司名稱
# ============================================================

COMPANY_NAMES = [
    "台積電",
    "聯電",
    "聯發科",
    "鴻海",
    "廣達",
    "緯穎",
    "台達電",
    "日月光",
    "南亞科",
    "國巨",
    "欣興",
    "南電",
    "力積電",
    "華邦電",
    "群聯",
    "威剛",
    "亞通",
    "亞德客",
    "中鋼",
    "台泥",
    "統一",
    "台塑",
    "南亞",
    "光寶科",
    "智邦",
    "華碩",
    "金像電",
    "技嘉",
    "微星",
    "台光電",
    "研華",
    "義隆",
    "聯詠",
    "緯創",
    "創意",
    "嘉澤",
    "世芯",
    "臻鼎",
    "祥碩",
    "信驊",
    "中美晶",
    "中租",
    "富世達",
    "高力",
    "AMD",
    "NVIDIA",
    "輝達",
    "Intel",
]


# ============================================================
# 句子切割
# ============================================================

def _sentences(text: str) -> list[str]:

    raw = re.split(
        r"[。！？!?；;\n]",
        text,
    )

    result = []

    for sentence in raw:

        sentence = sentence.strip()

        if len(sentence) >= 12:
            result.append(sentence)

    return result


# ============================================================
# 分類
# ============================================================

def _category(text: str) -> str:

    scores = {}

    lower_text = text.lower()

    for name, keywords in CATEGORY_KEYWORDS.items():

        score = 0

        for keyword in keywords:

            score += lower_text.count(
                keyword.lower()
            )

        scores[name] = score

    if not scores:
        return "其他"

    best = max(
        scores,
        key=scores.get,
    )

    if scores[best] <= 0:
        return "其他"

    return best


# ============================================================
# 找股票代號與公司名稱
# ============================================================

def _assets(text: str) -> list[str]:

    found = []

    # 四位數股票代號
    codes = re.findall(
        r"(?<!\d)\d{4}(?!\d)",
        text,
    )

    found.extend(codes)

    # 公司名稱
    lower_text = text.lower()

    for name in COMPANY_NAMES:

        if name.lower() in lower_text:
            found.append(name)

    # 去重
    result = []
    seen = set()

    for item in found:

        if item in seen:
            continue

        seen.add(item)
        result.append(item)

    return result[:20]


# ============================================================
# 股票顯示：
#
# 2330 → 2330 台積電
# 台積電 → 2330 台積電
# ============================================================

def _asset_display_name(asset: str) -> str:

    if re.fullmatch(
        r"\d{4}",
        asset,
    ):

        name = STOCK_NAMES.get(asset)

        if name:
            return f"{asset} {name}"

        return asset

    code = NAME_TO_STOCK.get(asset)

    if code:
        return f"{code} {asset}"

    return asset


def _assets_with_names(
    assets: list[str],
) -> list[str]:

    result = []
    seen = set()

    for asset in assets:

        display = _asset_display_name(
            asset
        )

        if display in seen:
            continue

        seen.add(display)
        result.append(display)

    return result[:15]


# ============================================================
# 評分
# ============================================================

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
        "轉強",
        "黑馬",
        "成長",
    ]

    lower_text = text.lower()

    for word in important:

        if word.lower() in lower_text:
            score += 4

    for word in keywords:

        if word.lower() in lower_text:
            score += 3

    if "%" in text:
        score += 5

    if re.search(
        r"\d{2,}",
        text,
    ):
        score += 5

    return max(
        0,
        min(
            100,
            score,
        ),
    )


# ============================================================
# 取得 Channel 資訊
# ============================================================

def _channel_keywords(
    channel: Any,
) -> list[str]:

    if channel is None:
        return []

    # dataclass Channel
    if hasattr(channel, "keywords"):

        value = channel.keywords

        if value:
            return [
                str(x)
                for x in value
            ]

    # dict Channel
    if isinstance(channel, dict):

        value = channel.get(
            "keywords",
            [],
        )

        if value:
            return [
                str(x)
                for x in value
            ]

    return []


# ============================================================
# Rules 分析
#
# ★ 相容所有目前 main.py 版本
#
# 支援：
#
# video
# text
# channel
# title
# description
# transcript
# keywords
# ============================================================

def analyze_rules(
    title: str = "",
    description: str = "",
    transcript: str = "",
    keywords: list[str] | None = None,
    video: dict | None = None,
    text: str = "",
    channel: Any = None,
) -> dict:

    # --------------------------------------------------------
    # keywords
    # --------------------------------------------------------

    if keywords is None:

        keywords = _channel_keywords(
            channel
        )

    # --------------------------------------------------------
    # channel 補 keywords
    # --------------------------------------------------------

    if not keywords:

        keywords = _channel_keywords(
            channel
        )

    # --------------------------------------------------------
    # video 補資料
    # --------------------------------------------------------

    if video:

        if not title:

            title = str(
                video.get(
                    "title",
                    "",
                )
            )

        if not description:

            description = str(
                video.get(
                    "description",
                    "",
                )
            )

    # --------------------------------------------------------
    # 分析文字
    #
    # main.py 如果傳 text：
    # 優先使用 text
    #
    # 否則：
    # title + description + transcript
    # --------------------------------------------------------

    if text:

        analysis_text = text

    else:

        analysis_text = (
            f"{title}\n"
            f"{description}\n"
            f"{transcript}"
        )

    # --------------------------------------------------------
    # 完全沒有文字
    # --------------------------------------------------------

    if not analysis_text.strip():

        analysis_text = (
            title
            or description
            or "影片未取得文字內容。"
        )

    # --------------------------------------------------------
    # 句子
    # --------------------------------------------------------

    sentences = _sentences(
        analysis_text
    )

    ranked = []

    for sentence in sentences:

        sentence_score = 0

        if "%" in sentence:
            sentence_score += 4

        if re.search(
            r"\d{2,}",
            sentence,
        ):
            sentence_score += 3

        lower_sentence = (
            sentence.lower()
        )

        for keyword in keywords:

            if keyword.lower() in lower_sentence:
                sentence_score += 3

        for category_keywords in CATEGORY_KEYWORDS.values():

            for word in category_keywords:

                if word.lower() in lower_sentence:
                    sentence_score += 1

        ranked.append(
            (
                sentence_score,
                sentence,
            )
        )

    # --------------------------------------------------------
    # 排序
    # --------------------------------------------------------

    ranked.sort(
        key=lambda x: x[0],
        reverse=True,
    )

    # --------------------------------------------------------
    # 取 6 個重點
    # --------------------------------------------------------

    key_points = []

    seen = set()

    for _, sentence in ranked:

        if sentence in seen:
            continue

        seen.add(sentence)

        key_points.append(
            sentence
        )

        if len(key_points) >= 6:
            break

    # --------------------------------------------------------
    # 沒有句子
    # --------------------------------------------------------

    if not key_points:

        key_points = [
            title[:180]
            if title
            else "影片未取得足夠文字內容。"
        ]

    # --------------------------------------------------------
    # 關鍵資訊
    # --------------------------------------------------------

    facts = []

    for sentence in key_points:

        if (
            "%"
            in sentence

            or re.search(
                r"\d{2,}",
                sentence,
            )
        ):

            facts.append(
                sentence
            )

    if not facts:

        facts = key_points[:3]

    # --------------------------------------------------------
    # 分類
    # --------------------------------------------------------

    category = _category(
        analysis_text
    )

    # --------------------------------------------------------
    # 股票
    # --------------------------------------------------------

    assets = _assets(
        analysis_text
    )

    assets_display = _assets_with_names(
        assets
    )

    # --------------------------------------------------------
    # 評分
    # --------------------------------------------------------

    score = _score(
        analysis_text,
        keywords,
    )

    # --------------------------------------------------------
    # Summary
    # --------------------------------------------------------

    summary = key_points[0]

    if len(summary) > 180:

        summary = (
            summary[:180]
            + "..."
        )

    # --------------------------------------------------------
    # 回傳
    # --------------------------------------------------------

    return {

        "score": score,

        "category": category,

        "summary": summary,

        "key_points": key_points[:6],

        "facts": facts[:5],

        "mentioned_assets": assets_display,

        "outlook": (
            "此版本使用規則式整理，"
            "未使用 AI 生成投資判斷。"
        ),

        "risks": [
            "規則式分析可能無法完整理解影片上下文。",
            "股票代號與公司名稱仍可能需要人工確認。",
        ],

        "reason": (
            "依影片關鍵字、數字、百分比、"
            "產業詞彙與重要詞彙計分。"
        ),
    }
