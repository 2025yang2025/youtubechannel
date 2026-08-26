from __future__ import annotations

import re


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
        "NVIDIA",
        "輝達",
        "AMD",
    ],

    "AI": [
        "AI",
        "人工智慧",
        "GPU",
        "大模型",
        "LLM",
        "機器人",
    ],

    "半導體": [
        "半導體",
        "晶圓",
        "先進製程",
        "封裝",
        "HBM",
        "記憶體",
        "晶片",
    ],

    "電子": [
        "電子",
        "PCB",
        "被動元件",
        "散熱",
        "伺服器",
        "網通",
    ],

    "能源": [
        "綠能",
        "能源",
        "太陽能",
        "風電",
        "儲能",
        "電動車",
    ],

    "總經": [
        "FED",
        "聯準會",
        "降息",
        "升息",
        "通膨",
        "CPI",
        "GDP",
        "利率",
        "美元",
    ],
}


# ============================================================
# 股票代號 → 中文名稱
# ============================================================

STOCK_NAMES = {

    "2330": "台積電",
    "2303": "聯電",
    "2454": "聯發科",
    "2317": "鴻海",
    "2382": "廣達",
    "6669": "緯穎",
    "2308": "台達電",
    "3711": "日月光投控",
    "2376": "技嘉",
    "2357": "華碩",
    "3231": "緯創",
    "3017": "奇鋐",
    "3037": "欣興",
    "3044": "健鼎",
    "2618": "長榮航",
    "2603": "長榮",
    "2609": "陽明",
    "2615": "萬海",
    "2881": "富邦金",
    "2882": "國泰金",
    "2886": "兆豐金",
    "2891": "中信金",
    "2892": "第一金",
    "2884": "玉山金",
    "2301": "光寶科",
    "2324": "仁寶",
    "2356": "英業達",
    "2377": "微星",
    "2379": "瑞昱",
    "2408": "南亞科",
    "2409": "友達",
    "3481": "群創",
    "2344": "華邦電",
    "2337": "旺宏",
    "6770": "力積電",
    "3008": "大立光",
    "2049": "上銀",
    "2048": "中纖",
    "3034": "聯詠",
    "3443": "創意",
    "3661": "世芯-KY",
    "5274": "信驊",
    "2376": "技嘉",
    "2353": "宏碁",
    "2327": "國巨",
    "8046": "南電",
    "2313": "華通",
    "2312": "金寶",
    "2368": "金像電",
    "2383": "台光電",
    "6668": "中揚光",
    "2404": "漢唐",
    "6239": "力成",
    "2449": "京元電子",
    "3711": "日月光投控",
    "6176": "瑞儀",
    "2302": "麗正",
    "1605": "華新",
    "1609": "大亞",
    "1519": "華城",
    "1503": "士電",
    "1513": "中興電",
    "6446": "藥華藥",
    "4123": "晟德",
    "6547": "高端疫苗",
}


# ============================================================
# 文字清理
# ============================================================

def _clean_text(text: str) -> str:

    if not text:
        return ""

    text = text.replace(
        "\r",
        "\n"
    )

    # 移除大量 URL
    text = re.sub(
        r"https?://\S+",
        "",
        text
    )

    # 移除 HTML
    text = re.sub(
        r"<[^>]+>",
        " ",
        text
    )

    # 多個空白
    text = re.sub(
        r"[ \t]+",
        " ",
        text
    )

    return text.strip()


# ============================================================
# 句子切割
# ============================================================

def _sentences(
    text: str,
) -> list[str]:

    raw = re.split(
        r"[。！？!?；;\n]+",
        text
    )

    result = []

    for sentence in raw:

        sentence = sentence.strip()

        if len(sentence) < 12:
            continue

        result.append(sentence)

    return result


# ============================================================
# 分類
# ============================================================

def _category(
    text: str,
) -> str:

    scores = {}

    lower_text = text.lower()

    for name, keywords in CATEGORY_KEYWORDS.items():

        score = 0

        for keyword in keywords:

            if keyword.lower() in lower_text:

                score += 1

        scores[name] = score

    if not scores:
        return "其他"

    best = max(
        scores,
        key=scores.get
    )

    if scores[best] <= 0:
        return "其他"

    return best


# ============================================================
# 股票代號
# ============================================================

def _stock_codes(
    text: str,
) -> list[str]:

    found = re.findall(
        r"(?<!\d)\d{4}(?!\d)",
        text
    )

    result = []

    seen = set()

    for code in found:

        if code in seen:
            continue

        seen.add(code)

        result.append(code)

    return result[:15]


# ============================================================
# 股票名稱
# ============================================================

def _stock_names(
    text: str,
) -> list[str]:

    result = []

    for code, name in STOCK_NAMES.items():

        if code in text or name in text:

            if name not in result:

                result.append(name)

    return result[:15]


# ============================================================
# 產業
# ============================================================

def _industries(
    text: str,
) -> list[str]:

    industry_keywords = [

        "AI",
        "半導體",
        "記憶體",
        "伺服器",
        "PCB",
        "被動元件",
        "散熱",
        "網通",
        "機器人",
        "綠能",
        "太陽能",
        "風電",
        "儲能",
        "電動車",
        "金融",
        "航運",
        "生技",
        "原油",
        "能源",
    ]

    result = []

    for item in industry_keywords:

        if item.lower() in text.lower():

            if item not in result:

                result.append(item)

    return result[:10]


# ============================================================
# 相同內容過濾
# ============================================================

def _unique_sentences(
    sentences: list[str],
) -> list[str]:

    result = []

    seen = set()

    for sentence in sentences:

        normalized = re.sub(
            r"\s+",
            "",
            sentence
        )

        if normalized in seen:
            continue

        seen.add(normalized)

        result.append(sentence)

    return result


# ============================================================
# 句子重要度
# ============================================================

def _sentence_score(
    sentence: str,
    keywords: list[str],
) -> int:

    score = 0

    lower = sentence.lower()

    important_words = [

        "營收",
        "獲利",
        "EPS",
        "財報",
        "法說",
        "訂單",
        "展望",
        "成長",
        "衰退",
        "突破",
        "創高",
        "轉強",
        "轉弱",
        "買進",
        "賣出",
        "布局",
        "主力",
        "外資",
        "法人",
        "產業",
        "需求",
        "供給",
        "價格",
        "漲",
        "跌",
    ]

    for word in important_words:

        if word.lower() in lower:

            score += 2

    for keyword in keywords:

        if keyword.lower() in lower:

            score += 2

    if "%" in sentence:

        score += 3

    if re.search(
        r"\d{2,}",
        sentence
    ):

        score += 2

    if re.search(
        r"\d{4}",
        sentence
    ):

        score += 2

    return score


# ============================================================
# 整體評分
# ============================================================

def _score(
    text: str,
    keywords: list[str],
) -> int:

    score = 25

    lower = text.lower()

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
        "主力",
        "外資",
        "法人",
    ]

    for word in important:

        if word.lower() in lower:

            score += 3

    for word in keywords:

        if word.lower() in lower:

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


# ============================================================
# 主分析函式
#
# 注意：
# main.py 必須使用：
#
# analyze_rules(
#     title=...,
#     description=...,
#     transcript=...,
#     keywords=...
# )
#
# ============================================================

def analyze_rules(
    title: str,
    description: str,
    transcript: str,
    keywords: list[str],
) -> dict:

    title = _clean_text(title)

    description = _clean_text(description)

    transcript = _clean_text(transcript)

    text = (
        f"{title}\n"
        f"{description}\n"
        f"{transcript}"
    )

    text = _clean_text(text)

    sentences = _sentences(text)

    sentences = _unique_sentences(
        sentences
    )

    # --------------------------------------------------------
    # 排序
    # --------------------------------------------------------

    ranked = []

    for sentence in sentences:

        score = _sentence_score(
            sentence,
            keywords
        )

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

    # --------------------------------------------------------
    # 取得重點
    # --------------------------------------------------------

    key_points = []

    for _, sentence in ranked:

        if sentence in key_points:
            continue

        key_points.append(sentence)

        if len(key_points) >= 6:
            break

    if not key_points:

        key_points = [
            title
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
                sentence
            )

            or any(
                word in sentence
                for word in [
                    "營收",
                    "獲利",
                    "EPS",
                    "訂單",
                    "展望",
                    "法人",
                    "外資",
                ]
            )
        ):

            facts.append(sentence)

    if not facts:

        facts = key_points[:3]

    # --------------------------------------------------------
    # 股票
    # --------------------------------------------------------

    stock_codes = _stock_codes(
        text
    )

    stock_names = _stock_names(
        text
    )

    industries = _industries(
        text
    )

    category = _category(
        text
    )

    score = _score(
        text,
        keywords
    )

    # --------------------------------------------------------
    # Summary
    # --------------------------------------------------------

    summary = key_points[0]

    if len(summary) > 180:

        summary = summary[:177] + "..."

    # --------------------------------------------------------
    # 回傳
    # --------------------------------------------------------

    return {

        "score":
            score,

        "category":
            category,

        "summary":
            summary,

        "key_points":
            key_points[:6],

        "facts":
            facts[:5],

        "mentioned_assets":
            stock_codes,

        "stock_codes":
            stock_codes,

        "stock_names":
            stock_names,

        "industries":
            industries,

        "outlook":
            (
                "此版本使用規則式整理，"
                "未使用 AI 生成投資判斷。"
            ),

        "risks":
            [
                "規則式分析可能無法理解上下文。",
                "股票代號與公司名稱以目前內建資料庫辨識。",
                "影片字幕無法取得時，可能只分析影片 Description。",
            ],

        "reason":
            (
                "依影片關鍵字、數字、"
                "百分比與重要詞彙計分。"
            ),
    }
