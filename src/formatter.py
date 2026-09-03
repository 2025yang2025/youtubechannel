from __future__ import annotations

import re


def _clean_point(text: str) -> str:
    text = re.sub(r"\s+", " ", str(text or "")).strip(" •-\t\n")
    text = re.sub(r"https?://\S+|www\.\S+", "", text, flags=re.I).strip()
    return text


def format_message(video: dict, analysis: dict) -> str:
    channel = str(video.get("channel_name", "未知頻道")).strip()
    points: list[str] = []

    for raw in analysis.get("key_points", []):
        point = _clean_point(raw)
        if len(point) < 18:
            continue
        if point not in points:
            points.append(point)
        if len(points) >= 4:
            break

    lines = [f"📺 {channel}", "", "🎯 影片重點"]
    if points:
        lines.extend(f"• {p}" for p in points)
    else:
        lines.append("• 此影片目前沒有足夠文字內容可整理。")

    assets: list[str] = []
    seen: set[str] = set()
    for item in analysis.get("mentioned_assets", []):
        if isinstance(item, str):
            name = item.strip()
            code = ""
        else:
            name = str(item.get("name", "")).strip()
            code = str(item.get("code", "")).strip()

        if code and not re.fullmatch(r"\d{4}", code):
            code = ""
        label = f"{code} {name}".strip() if code else name
        if label and label not in seen:
            seen.add(label)
            assets.append(label)

    if assets:
        lines += ["", "🏷 提及個股 / 公司"]
        lines.extend(f"• {x}" for x in assets[:12])

    lines += ["", "⚠️ 以上為影片內容整理，不代表投資建議。"]
    return "\n".join(lines)
