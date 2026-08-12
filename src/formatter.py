from __future__ import annotations

import re
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]

STOCK_FILE = (
    ROOT
    / "config"
    / "stock_names.yaml"
)


def load_stock_names() -> dict[str, str]:
    """
    載入股票代號 → 中文名稱。
    """

    if not STOCK_FILE.exists():
        return {}

    try:

        with open(
            STOCK_FILE,
            "r",
            encoding="utf-8",
        ) as f:

            data = yaml.safe_load(f) or {}

        stocks = data.get(
            "stocks",
            {},
        )

        return {
            str(code): str(name)
            for code, name
            in stocks.items()
        }

    except Exception:
        return {}


STOCK_NAMES = load_stock_names()


def normalize_stock_code(
    code: str,
) -> str:

    code = str(code).strip()

    return code


def stock_label(
    code: str,
) -> str:
    """
    將股票代號轉成：

        台積電（2330）

    如果沒有資料：

        2330（名稱待確認）
    """

    code = normalize_stock_code(
        code
    )

    name = STOCK_NAMES.get(
        code
    )

    if name:

        return f"{name}（{code}）"

    return f"{code}（名稱待確認）"


def extract_stock_codes(
    text: str,
) -> list[str]:
    """
    從文字中抓股票代號。

    只接受 4 位數字，
    避免把時間、年份、百分比亂當股票。

    例如：

        2330 → 保留
        2303 → 保留

        0811 → 排除
        2026 → 排除
        04:30 → 排除
    """

    if not text:
        return []

    candidates = re.findall(
        r"(?<!\d)(\d{4})(?!\d)",
        text,
    )

    result = []

    for code in candidates:

        # 排除年份
        if code.startswith(
            ("19", "20")
        ):
            continue

        # 排除月份/日期類
        if code[:2] in {
            "01",
            "02",
            "03",
            "04",
            "05",
            "06",
            "07",
            "08",
            "09",
            "10",
            "11",
            "12",
        }:
            # 如果它真的在股票清單裡，
            # 仍然保留
            if code not in STOCK_NAMES:
                continue

        # 只保留已知股票
        if code not in STOCK_NAMES:
            continue

        if code not in result:

            result.append(code)

    return result


def format_stock_list(
    analysis: dict,
    video: dict,
) -> str:

    codes = []

    # ---------------------------------------------------------
    # 優先使用 AI / Rules 已經辨識出的股票
    # ---------------------------------------------------------

    mentioned = analysis.get(
        "stocks",
        [],
    )

    if isinstance(
        mentioned,
        list,
    ):

        for item in mentioned:

            if isinstance(
                item,
                dict,
            ):

                code = str(
                    item.get(
                        "code",
                        "",
                    )
                ).strip()

            else:

                code = str(
                    item
                ).strip()

            if (
                code in STOCK_NAMES
                and code not in codes
            ):

                codes.append(code)

    # ---------------------------------------------------------
    # 再從影片文字補抓
    # ---------------------------------------------------------

    combined_text = " ".join(
        [
            str(
                video.get(
                    "title",
                    "",
                )
            ),
            str(
                video.get(
                    "description",
                    "",
                )
            ),
        ]
    )

    for code in extract_stock_codes(
        combined_text
    ):

        if code not in codes:

            codes.append(code)

    # ---------------------------------------------------------
    # 沒有股票
    # ---------------------------------------------------------

    if not codes:

        return "• 本片未辨識到明確股票標的"

    return "\n".join(
        f"• {stock_label(code)}"
        for code in codes[:15]
    )


def clean_text(
    text: str,
) -> str:

    if not text:
        return ""

    text = str(text)

    # ---------------------------------------------------------
    # 移除 URL
    # ---------------------------------------------------------

    text = re.sub(
        r"https?://\S+",
        "",
        text,
    )

    # ---------------------------------------------------------
    # 移除大量 hashtag
    # ---------------------------------------------------------

    text = re.sub(
        r"#[\w\u4e00-\u9fff\-]+",
        "",
        text,
    )

    # ---------------------------------------------------------
    # 移除多餘空白
    # ---------------------------------------------------------

    text = re.sub(
        r"[ \t]+",
        " ",
        text,
    )

    text = re.sub(
        r"\n{3,}",
        "\n\n",
        text,
    )

    return text.strip()


def format_core_points(
    analysis: dict,
) -> str:

    points = analysis.get(
        "core_points",
        [],
    )

    if not points:

        points = analysis.get(
            "key_points",
            [],
        )

    if not isinstance(
        points,
        list,
    ):

        return "• 本片重點整理不足"

    cleaned = []

    for point in points:

        text = clean_text(
            str(point)
        )

        if not text:
            continue

        # 避免整段 hashtag
        if text.startswith("#"):
            continue

        if text not in cleaned:

            cleaned.append(text)

    if not cleaned:

        return "• 本片重點整理不足"

    return "\n".join(
        f"• {point}"
        for point in cleaned[:6]
    )


def format_industries(
    analysis: dict,
) -> str:

    industries = analysis.get(
        "industries",
        [],
    )

    if not isinstance(
        industries,
        list,
    ):

        return "• 未明確辨識"

    cleaned = []

    for industry in industries:

        text = clean_text(
            str(industry)
        )

        if not text:
            continue

        if text not in cleaned:

            cleaned.append(text)

    if not cleaned:

        return "• 未明確辨識"

    return "\n".join(
        f"• {item}"
        for item in cleaned[:8]
    )


def format_timeline(
    analysis: dict,
) -> str:

    timeline = analysis.get(
        "timeline",
        [],
    )

    if not isinstance(
        timeline,
        list,
    ):

        return ""

    result = []

    for item in timeline:

        if isinstance(
            item,
            dict,
        ):

            time = str(
                item.get(
                    "time",
                    "",
                )
            ).strip()

            text = clean_text(
                str(
                    item.get(
                        "topic",
                        item.get(
                            "text",
                            "",
                        ),
                    )
                )
            )

            if time and text:

                result.append(
                    f"{time} {text}"
                )

        else:

            text = clean_text(
                str(item)
            )

            if text:
                result.append(text)

    if not result:

        return ""

    return "\n".join(
        result[:6]
    )


def format_message(
    video: dict,
    analysis: dict,
) -> str:
    """
    Telegram 最終訊息。

    固定為精簡情報格式。
    """

    score = analysis.get(
        "score",
        0,
    )

    try:
        score = int(score)
    except (
        TypeError,
        ValueError,
    ):
        score = 0

    score = max(
        0,
        min(
            100,
            score,
        ),
    )

    channel_name = (
        video.get(
            "channel_name"
        )
        or video.get(
            "channel_title"
        )
        or "YouTube"
    )

    title = clean_text(
        video.get(
            "title",
            "",
        )
    )

    core_points = format_core_points(
        analysis
    )

    stocks = format_stock_list(
        analysis,
        video,
    )

    industries = format_industries(
        analysis
    )

    timeline = format_timeline(
        analysis
    )

    analysis_source = (
        analysis.get(
            "analysis_source",
            "rules",
        )
    )

    if analysis_source == "gemini":

        analysis_label = "AI 摘要"

    else:

        analysis_label = "規則式摘要"

    lines = []

    lines.append(
        f"📌【{analysis_label}重要度 {score}/100】"
    )

    lines.append("")

    lines.append(
        f"📺 {channel_name}"
    )

    lines.append("")

    lines.append(
        f"🎬 {title}"
    )

    lines.append("")

    lines.append(
        "━━━━━━━━━━━━━━"
    )

    lines.append("")

    lines.append(
        "🎯 核心結論"
    )

    lines.append(
        core_points
    )

    lines.append("")

    lines.append(
        "📈 提及標的"
    )

    lines.append(
        stocks
    )

    lines.append("")

    lines.append(
        "🏭 提及產業"
    )

    lines.append(
        industries
    )

    if timeline:

        lines.append("")

        lines.append(
            "⏱ 影片重點"
        )

        lines.append(
            timeline
        )

    lines.append("")

    lines.append(
        "⚠️ 僅整理影片內容，不代表投資建議。"
    )

    lines.append("")

    url = video.get(
        "url",
        "",
    )

    if url:

        lines.append(
            "🔗 原影片"
        )

        lines.append(
            url
        )

    return "\n".join(
        lines
    )
