from __future__ import annotations

import logging
import sys

from .config import (
    get_env,
    load_channels,
    load_settings,
    required_env,
)

from .formatter import (
    format_message,
)

from .gemini import (
    analyze_gemini,
)

from .rules import (
    analyze_rules,
)

from .state import (
    is_processed,
    load_state,
    mark_processed,
    save_state,
)

from .telegram import (
    send_message,
)

from .transcript import (
    get_transcript,
)

from .youtube import (
    get_latest_videos,
)


logging.basicConfig(
    level=logging.INFO,
    format=(
        "%(asctime)s | "
        "%(levelname)s | "
        "%(message)s"
    ),
)


def _get_channel_value(channel, name, default=None):
    """
    相容目前的 Channel dataclass / object。

    例如：
        channel.name
        channel.handle
        channel.channel_id
        channel.keywords
        channel.min_score
    """

    return getattr(
        channel,
        name,
        default,
    )


def main() -> int:

    # =========================================================
    # Settings
    # =========================================================

    settings = load_settings()

    # =========================================================
    # Environment
    # =========================================================

    youtube_key = required_env(
        "YOUTUBE_API_KEY"
    )

    telegram_token = required_env(
        "TELEGRAM_BOT_TOKEN"
    )

    telegram_chat_id = required_env(
        "TELEGRAM_CHAT_ID"
    )

    gemini_key = get_env(
        "GEMINI_API_KEY"
    )

    gemini_model = get_env(
        "GEMINI_MODEL",
        settings.get(
            "ai",
            {}
        ).get(
            "default_gemini_model",
            "gemini-2.0-flash",
        ),
    )

    # =========================================================
    # AI settings
    # =========================================================

    use_gemini = bool(
        settings.get(
            "free_mode",
            {}
        ).get(
            "use_gemini_if_available",
            True,
        )
    )

    fallback_rules = bool(
        settings.get(
            "free_mode",
            {}
        ).get(
            "fallback_to_rules",
            True,
        )
    )

    # =========================================================
    # Channels
    #
    # 現在支援：
    #
    #   channel_id: UCxxxxxxxx
    #
    # 或：
    #
    #   handle: "@berich888"
    #
    # =========================================================

    all_channels = load_channels()

    channels = []

    for channel in all_channels:

        enabled = bool(
            _get_channel_value(
                channel,
                "enabled",
                False,
            )
        )

        if not enabled:
            continue

        channel_id = _get_channel_value(
            channel,
            "channel_id",
            "",
        )

        handle = _get_channel_value(
            channel,
            "handle",
            "",
        )

        # -----------------------------------------------------
        # 至少需要 channel_id 或 handle
        # -----------------------------------------------------

        if not channel_id and not handle:
            logging.warning(
                "頻道 %s 沒有 channel_id "
                "或 handle，跳過。",
                _get_channel_value(
                    channel,
                    "name",
                    "Unknown",
                ),
            )

            continue

        # -----------------------------------------------------
        # 舊版預設值排除
        # -----------------------------------------------------

        if (
            channel_id
            and channel_id.startswith(
                "UC_REPLACE"
            )
        ):
            channel_id = ""

        if not channel_id and not handle:
            continue

        channels.append(channel)

    if not channels:

        logging.error(
            "沒有啟用有效 YouTube 頻道。"
        )

        return 1

    # =========================================================
    # State
    # =========================================================

    state = load_state()

    # =========================================================
    # Monitor settings
    # =========================================================

max_videos = int(
    settings.get(
        "monitor",
        {}
    ).get(
        "max_videos_per_channel",
        3
    )
)

test_mode = bool(
    settings.get(
        "monitor",
        {}
    ).get(
        "test_mode",
        False
    )
)

if test_mode:

    logging.warning(
        "========================================"
    )

    logging.warning(
        "TEST MODE 已啟用"
    )

    logging.warning(
        "將忽略 state.json 的已處理紀錄"
    )

    logging.warning(
        "影片會重新進行 AI / Rules 分析"
    )

    logging.warning(
        "========================================"
    )


bootstrap = bool(
    settings.get(
        "monitor",
        {}
    ).get(
        "bootstrap",
        {}
    ).get(
        "mark_existing_as_processed",
        True
    )
)


languages = (
    settings.get(
        "transcript",
        {}
    ).get(
        "languages",
        [
            "zh-TW",
            "zh-Hant",
            "zh",
            "en",
        ]
    )
)


fallback_description = bool(
    settings.get(
        "transcript",
        {}
    ).get(
        "fallback_to_description",
        True
    )
)


max_chars = int(
    settings.get(
        "ai",
        {}
    ).get(
        "max_transcript_chars",
        50000
    )
)


telegram_limit = int(
    settings.get(
        "telegram",
        {}
    ).get(
        "max_message_chars",
        3900
    )
)


total_new = 0
total_sent = 0


if gemini_key and use_gemini:

    logging.info(
        "AI mode: Gemini available"
    )

else:

    logging.info(
        "AI mode: FREE RULES ONLY"
    )


for channel in channels:

    logging.info(
        "Checking: %s",
        channel.name
    )

    try:

        videos = get_latest_videos(
            youtube_key,
            channel,
            max_videos
        )

    except Exception:

        logging.exception(
            "YouTube API failed: %s",
            channel.name
        )

        continue

    logging.info(
        "Found %s videos: %s",
        len(videos),
        channel.name
    )

    for video in videos:

        video_id = str(
            video.get(
                "video_id",
                ""
            )
        ).strip()

        if not video_id:

            logging.warning(
                "影片缺少 video_id，跳過"
            )

            continue


        # =====================================================
        # 正常模式：檢查 state
        #
        # 測試模式：完全忽略 state
        # =====================================================

        if not test_mode:

            if is_processed(
                state,
                video_id
            ):

                logging.info(
                    "Skip processed: %s",
                    video_id
                )

                continue


        logging.info(
            "Processing video: %s",
            video.get(
                "title",
                video_id
            )
        )


        total_new += 1


        # =====================================================
        # Bootstrap
        #
        # 測試模式絕對不能進 bootstrap skip
        # =====================================================

        if (
            not test_mode
            and not state.get(
                "initialized",
                False
            )
            and bootstrap
        ):

            logging.info(
                "Bootstrap skip: %s",
                video_id
            )

            mark_processed(
                state,
                video_id,
                "bootstrap_skipped",
                None
            )

            save_state(
                state
            )

            continue


        # =====================================================
        # 取得字幕
        # =====================================================

        transcript, source = get_transcript(
            video_id,
            languages
        )


        # =====================================================
        # 沒有字幕 → 使用 Description
        # =====================================================

        if (
            not transcript
            and fallback_description
        ):

            transcript = str(
                video.get(
                    "description",
                    ""
                )
            )

            source = "description"

            logging.info(
                "使用影片 Description 作為分析文字: %s",
                video_id
            )


        if not transcript:

            logging.warning(
                "沒有字幕也沒有 Description: %s",
                video_id
            )

            if not test_mode:

                mark_processed(
                    state,
                    video_id,
                    "no_text",
                    None
                )

                save_state(
                    state
                )

            continue


        # =====================================================
        # 分析
        # =====================================================

        analysis = None

        analysis_source = "rules"


        if (
            gemini_key
            and use_gemini
        ):

            try:

                analysis = analyze_gemini(
                    api_key=gemini_key,
                    model=gemini_model,
                    video=video,
                    text=transcript,
                    max_chars=max_chars,
                )

                analysis_source = "gemini"

                logging.info(
                    "Gemini analysis success: %s",
                    video_id
                )

            except Exception as exc:

                logging.warning(
                    "Gemini failed, fallback rules: %s",
                    exc
                )


        # =====================================================
        # Gemini 失敗 → Rules
        # =====================================================

        if (
            analysis is None
            and fallback_rules
        ):

            analysis = analyze_rules(
                title=video.get(
                    "title",
                    ""
                ),
                description=video.get(
                    "description",
                    ""
                ),
                transcript=transcript,
                keywords=channel.keywords,
            )

            analysis_source = "rules"


        if analysis is None:

            logging.error(
                "No analysis available: %s",
                video_id
            )

            continue


        # =====================================================
        # 告訴 formatter 分析來源
        # =====================================================

        analysis[
            "analysis_source"
        ] = analysis_source


        # =====================================================
        # Score
        # =====================================================

        try:

            score = int(
                analysis.get(
                    "score",
                    0
                )
            )

        except (
            TypeError,
            ValueError,
        ):

            score = 0


        score = max(
            0,
            min(
                100,
                score
            )
        )


        logging.info(
            "%s | score=%s | source=%s | text=%s",
            video.get(
                "title",
                video_id
            ),
            score,
            analysis_source,
            source
        )


        # =====================================================
        # 分數過濾
        # =====================================================

        if score < channel.min_score:

            logging.info(
                "Filtered: %s | score=%s < min=%s",
                video_id,
                score,
                channel.min_score
            )

            if not test_mode:

                mark_processed(
                    state,
                    video_id,
                    "filtered",
                    score
                )

                save_state(
                    state
                )

            continue


        # =====================================================
        # Telegram 格式
        # =====================================================

        message = format_message(
            video,
            analysis
        )


        # =====================================================
        # Telegram
        # =====================================================

        try:

            send_message(
                telegram_token,
                telegram_chat_id,
                message,
                telegram_limit
            )

        except Exception:

            logging.exception(
                "Telegram failed: %s",
                video_id
            )

            continue


                total_sent += 1


        # =====================================================
        # 正常模式才寫入 state
        #
        # TEST MODE 不寫入
        # =====================================================

        if not test_mode:

            mark_processed(
                state,
                video_id,
                f"sent_{analysis_source}",
                score
            )

            save_state(
                state
            )

        else:

            logging.info(
                "TEST MODE: 不修改 state: %s",
                video_id
            )


    if not test_mode:

        state["initialized"] = True

        save_state(
            state
        )

    else:

        logging.warning(
            "TEST MODE: state.json 未修改"
        )


    logging.info(
        "Finished: new=%s sent=%s",
        total_new,
        total_sent
    )


    return 0


if __name__ == "__main__":
    sys.exit(
        main()
    )
