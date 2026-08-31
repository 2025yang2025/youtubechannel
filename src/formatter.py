from __future__ import annotations


def _safe(value) -> str:
    if value is None:
        return ""

    return str(value).strip()


def format_message(
    video: dict,
    analysis: dict,
) -> str:

    channel_name = _safe(
        video.get(
            "channel_name",
            "YouTube",
        )
    )

    title = _safe(
        video.get(
            "title",
            "",
        )
    )

    video_url = _safe(
        video.get(
            "url",
            "",
        )
    )

    lines = []

    lines.append(
        f"📺 {channel_name}"
    )

    lines.append("")

    lines.append(
        f"🎬 {title}"
    )

    lines.append("")

    stocks = analysis.get(
        "mentioned_stocks",
        [],
    )

    if stocks:

        lines.append(
            "📈 影片強調個股"
        )

        lines.append("")

        for stock in stocks:

            code = _safe(
                stock.get(
                    "code",
                    "",
                )
            )

            name = _safe(
                stock.get(
                    "name",
                    "",
                )
            )

            if code:
                lines.append(
                    f"【{name}（{code}）】"
                )
            else:
                lines.append(
                    f"【{name}】"
                )

            points = stock.get(
                "points",
                [],
            )

            for point in points[:3]:

                point = _safe(point)

                if not point:
                    continue

                lines.append(
                    f"• {point}"
                )

            lines.append("")

    else:

        lines.append(
            "📌 影片重點"
        )

        lines.append("")

        points = analysis.get(
            "key_points",
            [],
        )

        for point in points[:5]:

            point = _safe(point)

            if point:
                lines.append(
                    f"• {point}"
                )

        lines.append("")

    lines.append(
        "⚠️ 以上為影片內容整理，"
        "不代表投資建議。"
    )

    if video_url:

        lines.append("")

        lines.append(
            f"🔗 原影片\n{video_url}"
        )

    return "\n".join(lines)
