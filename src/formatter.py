from __future__ import annotations

import re


def _clean(value: str) -> str:

    if not value:
        return ""

    value = re.sub(
        r"https?://\S+",
        "",
        value,
    )

    value = re.sub(
        r"#\S+",
        "",
        value,
    )

    value = re.sub(
        r"\s+",
        " ",
        value,
    )

    return value.strip()


def _remove_duplicate_points(
    points: list[str],
) -> list[str]:

    result = []
    seen = set()

    for point in points:

        point = _clean(point)

        if not point:
            continue

        key = re.sub(
            r"\s+",
            "",
            point,
        )

        if key in seen:
            continue

        seen.add(key)
        result.append(point)

    return result


def format_message(
    video: dict,
    analysis: dict,
    channel=None,
) -> str:

    # -----------------------------------------------------
    # 頻道名稱
    # -----------------------------------------------------

    channel_name = (
        video.get("channel_name")
        or video.get("channel")
        or (
            getattr(channel, "name", "")
            if channel
            else ""
        )
        or "YouTube"
    )

    # -----------------------------------------------------
    # 標題
    # -----------------------------------------------------

    title = _clean(
        video.get(
            "title",
            "",
        )
    )

    # -----------------------------------------------------
    # 重點
    # -----------------------------------------------------

    points = analysis.get(
        "key_points",
        [],
    )

    if not isinstance(points, list):
        points = []

    points = _remove_duplicate_points(
        points
    )

    # -----------------------------------------------------
    # 個股
    # -----------------------------------------------------

    assets = analysis.get(
        "mentioned_assets",
        [],
    )

    if not isinstance(assets, list):
        assets = []

    asset_result = []

    seen_assets = set()

    for asset in assets:

        asset = _clean(
            str(asset)
        )

        if not asset:
            continue

        if asset in seen_assets:
            continue

        seen_assets.add(asset)
        asset_result.append(asset)

    # -----------------------------------------------------
    # 組合 Telegram
    # -----------------------------------------------------

    lines = []

    lines.append(
        f"📺 {channel_name}"
    )

    lines.append("")

    if title:

        lines.append(
            f"🎬 {title}"
        )

        lines.append("")

    # -----------------------------------------------------
    # 影片重點
    # -----------------------------------------------------

    lines.append(
        "🔎 影片重點"
    )

    if points:

        for point in points[:5]:

            lines.append(
                f"• {point}"
            )

    else:

        lines.append(
            "• 目前無法取得足夠影片內容。"
        )

    # -----------------------------------------------------
    # 個股
    # -----------------------------------------------------

    if asset_result:

        lines.append("")

        lines.append(
            "📈 提及個股"
        )

        for asset in asset_result[:15]:

            lines.append(
                f"• {asset}"
            )

    return "\n".join(lines)