from __future__ import annotations

import re
from typing import Any


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


# ============================================================
# 安全取得欄位
# ============================================================

def _get_value(
    obj: Any,
    key: str,
    default: Any = "",
) -> Any:

    if obj is None:
        return default

    if isinstance(obj, dict):
        return obj.get(key, default)

    return getattr(
        obj,
        key,
        default,
    )


# ============================================================
# 股票名稱轉換
# ============================================================

def _format_asset(
    asset: str,
) -> str:

    asset = str(asset).strip()

    if not asset:
        return ""

    # 已經是「2330 台積電」
    if re.match(
        r"^\d{4}\s+.+$",
        asset,
    ):
        return asset

    # 純股票代號
    if re.fullmatch(
        r"\d{4}",
        asset,
    ):

        name = STOCK_NAMES.get(
            asset
        )

        if name:
            return f"{asset} {name}"

        return asset

    return asset


# ============================================================
# 股票清單
# ============================================================

def _format_assets(
    assets: Any,
) -> list[str]:

    if not assets:
        return []

    if isinstance(
        assets,
        str,
    ):
        assets = [assets]

    result = []
    seen = set()

    for asset in assets:

        formatted = _format_asset(
            asset
        )

        if not formatted:
            continue

        if formatted in seen:
            continue

        seen.add(formatted)

        result.append(
            formatted
        )

    return result[:10]


# ============================================================
# 清除雜訊
# ============================================================

def _clean_text(
    text: Any,
    max_length: int = 180,
) -> str:

    if text is None:
        return ""

    text = str(text)

    text = text.replace(
        "\r",
        " ",
    )

    text = re.sub(
        r"\s+",
        " ",
        text,
    )

    text = text.strip()

    if len(text) > max_length:

        text = (
            text[:max_length]
            + "..."
        )

    return text


# ============================================================
# 清理重點
# ============================================================

def _clean_points(
    points: Any,
    limit: int = 5,
) -> list[str]:

    if not points:
        return []

    if isinstance(
        points,
        str,
    ):
        points = [points]

    result = []
    seen = set()

    for point in points:

        point = _clean_text(
            point,
            220,
        )

        if not point:
            continue

        # 避免完全重複
        normalized = point.lower()

        if normalized in seen:
            continue

        seen.add(normalized)

        result.append(
            point
        )

        if len(result) >= limit:
            break

    return result


# ============================================================
# 核心主題
# ============================================================

def _build_topics(
    analysis: dict,
) -> list[str]:

    points = _clean_points(
        analysis.get(
            "key_points",
            [],
        ),
        3,
    )

    if points:
        return points

    summary = _clean_text(
        analysis.get(
            "summary",
            "",
        ),
        180,
    )

    if summary:
        return [summary]

    return []


# ============================================================
# 產生 Telegram 訊息
#
# 支援：
#
# format_message(video, analysis)
#
# 以及：
#
# format_message(
#     video=video,
#     analysis=analysis,
#     channel=channel,
# )
# ============================================================

def format_message(
    video: dict,
    analysis: dict,
    channel: Any = None,
) -> str:

    # --------------------------------------------------------
    # 影片資訊
    # --------------------------------------------------------

    title = _clean_text(
        _get_value(
            video,
            "title",
            "未命名影片",
        ),
        200,
    )

    description = _clean_text(
        _get_value(
            video,
            "description",
            "",
        ),
        300,
    )

    channel_name = _get_value(
        video,
        "channel_name",
        "",
    )

    # --------------------------------------------------------
    # 如果 video 沒有 channel_name
    # 從 channel 補
    # --------------------------------------------------------

    if not channel_name:

        channel_name = _get_value(
            channel,
            "name",
            "",
        )

    if not channel_name:

        channel_name = "YouTube 頻道"

    channel_name = _clean_text(
        channel_name,
        80,
    )

    # --------------------------------------------------------
    # Video URL
    # --------------------------------------------------------

    video_url = _get_value(
        video,
        "url",
        "",
    )

    if not video_url:

        video_id = _get_value(
            video,
            "video_id",
            "",
        )

        if video_id:

            video_url = (
                "https://www.youtube.com/watch?v="
                + str(video_id)
            )

    # --------------------------------------------------------
    # 分析資料
    # --------------------------------------------------------

    score = analysis.get(
        "score",
        0,
    )

    try:
        score = int(score)
    except Exception:
        score = 0

    category = _clean_text(
        analysis.get(
            "category",
            "其他",
        ),
        50,
    )

    # --------------------------------------------------------
    # 標的
    # --------------------------------------------------------

    assets = _format_assets(
        analysis.get(
            "mentioned_assets",
            [],
        )
    )

    # --------------------------------------------------------
    # 重點
    # --------------------------------------------------------

    key_points = _clean_points(
        analysis.get(
            "key_points",
            [],
        ),
        5,
    )

    # --------------------------------------------------------
    # 關鍵資訊
    # --------------------------------------------------------

    facts = _clean_points(
        analysis.get(
            "facts",
            [],
        ),
        3,
    )

    # --------------------------------------------------------
    # Summary
    # --------------------------------------------------------

    summary = _clean_text(
        analysis.get(
            "summary",
            "",
        ),
        180,
    )

    # --------------------------------------------------------
    # 建立訊息
    # --------------------------------------------------------

    lines = []

    lines.append(
        f"📌【{category}｜重要度 {score}/100】"
    )

    lines.append("")

    lines.append(
        f"📺 {channel_name}"
    )

    lines.append("")

    lines.append(
        f"🎬 {title}"
    )

    # --------------------------------------------------------
    # 核心主題
    # --------------------------------------------------------

    if summary:

        lines.append("")

        lines.append(
            "🎯 核心主題"
        )

        lines.append(
            f"• {summary}"
        )

    # --------------------------------------------------------
    # 重點整理
    # --------------------------------------------------------

    if key_points:

        lines.append("")

        lines.append(
            "📌 重點整理"
        )

        for index, point in enumerate(
            key_points,
            start=1,
        ):

            lines.append(
                f"{index}. {point}"
            )

    # --------------------------------------------------------
    # 提及標的 / 產業
    # --------------------------------------------------------

    if assets:

        lines.append("")

        lines.append(
            "📈 提及標的 / 產業"
        )

        for asset in assets:

            lines.append(
                f"• {asset}"
            )

    # --------------------------------------------------------
    # 關鍵資訊
    # --------------------------------------------------------

    if facts:

        # 避免 facts 與 key_points 完全重複
        unique_facts = []

        for fact in facts:

            if fact in key_points:
                continue

            unique_facts.append(
                fact
            )

        if unique_facts:

            lines.append("")

            lines.append(
                "📊 關鍵資訊"
            )

            for fact in unique_facts[:3]:

                lines.append(
                    f"• {fact}"
                )

    # --------------------------------------------------------
    # 觀點
    # --------------------------------------------------------

    outlook = _clean_text(
        analysis.get(
            "outlook",
            "",
        ),
        300,
    )

    if outlook:

        lines.append("")

        lines.append(
            "🧠 分析方式"
        )

        lines.append(
            f"• {outlook}"
        )

    # --------------------------------------------------------
    # 注意事項
    # --------------------------------------------------------

    risks = _clean_points(
        analysis.get(
            "risks",
            [],
        ),
        2,
    )

    if risks:

        lines.append("")

        lines.append(
            "⚠️ 注意事項"
        )

        for risk in risks:

            lines.append(
                f"• {risk}"
            )

    # --------------------------------------------------------
    # 原影片
    # --------------------------------------------------------

    if video_url:

        lines.append("")

        lines.append(
            "🔗 原影片"
        )

        lines.append(
            video_url
        )

    # --------------------------------------------------------
    # 最終訊息
    # --------------------------------------------------------

    message = "\n".join(
        lines
    )

    return message.strip()
