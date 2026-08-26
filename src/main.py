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


# ============================================================
# Logging
# ============================================================

logging.basicConfig(

    level=logging.INFO,

    format=(
        "%(asctime)s | "
        "%(levelname)s | "
        "%(message)s"
    ),
)


# ============================================================
# Main
# ============================================================

def main() -> int:

    # ========================================================
    # Settings
    # ========================================================

    settings = load_settings()

    # ========================================================
    # Environment
    # ========================================================

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
            "gemini-2.0-flash"
        )
    )

    # ========================================================
    # AI / Free Mode
    # ========================================================

    use_gemini = bool(

        settings.get(
            "free_mode",
            {}
        ).get(
            "use_gemini_if_available",
            True
        )
    )

    fallback_rules = bool(

        settings.get(
            "free_mode",
            {}
        ).get(
            "fallback_to_rules",
            True
        )
    )

    # ========================================================
    # TEST MODE
    #
    # GitHub Actions:
    #
    # TEST_MODE=true
    #
    # 或 settings.yaml
    #
    # ========================================================

    test_mode_env = get_env(
        "TEST_MODE",
        ""
    ).lower()

    test_mode_config = bool(

        settings.get(
            "monitor",
            {}
        ).get(
            "test_mode",
            False
        )
    )

    test_mode = (

        test_mode_env
        in [
            "1",
            "true",
            "yes",
            "on",
        ]

    ) or test_mode_config

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

    # ========================================================
    # Channels
    # ========================================================

    all_channels = load_channels()

    channels = []

    for channel in all_channels:

        if not channel.enabled:
            continue

        if (
            not channel.channel_id
            and not channel.handle
        ):

            logging.warning(
                "頻道 %s 沒有 channel_id 或 handle，跳過。",
                channel.name,
            )

            continue

        channels.append(
            channel
        )

    if not channels:

        logging.error(
            "沒有啟用有效 YouTube 頻道。"
        )

        return 1

    # ========================================================
    # State
    # ========================================================

    state = load_state()

    # TEST MODE 不使用原本的 processed
    if test_mode:

        test_state = {
            "initialized": True,
            "processed": {},
        }

    else:

        test_state = state

    # ========================================================
    # Monitor settings
    # ========================================================

    monitor_settings = settings.get(
        "monitor",
        {}
    )

    max_videos = int(
        monitor_settings.get(
            "max_videos_per_channel",
            1
        )
    )

    bootstrap = bool(

        monitor_settings.get(
            "bootstrap",
            {}
        ).get(
            "mark_existing_as_processed",
            False
        )
    )

    # ========================================================
    # Transcript settings
    # ========================================================

    transcript_settings = settings.get(
        "transcript",
        {}
    )

    languages = transcript_settings.get(

        "languages",

        [
            "zh-TW",
            "zh-Hant",
            "zh",
            "en",
        ]
    )

    fallback_description = bool(

        transcript_settings.get(
            "fallback_to_description",
            True
        )
    )

    # ========================================================
    # AI settings
    # ========================================================

    ai_settings = settings.get(
        "ai",
        {}
    )

    max_chars = int(
        ai_settings.get(
            "max_transcript_chars",
            50000
        )
    )

    # ========================================================
    # Telegram settings
    # ========================================================

    telegram_settings = settings.get(
        "telegram",
        {}
    )

    telegram_limit = int(
        telegram_settings.get(
            "max_message_chars",
            3900
        )
    )

    # ========================================================
    # AI Mode
    # ========================================================

    if gemini_key and use_gemini:

        logging.info(
            "AI mode: Gemini available"
        )

    else:

        logging.info(
            "AI mode: FREE RULES ONLY"
        )

    # ========================================================
    # Counters
    # ========================================================

    total_new = 0

    total_sent = 0

    # ========================================================
    # Channel Loop
    # ========================================================

    for channel in channels:

        logging.info(
            "Checking: %s",
            channel.name
        )

        try:

            videos = get_latest_videos(

                youtube_key,

                channel,

                max_videos,
            )

        except Exception:

            logging.exception(
                "YouTube API failed: %s",
                channel.name,
            )

            continue

        logging.info(
            "Found %s videos: %s",
            len(videos),
            channel.name,
        )

        # ====================================================
        # Video Loop
        # ====================================================

        for video in videos:

            video_id = video.get(
                "video_id",
                ""
            )

            if not video_id:

                continue

            # ------------------------------------------------
            # 補上 channel_name
            #
            # formatter 不再需要 channel=
            # ------------------------------------------------

            video["channel_name"] = (
                channel.name
            )

            # ------------------------------------------------
            # URL
            # ------------------------------------------------

            if not video.get("url"):

                video["url"] = (
                    f"https://www.youtube.com/watch?v={video_id}"
                )

            # ------------------------------------------------
            # TEST MODE
            # ------------------------------------------------

            if not test_mode:

                if is_processed(
                    state,
                    video_id
                ):

                    continue

            total_new += 1

            logging.info(
                "Processing video: %s",
                video.get(
                    "title",
                    video_id
                )
            )

            # ------------------------------------------------
            # Bootstrap
            # ------------------------------------------------

            if (
                not test_mode
                and not state.get(
                    "initialized",
                    False
                )
                and bootstrap
            ):

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

            # =================================================
            # Transcript
            # =================================================

            transcript = ""

            source = "none"

            try:

                transcript, source = get_transcript(

                    video_id,

                    languages,
                )

            except Exception:

                logging.exception(
                    "Transcript failed: %s",
                    video_id,
                )

            # ------------------------------------------------
            # Description fallback
            # ------------------------------------------------

            if (
                not transcript
                and fallback_description
            ):

                transcript = video.get(
                    "description",
                    ""
                )

                source = "description"

                logging.info(
                    "使用影片 Description "
                    "作為分析文字: %s",
                    video_id,
                )

            # ------------------------------------------------
            # Completely no text
            # ------------------------------------------------

            if not transcript:

                logging.warning(
                    "影片沒有可分析文字: %s",
                    video_id,
                )

                if not test_mode:

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

            # ------------------------------------------------
            # Gemini
            # ------------------------------------------------

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
                        "Gemini analysis complete: %s",
                        video_id,
                    )

                except Exception:

                    logging.exception(
                        "Gemini 分析失敗，"
                        "嘗試回退規則模式: %s",
                        video_id,
                    )

            # ------------------------------------------------
            # Rules fallback
            # ------------------------------------------------

            if (
                analysis is None
                and fallback_rules
            ):

                try:

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

                    logging.info(
                        "Rules analysis complete: %s",
                        video_id,
                    )

                except Exception:

                    logging.exception(
                        "Rules analysis failed: %s",
                        video_id,
                    )

                    continue

            # ------------------------------------------------
            # No analysis
            # ------------------------------------------------

            if analysis is None:

                logging.error(
                    "No analysis available: %s",
                    video_id,
                )

                continue

            # =================================================
            # Score
            # =================================================

            try:

                score = int(
                    analysis.get(
                        "score",
                        0
                    )
                )

            except Exception:

                score = 0

            score = max(
                0,
                min(
                    100,
                    score
                )
            )

            logging.info(

                "%s | score=%s | "
                "source=%s | text=%s",

                video.get(
                    "title",
                    video_id
                ),

                score,

                analysis_source,

                source,
            )

            # =================================================
            # Filter
            # =================================================

            if score < channel.min_score:

                logging.info(
                    "影片低於最低分數，"
                    "不傳送 Telegram: %s",
                    video_id,
                )

                if not test_mode:

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
            # Formatter
            # =================================================

            try:

                message = format_message(

                    video,

                    analysis,
                )

            except Exception:

                logging.exception(
                    "Formatter failed: %s",
                    video_id,
                )

                continue

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
                    video_id,
                )

                continue

            # =================================================
            # Mark processed
            # =================================================

            if not test_mode:

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

            logging.info(
                "Telegram sent: %s",
                video_id
            )

    # ========================================================
    # State initialized
    # ========================================================

    if not test_mode:

        state["initialized"] = True

        save_state(
            state
        )

    # ========================================================
    # Finished
    # ========================================================

    logging.info(
        "Finished: new=%s sent=%s",
        total_new,
        total_sent,
    )

    return 0


# ============================================================
# Entry
# ============================================================

if __name__ == "__main__":

    sys.exit(
        main()
    )
