from __future__ import annotations

import re


# ============================================================
# Telegram Markdown 清理
# ============================================================

def _clean(
    text: str,
) -> str:

    if not text:
        return ""

    text = str(text)

    # 移除 URL
    text = re.sub(
        r"https?://\S+",
        "",
        text
    )

    # 移除大量 hashtag
    text = re.sub(
        r"(?:^|\s)#[^\s#]+",
        "",
        text
    )

    # 清除多餘空白
    text = re.sub(
        r"[ \t]+",
        " ",
        text
    )

    text = re.sub(
        r"\n{3,}",
        "\n\n",
        text
    )

    return text.strip()


# ============================================================
# 截斷
# ============================================================

def _truncate(
    text: str,
    limit: int,
) -> str:

    if len(text) <= limit:
        return text

    return text[:limit - 3] + "..."


# ============================================================
# 股票
# ============================================================

def _format_stocks(
    analysis: dict,
) -> list[str]:

    codes = analysis.get(
        "stock_codes",
        []
    )

    names = analysis.get(
        "stock_names",
        []
    )

    result = []

    # --------------------------------------------------------
    # 如果有中文名稱，優先組合
    # --------------------------------------------------------

    used_names = set()

    for code in codes:

        # 目前由 rules.py 建立的中文名稱資料
        name = ""

        # 先從 mentioned_assets / stock_names 推估
        for candidate in names:

            if candidate in used_names:
                continue

            name = candidate
            break

        if name:

            result.append(
                f"{code} {name}"
            )

            used_names.add(name)

        else:

            result.append(
                code
            )

    # --------------------------------------------------------
    # 沒有代號但有公司名稱
    # --------------------------------------------------------

    for name in names:

        if name in used_names:
            continue

        result.append(name)

    return result[:10]


# ============================================================
# 主訊息
# ============================================================

def format_message(
    video: dict,
    analysis: dict,
) -> str:

    channel_name = _clean(
        video.get(
            "channel_name",
            ""
        )
    )

    title = _clean(
        video.get(
            "title",
            "未命名影片"
        )
    )

    category = _clean(
        analysis.get(
            "category",
            "其他"
        )
    )

    score = int(
        analysis.get(
            "score",
            0
        )
    )

    key_points = analysis.get(
        "key_points",
        []
    )

    facts = analysis.get(
        "facts",
        []
    )

    industries = analysis.get(
        "industries",
        []
    )

    stock_items = _format_stocks(
        analysis
    )

    video_url = video.get(
        "url",
        ""
    )

    # ========================================================
    # 開始組合
    # ========================================================

    lines = []

    # --------------------------------------------------------
    # 頻道
    # --------------------------------------------------------

    if channel_name:

        lines.append(
            f"📺 {channel_name}"
        )

    # --------------------------------------------------------
    # 標題
    # --------------------------------------------------------

    lines.append(
        f"\n🎬 {_truncate(title, 180)}"
    )

    # --------------------------------------------------------
    # 分類 / 分數
    # --------------------------------------------------------

    lines.append(
        f"\n📊 評分：{score}/100"
    )

    lines.append(
        f"📂 分類：{category}"
    )

    # --------------------------------------------------------
    # 重點
    # --------------------------------------------------------

    if key_points:

        lines.append(
            "\n📌 重點整理"
        )

        count = 0

        for point in key_points:

            point = _clean(point)

            if not point:
                continue

            # 避免超長
            point = _truncate(
                point,
                180
            )

            count += 1

            lines.append(
                f"{count}. {point}"
            )

            if count >= 5:
                break

    # --------------------------------------------------------
    # 關鍵資訊
    # --------------------------------------------------------

    if facts:

        lines.append(
            "\n💡 關鍵資訊"
        )

        count = 0

        for fact in facts:

            fact = _clean(fact)

            if not fact:
                continue

            fact = _truncate(
                fact,
                160
            )

            # 避免和重點完全一樣
            if fact in key_points:
                continue

            lines.append(
                f"• {fact}"
            )

            count += 1

            if count >= 3:
                break

    # --------------------------------------------------------
    # 股票
    # --------------------------------------------------------

    if stock_items:

        lines.append(
            "\n📈 提及標的"
        )

        for item in stock_items:

            lines.append(
                f"• {item}"
            )

    # --------------------------------------------------------
    # 產業
    # --------------------------------------------------------

    if industries:

        lines.append(
            "\n🏭 相關產業"
        )

        for industry in industries[:8]:

            lines.append(
                f"• {industry}"
            )

    # --------------------------------------------------------
    # 影片觀點
    # --------------------------------------------------------

    outlook = _clean(
        analysis.get(
            "outlook",
            ""
        )
    )

    if outlook:

        lines.append(
            f"\n🧠 影片觀點\n{_truncate(outlook, 180)}"
        )

    # --------------------------------------------------------
    # 風險
    # --------------------------------------------------------

    risks = analysis.get(
        "risks",
        []
    )

    if risks:

        lines.append(
            "\n⚠️ 注意"
        )

        for risk in risks[:2]:

            risk = _clean(risk)

            if risk:

                lines.append(
                    f"• {_truncate(risk, 150)}"
                )

    # --------------------------------------------------------
    # 原影片
    # --------------------------------------------------------

    if video_url:

        lines.append(
            f"\n🔗 原影片\n{video_url}"
        )

    # --------------------------------------------------------
    # 最後免責
    # --------------------------------------------------------

    lines.append(
        "\n⚠️ 以上為影片內容整理，"
        "不代表投資建議。"
    )

    return "\n".join(lines)
