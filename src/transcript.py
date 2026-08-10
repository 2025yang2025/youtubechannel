from __future__ import annotations

import logging
import re

from youtube_transcript_api import (
    YouTubeTranscriptApi
)


log = logging.getLogger(__name__)


def clean(text: str) -> str:

    text = re.sub(
        r"\s+",
        " ",
        text or "",
    )

    return text.strip()


def get_transcript(

    video_id: str,

    languages: list[str],

) -> tuple[str | None, str]:

    api = YouTubeTranscriptApi()


    # 新版 API
    try:

        fetched = api.fetch(

            video_id,

            languages=languages,
        )


        pieces = []


        for item in fetched:

            if isinstance(
                item,
                dict
            ):

                pieces.append(

                    str(
                        item.get(
                            "text",
                            ""
                        )
                    )
                )

            else:

                pieces.append(

                    str(
                        getattr(
                            item,
                            "text",
                            ""
                        )
                    )
                )


        text = clean(
            " ".join(
                pieces
            )
        )


        if text:

            return (
                text,
                "transcript"
            )


    except Exception as exc:

        log.warning(

            "字幕取得失敗 %s: %s",

            video_id,

            exc,
        )


    # 舊版相容模式
    try:

        transcript_list = (

            YouTubeTranscriptApi
            .list_transcripts(
                video_id
            )
        )


        transcript = None


        for lang in languages:

            try:

                transcript = (

                    transcript_list
                    .find_transcript(
                        [lang]
                    )
                )

                break

            except Exception:

                continue


        if transcript is None:

            try:

                transcript = (

                    transcript_list
                    .find_generated_transcript(
                        languages
                    )
                )

            except Exception:

                pass


        if transcript:

            items = transcript.fetch()

            pieces = []


            for item in items:

                if isinstance(
                    item,
                    dict
                ):

                    pieces.append(

                        str(
                            item.get(
                                "text",
                                ""
                            )
                        )
                    )

                else:

                    pieces.append(

                        str(
                            getattr(
                                item,
                                "text",
                                ""
                            )
                        )
                    )


            text = clean(
                " ".join(
                    pieces
                )
            )


            if text:

                return (
                    text,
                    "transcript"
                )


    except Exception as exc:

        log.warning(

            "字幕相容模式失敗 %s: %s",

            video_id,

            exc,
        )


    return (
        None,
        "none"
    )
