from __future__ import annotations

def _clip(text: str, limit: int) -> str:
    text = (text or "").strip()
    return text if len(text) <= limit else text[:limit-1].rstrip() + "…"

def format_message(video: dict, analysis: dict, channel_name: str = "", **_) -> str:
    channel = channel_name or analysis.get("channel_name") or video.get("channel_name", "")
    lines = [f"📺【{channel}】", "", f"🎬 {video.get('title', '未命名影片')}", "", "📌【重點個股】"]
    stocks = analysis.get("stocks", [])

    if not stocks:
        lines.append("影片中沒有明確強調的個股。")
    else:
        for s in stocks[:5]:
            name, code = s.get("name", "").strip(), s.get("code", "").strip()
            label = f"{name}（{code}）" if code else name
            lines += ["", f"🔹 {label}"]
            if s.get("development"):
                lines.append(f"後續發展：{_clip(s['development'], 240)}")
            if s.get("view"):
                lines.append(f"影片觀點：{_clip(s['view'], 200)}")

    lines += ["", "⚠️ 以上為影片內容整理，不代表投資建議。", "", "🔗 原影片", video.get("url", "")]
    return "\n".join(lines)

def split_message(message: str, limit: int = 3900) -> list[str]:
    if len(message) <= limit:
        return [message]
    chunks, current = [], ""
    for line in message.splitlines(True):
        if len(current) + len(line) <= limit:
            current += line
        else:
            if current: chunks.append(current.rstrip())
            current = line
    if current: chunks.append(current.rstrip())
    return chunks
