from __future__ import annotations

import requests


BASE = "https://www.googleapis.com/youtube/v3"


def api_get(
    path: str,
    params: dict,
) -> dict:

    response = requests.get(

        f"{BASE}/{path}",

        params=params,

        timeout=30,
    )

    response.raise_for_status()

    return response.json()


def get_upload_playlist(
    api_key: str,
    channel_id: str,
) -> str:

    data = api_get(

        "channels",

        {
            "part": "contentDetails",

            "id": channel_id,

            "key": api_key,
        },
    )

    items = data.get(
        "items",
        []
    )

    if not items:

        raise ValueError(
            f"找不到頻道: {channel_id}"
        )

    return (
        items[0]
        ["contentDetails"]
        ["relatedPlaylists"]
        ["uploads"]
    )


def get_latest_videos(

    api_key: str,

    channel,

    limit: int,

) -> list[dict]:

    playlist_id = get_upload_playlist(

        api_key,

        channel.channel_id,
    )


    playlist = api_get(

        "playlistItems",

        {
            "part":
                "snippet,contentDetails",

            "playlistId":
                playlist_id,

            "maxResults":
                min(
                    max(
                        limit,
                        1
                    ),
                    50
                ),

            "key":
                api_key,
        },
    )


    ids = [

        item
        .get(
            "contentDetails",
            {}
        )
        .get(
            "videoId"
        )

        for item
        in playlist.get(
            "items",
            []
        )

    ]


    ids = [
        x
        for x in ids
        if x
    ]


    if not ids:

        return []


    videos = api_get(

        "videos",

        {
            "part":
                "snippet,contentDetails,statistics",

            "id":
                ",".join(ids),

            "key":
                api_key,
        },
    )


    result = []


    for video in videos.get(
        "items",
        []
    ):

        snippet = video.get(
            "snippet",
            {}
        )


        result.append(

            {

                "video_id":
                    video["id"],

                "channel_id":
                    snippet.get(
                        "channelId",
                        channel.channel_id
                    ),

                "channel_name":
                    channel.name,

                "title":
                    snippet.get(
                        "title",
                        ""
                    ),

                "description":
                    snippet.get(
                        "description",
                        ""
                    ),

                "published_at":
                    snippet.get(
                        "publishedAt",
                        ""
                    ),

                "url":
                    (
                        "https://www.youtube.com/"
                        "watch?v="
                        f"{video['id']}"
                    ),

                "view_count":
                    video.get(
                        "statistics",
                        {}
                    ).get(
                        "viewCount",
                        ""
                    ),

                "duration":
                    video.get(
                        "contentDetails",
                        {}
                    ).get(
                        "duration",
                        ""
                    ),
            }
        )


    result.sort(

        key=lambda x:
            x.get(
                "published_at",
                ""
            ),

        reverse=True,
    )


    return result
