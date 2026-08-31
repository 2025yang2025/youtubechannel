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


def main() -> int:

    settings = load_settings()

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
            {},
        ).get(
            "default_gemini_model",
            "gemini-2.0-flash",
        ),
    )

    use_gemini = bool(
        settings.get(
            "free_mode",
            {},
        ).get(
            "use_gemini_if_available",
            True,
        )
    )

    fallback_rules = bool(
        settings.get(
            "free_mode",
            {},
        ).get(
            "fallback_to_rules",
            True,
        )
    )

    test_mode = bool(
        settings.get(
            "monitor",
            {},
        ).get(
            "test_mode",
            False,
        )
    )

    channels = []

    for channel in load_channels():

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
            "沒有有效 YouTube 頻道。"
        )

        return 1

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

    if gemini_key and use_gemini:

        logging.info(
            "AI mode: Gemini available"
        )

    else:

        logging.info(
            "AI mode: FREE RULES ONLY"
        )

    state = load_state()

    max_videos = int(
        settings.get(
            "monitor",
            {},
        ).get(
            "max_videos_per_channel",
            3,
        )
    )

    bootstrap = bool(
        settings.get(
            "monitor",
            {},
        ).get(
            "bootstrap",
            {},
        ).get(
            "mark_existing_as_processed",
            False,
        )
    )

    languages = (
        settings.get(
            "transcript",
            {},
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
            {},
        ).get(
            "fallback_to_description",
            True,
        )
    )

    max_chars = int(
        settings.get(
            "ai",
            {},
        ).get(
            "max_transcript_chars",
            50000,
        )
    )

    telegram_limit = int(
        settings.get(
            "telegram",
            {},
        ).get(
            "max_message_chars",
            3900,
        )
    )

    total_new = 0
    total_sent = 0

    for channel in channels:

        logging.info(
            "Checking: %s",
            channel.name,
        )

        try:

            videos = get_latest_videos(
                youtube_key,
                channel,
                max_videos,
            )

        except Exception as exc:

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

        for video in videos:

            video_id = video.get(
                "video_id",
                "",
            )

            if not video_id:
                continue

            logging.info(
                "Processing video: %s",
                video.get(
                    "title",
                    video_id,
                ),
            )

            if (
                not test_mode
                and is_processed(
                    state,
                    video_id,
                )
            ):

                continue

            total_new += 1

            if (
                not test_mode
                and not state.get(
                    "initialized",
                    False,
                )
                and bootstrap
            ):

                mark_processed(
                    state,
                    video_id,
                    "bootstrap_skipped",
                    None,
                )

                save_state(state)

                continue

            transcript = ""
            source = "none"

            try:

                transcript, source = (
                    get_transcript(
                        video_id,
                        languages,
                    )
                )

            except Exception:

                logging.exception(
                    "字幕取得錯誤: %s",
                    video_id,
                )

            if transcript:

                logging.info(
                    "字幕取得成功: %s",
                    video_id,
                )

            if (
                not transcript
                and fallback_description
            ):

                transcript = (
                    video.get(
                        "description",
                        "",
                    )
                    or ""
                )

                source = "description"

                logging.info(
                    "使用影片 Description 作為分析文字: %s",
                    video_id,
                )

            if not transcript:

                logging.warning(
                    "沒有可分析文字: %s",
                    video_id,
                )

                if not test_mode:

                    mark_processed(
                        state,
                        video_id,
                        "no_text",
                        None,
                    )

                    save_state(state)

                continue

            analysis = None
            analysis_source = "rules"

            # -------------------------
            # Gemini
            # -------------------------

            if (
                gemini_key
                and use_gemini
            ):

                try:

                    analysis = (
                        analyze_gemini(
                            api_key=gemini_key,
                            model=gemini_model,
                            video=video,
                            text=transcript,
                            max_chars=max_chars,
                        )
                    )

                    analysis_source = (
                        "gemini"
                    )

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

            # -------------------------
            # Rules fallback
            # -------------------------

            if (
                analysis is None
                and fallback_rules
            ):

                try:

                    analysis = (
                        analyze_rules(
                            title=video.get(
                                "title",
                                "",
                            ),
                            description=video.get(
                                "description",
                                "",
                            ),
                            transcript=transcript,
                            keywords=channel.keywords,
                        )
                    )

                    analysis_source = (
                        "rules"
                    )

                    logging.info(
                        "Rules analysis complete: %s",
                        video_id,
                    )

                except Exception:

                    logging.exception(
                        "Rules analysis failed: %s",
                        video_id,
                    )

            if analysis is None:

                logging.error(
                    "No analysis available: %s",
                    video_id,
                )

                continue

            # -------------------------
            # 分數
            # -------------------------

            try:

                score = int(
                    analysis.get(
                        "score",
                        0,
                    )
                )

            except Exception:

                score = 0

            score = max(
                0,
                min(
                    100,
                    score,
                ),
            )

            logging.info(
                "%s | score=%s | source=%s | text=%s",
                video.get(
                    "title",
                    "",
                ),
                score,
                analysis_source,
                source,
            )

            # -------------------------
            # 不再依 min_score 過濾
            # 測試階段先讓影片都能送出
            # -------------------------

            message = format_message(
                video=video,
                analysis=analysis,
            )

            if not message.strip():

                logging.warning(
                    "產生的 Telegram 訊息為空: %s",
                    video_id,
                )

                continue

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

            if not test_mode:

                mark_processed(
                    state,
                    video_id,
                    f"sent_{analysis_source}",
                    score,
                )

                save_state(state)

            total_sent += 1

    if not test_mode:

        state["initialized"] = True

        save_state(state)

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
