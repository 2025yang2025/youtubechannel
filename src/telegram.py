from __future__ import annotations

import requests


def split_message(

    text: str,

    limit: int = 3900,

) -> list[str]:

    if len(text) <= limit:

        return [
            text
        ]


    parts = []

    current = ""


    for line in text.split(
        "\n"
    ):

        candidate = (

            line

            if not current

            else

            current
            + "\n"
            + line
        )


        if len(
            candidate
        ) <= limit:

            current = candidate

        else:

            if current:

                parts.append(
                    current
                )


            while len(
                line
            ) > limit:

                parts.append(
                    line[:limit]
                )

                line = line[
                    limit:
                ]


            current = line


    if current:

        parts.append(
            current
        )


    return parts


def send_message(

    bot_token: str,

    chat_id: str,

    text: str,

    limit: int = 3900,

) -> None:

    url = (

        "https://api.telegram.org/"

        f"bot{bot_token}"

        "/sendMessage"
    )


    for part in split_message(

        text,

        limit,

    ):

        response = requests.post(

            url,

            data={

                "chat_id":
                    chat_id,

                "text":
                    part,

                "disable_web_page_preview":
                    False,
            },

            timeout=30,
        )


        response.raise_for_status()
