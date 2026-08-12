from __future__ import annotations

import logging

from youtube_transcript_api import (
    YouTubeTranscriptApi,
)


def _convert_transcript(
    fetched,
) -> str:

    if fetched is None:
        return ""

    parts = []

    # ---------------------------------------------------------
    # 新版 FetchedTranscript
    # ---------------------------------------------------------

    try:

        for item in fetched:

            text = getattr(
                item,
                "text",
                "",
            )

            if text:

                parts.append(
                    str(text).strip()
                )

    except Exception:

        # -----------------------------------------------------
        # 如果是 raw data / dict list
        # -----------------------------------------------------

        try:

            for item in fetched:

                if isinstance(
                    item,
                    dict,
                ):

                    text = item.get(
                        "text",
                        "",
                    )

                    if text:

                        parts.append(
                            str(text).strip()
                        )

        except Exception:
            pass

    return "\n".join(
        x
        for x in parts
        if x
    ).strip()


def _fetch_direct(
    video_id: str,
    languages: list[str],
) -> str:

    api = YouTubeTranscriptApi()

    fetched = api.fetch(
        video_id,
        languages=languages,
    )

    return _convert_transcript(
        fetched
    )


def _fetch_by_list(
    video_id: str,
    languages: list[str],
) -> str:

    api = YouTubeTranscriptApi()

    transcript_list = api.list(
        video_id
    )

    # ---------------------------------------------------------
    # 優先指定語言
    # ---------------------------------------------------------

    try:

        transcript = (
            transcript_list
            .find_transcript(
                languages
            )
        )

        fetched = transcript.fetch()

        return _convert_transcript(
            fetched
        )

    except Exception:
        pass

    # ---------------------------------------------------------
    # 如果指定語言不存在，
    # 嘗試第一個可用字幕
    # ---------------------------------------------------------

    try:

        for transcript in transcript_list:

            fetched = transcript.fetch()

            text = _convert_transcript(
                fetched
            )

            if text:

                return text

    except Exception:
        pass

    return ""


def get_transcript(
    video_id: str,
    languages: list[str] | None = None,
) -> tuple[str, str]:
    """
    取得 YouTube 字幕。

    回傳：

        transcript, source

    source:
        transcript
        ""
    """

    if not video_id:

        return "", ""

    if not languages:

        languages = [
            "zh-TW",
            "zh-Hant",
            "zh",
            "en",
        ]

    # ---------------------------------------------------------
    # 新版 API：fetch()
    # ---------------------------------------------------------

    try:

        text = _fetch_direct(
            video_id,
            languages,
        )

        if text:

            logging.info(
                "字幕取得成功 %s",
                video_id,
            )

            return (
                text,
                "transcript",
            )

    except Exception as exc:

        logging.warning(
            "字幕直接取得失敗 %s: %s",
            video_id,
            exc,
        )

    # ---------------------------------------------------------
    # 新版 API：list()
    # ---------------------------------------------------------

    try:

        text = _fetch_by_list(
            video_id,
            languages,
        )

        if text:

            logging.info(
                "字幕列表取得成功 %s",
                video_id,
            )

            return (
                text,
                "transcript",
            )

    except Exception as exc:

        logging.warning(
            "字幕列表取得失敗 %s: %s",
            video_id,
            exc,
        )

    # ---------------------------------------------------------
    # GitHub Actions / Cloud IP 被 YouTube 擋
    #
    # 不再嘗試 cookies。
    # 直接讓 main.py fallback description。
    # ---------------------------------------------------------

    logging.warning(
        "字幕無法取得 %s，"
        "將由主程式嘗試使用影片 Description。",
        video_id,
    )

    return "", ""
