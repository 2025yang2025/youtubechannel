from __future__ import annotations


def bullet(
    items,
    fallback="無"
):

    if not items:

        return f"• {fallback}"


    return "\n".join(

        f"• {x}"

        for x in items
    )


def numbered(
    items,
    fallback="無"
):

    if not items:

        return f"1. {fallback}"


    return "\n".join(

        f"{i}. {x}"

        for i, x
        in enumerate(
            items,
            1
        )
    )


def format_message(

    video: dict,

    analysis: dict,

) -> str:

    score = int(
        analysis.get(
            "score",
            0
        )
    )


    if score >= 80:

        icon = "🚨"

    elif score >= 60:

        icon = "🔥"

    else:

        icon = "📌"


    return f"""\
{icon}【AI/規則重要度 {score}/100】

📺 {video['channel_name']}

🎬 {video['title']}


🏷 分類

{analysis.get(
    'category',
    '其他'
)}


🎯 核心主題

{analysis.get(
    'summary',
    ''
)}


📌 重點整理

{numbered(
    analysis.get(
        'key_points',
        []
    )
)}


📊 關鍵資訊

{bullet(
    analysis.get(
        'facts',
        []
    )
)}


📈 提及標的 / 產業

{bullet(
    analysis.get(
        'mentioned_assets',
        []
    )
)}


🧠 影片觀點

{analysis.get(
    'outlook',
    '無'
)}


⚠️ 注意事項

{bullet(
    analysis.get(
        'risks',
        []
    )
)}


🔎 評分理由

{analysis.get(
    'reason',
    ''
)}


⚠️ 以上為影片內容整理，
不代表投資建議。


🔗 原影片

{video['url']}
""".strip()
