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
    format_message
)


from .gemini import (
    analyze_gemini
)


from .rules import (
    analyze_rules
)


from .state import (

    is_processed,

    load_state,

    mark_processed,

    save_state,
)


from .telegram import (
    send_message
)


from .transcript import (
    get_transcript
)


from .youtube import (
    get_latest_videos
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

    settings = (
        load_settings()
    )


    youtube_key = (
        required_env(
            "YOUTUBE_API_KEY"
        )
    )


    telegram_token = (
        required_env(
            "TELEGRAM_BOT_TOKEN"
        )
    )


    telegram_chat_id = (
        required_env(
            "TELEGRAM_CHAT_ID"
        )
    )


    gemini_key = (
        get_env(
            "GEMINI_API_KEY"
        )
    )


    gemini_model = (

        get_env(

            "GEMINI_MODEL",

            settings.get(
                "ai",
                {}
            ).get(
                "default_gemini_model",
                "gemini-2.0-flash"
            )
        )
    )


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


    channels = [

        channel

        for channel
        in load_channels()

        if (

            channel.enabled

            and not channel.channel_id.startswith(
                "UC_REPLACE"
            )
        )
    ]


    if not channels:

        logging.error(

            "沒有啟用有效 YouTube 頻道。"
        )

        return 1


    state = (
        load_state()
    )


    max_videos = int(

        settings.get(
            "monitor",
            {}
        ).get(
            "max_videos_per_channel",
            3
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

            videos = (

                get_latest_videos(

                    youtube_key,

                    channel,

                    max_videos
                )
            )

        except Exception:

            logging.exception(

                "YouTube API failed"
            )

            continue


        for video in videos:

            video_id = (
                video["video_id"]
            )


            if is_processed(

                state,

                video_id
            ):

                continue


            total_new += 1


            if (

                not state.get(
                    "initialized",
                    False
                )

                and bootstrap
            ):

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


            transcript, source = (

                get_transcript(

                    video_id,

                    languages
                )
            )


            if (

                not transcript

                and fallback_description
            ):

                transcript = (
                    video["description"]
                )

                source = (
                    "description"
                )


            if not transcript:

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


            analysis = None

            analysis_source = (
                "rules"
            )


            if (

                gemini_key

                and use_gemini
            ):

                try:

                    analysis = (

                        analyze_gemini(

                            api_key=
                                gemini_key,

                            model=
                                gemini_model,

                            video=
                                video,

                            text=
                                transcript,

                            max_chars=
                                max_chars,
                        )
                    )


                    analysis_source = (
                        "gemini"
                    )


                except Exception as exc:

                    logging.warning(

                        "Gemini failed, "
                        "fallback rules: %s",

                        exc
                    )


            if (

                analysis is None

                and fallback_rules
            ):

                analysis = (

                    analyze_rules(

                        title=
                            video["title"],

                        description=
                            video["description"],

                        transcript=
                            transcript,

                        keywords=
                            channel.keywords,
                    )
                )


            if analysis is None:

                logging.error(

                    "No analysis available."
                )

                continue


            score = max(

                0,

                min(

                    100,

                    int(
                        analysis.get(
                            "score",
                            0
                        )
                    )
                )
            )


            logging.info(

                "%s | score=%s | "
                "source=%s | text=%s",

                video["title"],

                score,

                analysis_source,

                source
            )


            if score < channel.min_score:

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


            message = (

                format_message(

                    video,

                    analysis
                )
            )


            try:

                send_message(

                    telegram_token,

                    telegram_chat_id,

                    message,

                    telegram_limit
                )

            except Exception:

                logging.exception(

                    "Telegram failed"
                )

                continue


            mark_processed(

                state,

                video_id,

                f"sent_{analysis_source}",

                score
            )


            save_state(
                state
            )


            total_sent += 1


    state["initialized"] = True

    save_state(
        state
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
