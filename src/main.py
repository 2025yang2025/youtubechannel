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
            3,
        )
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
            True,
        )
    )

    # =========================================================
    # Transcript settings
    # =========================================================

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
            ],
        )
    )

    fallback_description = bool(
        settings.get(
            "transcript",
            {}
        ).get(
            "fallback_to_description",
            True,
        )
    )

    # =========================================================
    # AI settings
    # =========================================================

    max_chars = int(
        settings.get(
            "ai",
            {}
        ).get(
            "max_transcript_chars",
            50000,
        )
    )

    # =========================================================
    # Telegram settings
    # =========================================================

    telegram_limit = int(
        settings.get(
            "telegram",
            {}
        ).get(
            "max_message_chars",
            3900,
        )
    )

    # =========================================================
    # Counters
    # =========================================================

    total_new = 0
    total_sent = 0

    # =========================================================
    # AI mode
    # =========================================================

    if gemini_key and use_gemini:

        logging.info(
            "AI mode: Gemini available"
        )

    else:

        logging.info(
            "AI mode: FREE RULES ONLY"
        )

    # =========================================================
    # Process channels
    # =========================================================

    for channel in channels:

        channel_name = _get_channel_value(
            channel,
            "name",
            "Unnamed Channel",
        )

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

        keywords = _get_channel_value(
            channel,
            "keywords",
            [],
        )

        min_score = int(
            _get_channel_value(
                channel,
                "min_score",
                50,
            )
        )

        logging.info(
            "Checking: %s",
            channel_name,
        )

        # -----------------------------------------------------
        # 顯示目前使用哪一種方式
        # -----------------------------------------------------

        if handle:

            logging.info(
                "YouTube source: %s",
                handle,
            )

        elif channel_id:

            logging.info(
                "YouTube source: %s",
                channel_id,
            )

        # -----------------------------------------------------
        # YouTube API
        # -----------------------------------------------------

        try:

            videos = get_latest_videos(
                youtube_key,
                channel,
                max_videos,
            )

        except Exception:

            logging.exception(
                "YouTube API failed: %s",
                channel_name,
            )

            continue

        logging.info(
            "Found %s videos: %s",
            len(videos),
            channel_name,
        )

        # =====================================================
        # Process videos
        # =====================================================

        for video in videos:

            video_id = video.get(
                "video_id"
            )

            if not video_id:

                logging.warning(
                    "影片沒有 video_id，跳過。"
                )

                continue

            # -------------------------------------------------
            # 已處理
            # -------------------------------------------------

            if is_processed(
                state,
                video_id,
            ):

                continue

            total_new += 1

            # -------------------------------------------------
            # Bootstrap
            #
            # 第一次執行不推播舊影片
            # -------------------------------------------------

            if (
                not state.get(
                    "initialized",
                    False,
                )
                and bootstrap
            ):

                logging.info(
                    "Bootstrap skip: %s",
                    video.get(
                        "title",
                        video_id,
                    ),
                )

                mark_processed(
                    state,
                    video_id,
                    "bootstrap_skipped",
                    None,
                )

                save_state(
                    state
                )

                continue

            # -------------------------------------------------
            # Transcript
            # -------------------------------------------------

            transcript, source = get_transcript(
                video_id,
                languages,
            )

            # -------------------------------------------------
            # Description fallback
            # -------------------------------------------------

            if (
                not transcript
                and fallback_description
            ):

                transcript = video.get(
                    "description",
                    "",
                )

                source = "description"

            # -------------------------------------------------
            # 沒有文字
            # -------------------------------------------------

            if not transcript:

                logging.warning(
                    "No transcript/description: %s",
                    video.get(
                        "title",
                        video_id,
                    ),
                )

                mark_processed(
                    state,
                    video_id,
                    "no_text",
                    None,
                )

                save_state(
                    state
                )

                continue

            # =================================================
            # Analysis
            # =================================================

            analysis = None

            analysis_source = "rules"

            # -------------------------------------------------
            # Gemini
            # -------------------------------------------------

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

                except Exception as exc:

                    logging.warning(
                        "Gemini failed, "
                        "fallback rules: %s",
                        exc,
                    )

            # -------------------------------------------------
            # FREE RULES
            # -------------------------------------------------

            if (
                analysis is None
                and fallback_rules
            ):

                analysis = analyze_rules(
                    title=video.get(
                        "title",
                        "",
                    ),
                    description=video.get(
                        "description",
                        "",
                    ),
                    transcript=transcript,
                    keywords=keywords,
                )

                analysis_source = "rules"

            # -------------------------------------------------
            # Analysis failed
            # -------------------------------------------------

            if analysis is None:

                logging.error(
                    "No analysis available: %s",
                    video.get(
                        "title",
                        video_id,
                    ),
                )

                continue

            # =================================================
            # Score
            # =================================================

            try:

                score = int(
                    analysis.get(
                        "score",
                        0,
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
                    score,
                ),
            )

            logging.info(
                "%s | score=%s | "
                "source=%s | text=%s",
                video.get(
                    "title",
                    video_id,
                ),
                score,
                analysis_source,
                source,
            )

            # =================================================
            # Score filter
            # =================================================

            if score < min_score:

                mark_processed(
                    state,
                    video_id,
                    "filtered",
                    score,
                )

                save_state(
                    state
                )

                continue

            # =================================================
            # Format Telegram message
            # =================================================

            message = format_message(
                video,
                analysis,
            )

            # =================================================
            # Telegram
            # =================================================

            try:

                send_message(
                    telegram_token,
                    telegram_chat_id,
                    message,
                    telegram_limit,
                )

            except Exception:

                logging.exception(
                    "Telegram failed: %s",
                    video.get(
                        "title",
                        video_id,
                    ),
                )

                # 不標記為已成功發送
                # 下一次可以重新嘗試

                continue

            # =================================================
            # Mark successfully sent
            # =================================================

            mark_processed(
                state,
                video_id,
                f"sent_{analysis_source}",
                score,
            )

            save_state(
                state
            )

            total_sent += 1

    # =========================================================
    # Initialization completed
    # =========================================================

    state["initialized"] = True

    save_state(
        state
    )

    # =========================================================
    # Summary
    # =========================================================

    logging.info(
        "Finished: new=%s sent=%s",
        total_new,
        total_sent,
    )

    return 0


if __name__ == "__main__":
    sys.exit(
        main()
    )
