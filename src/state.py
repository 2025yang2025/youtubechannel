from __future__ import annotations

import json

from .config import ROOT


STATE_PATH = (
    ROOT
    / "data"
    / "state.json"
)


def load_state() -> dict:

    STATE_PATH.parent.mkdir(
        parents=True,
        exist_ok=True
    )


    if not STATE_PATH.exists():

        return {

            "initialized":
                False,

            "processed_videos":
                {},
        }


    try:

        return json.loads(

            STATE_PATH.read_text(
                encoding="utf-8"
            )
        )

    except Exception:

        return {

            "initialized":
                False,

            "processed_videos":
                {},
        }


def save_state(
    state: dict
) -> None:

    STATE_PATH.parent.mkdir(

        parents=True,

        exist_ok=True
    )


    tmp = (
        STATE_PATH
        .with_suffix(
            ".tmp"
        )
    )


    tmp.write_text(

        json.dumps(

            state,

            ensure_ascii=False,

            indent=2,
        ),

        encoding="utf-8"
    )


    tmp.replace(
        STATE_PATH
    )


def is_processed(

    state: dict,

    video_id: str,

) -> bool:

    return (

        video_id

        in state.get(
            "processed_videos",
            {}
        )
    )


def mark_processed(

    state: dict,

    video_id: str,

    status: str,

    score: int | None,

) -> None:

    state.setdefault(

        "processed_videos",
        {}
    )[video_id] = {

        "status":
            status,

        "score":
            score,
    }
