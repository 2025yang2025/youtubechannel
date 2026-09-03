from __future__ import annotations

import logging
import sys

from .config import get_env, load_channels, load_settings, required_env
from .formatter import format_message
from .gemini import analyze_gemini
from .rules import analyze_rules
from .state import is_processed, load_state, mark_processed, save_state
from .telegram import send_message
from .transcript import get_transcript, usable_text
from .youtube import get_latest_videos

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")


def _models(settings: dict) -> list[str]:
    ai = settings.get("ai", {}) or {}
    preferred = get_env("GEMINI_MODEL", ai.get("default_gemini_model", "gemini-3.7-flash"))
    # Ignore old model names left in an existing GitHub Secret.
    retired = {"gemini-2.0-flash", "gemini-2.0-flash-lite", "gemini-2.5-flash", "gemini-2.5-flash-lite"}
    if preferred in retired:
        preferred = str(ai.get("default_gemini_model", "gemini-3.7-flash"))
    fallbacks = [str(x).strip() for x in ai.get("fallback_models", []) if str(x).strip()]
    result: list[str] = []
    for model in [preferred, *fallbacks]:
        if model and model not in result:
            result.append(model)
    return result or ["gemini-3.7-flash", "gemini-3.6-flash", "gemini-3.5-flash"]


def _try_gemini(api_key: str, models: list[str], video: dict, text: str, max_chars: int, max_tokens: int, use_youtube_url: bool):
    last_error: Exception | None = None
    for model in models:
        try:
            logging.info("Gemini model: %s", model)
            return analyze_gemini(api_key, model, video, text, max_chars, max_tokens, use_youtube_url), model
        except Exception as exc:
            last_error = exc
            logging.warning("Gemini model failed [%s]: %s", model, str(exc).splitlines()[0][:250])
    if last_error:
        raise last_error
    raise RuntimeError("沒有可用 Gemini model")


def main() -> int:
    settings = load_settings()
    youtube_key = required_env("YOUTUBE_API_KEY")
    telegram_token = required_env("TELEGRAM_BOT_TOKEN")
    telegram_chat_id = required_env("TELEGRAM_CHAT_ID")
    gemini_key = get_env("GEMINI_API_KEY")

    test_mode = bool(settings.get("monitor", {}).get("test_mode", True))
    max_videos = int(settings.get("monitor", {}).get("max_videos_per_channel", 1))
    languages = settings.get("transcript", {}).get("languages", ["zh-TW", "zh-Hant", "zh", "en"])
    minimum = int(settings.get("transcript", {}).get("minimum_useful_chars", 80))
    fallback_description = bool(settings.get("transcript", {}).get("fallback_to_description", True))
    use_gemini = bool(settings.get("free_mode", {}).get("use_gemini_if_available", True))
    use_rules = bool(settings.get("free_mode", {}).get("fallback_to_rules", True))
    gemini_youtube = bool(settings.get("gemini_youtube", {}).get("enabled", True))
    state = load_state()
    sent = 0

    channels = [c for c in load_channels() if c.enabled and (c.channel_id or c.handle)]
    if not channels:
        logging.error("沒有啟用有效 YouTube 頻道。")
        return 1

    if test_mode:
        logging.warning("TEST MODE：忽略 state.json，重新分析影片。")

    model_list = _models(settings)
    logging.info("AI mode: Gemini available | models=%s", ", ".join(model_list) if gemini_key and use_gemini else "rules only")

    for channel in channels:
        logging.info("Checking: %s", channel.name)
        try:
            videos = get_latest_videos(youtube_key, channel, max_videos)
        except Exception as exc:
            logging.exception("YouTube API failed: %s", exc)
            continue

        for video in videos:
            video_id = video.get("video_id", "")
            if not video_id or (not test_mode and is_processed(state, video_id)):
                continue

            logging.info("Processing video: %s", video.get("title", ""))
            text, source = get_transcript(video_id, languages)
            description = str(video.get("description", "") or "").strip()

            # YouTube Transcript API 在 GitHub Actions 常被 YouTube 擋住。
            # 不再因為沒有字幕而直接跳過；如果啟用 Gemini YouTube URL，
            # 讓 Gemini 直接讀取公開影片的音訊/畫面內容。
            if not usable_text(text, minimum) and fallback_description and usable_text(description, minimum):
                text, source = description, "description"
                logging.info("字幕不可用，改用影片 Description 作為文字輔助: %s", video_id)

            if not usable_text(text, minimum):
                logging.warning("字幕/Description 不足，將嘗試 Gemini 直接分析 YouTube 影片：%s", video_id)

            analysis = None
            analysis_source = ""

            if gemini_key and use_gemini:
                try:
                    analysis, used_model = _try_gemini(
                        gemini_key,
                        model_list,
                        video,
                        text,
                        int(settings.get("ai", {}).get("max_transcript_chars", 45000)),
                        int(settings.get("ai", {}).get("max_output_tokens", 900)),
                        gemini_youtube,
                    )
                    analysis_source = f"gemini:{used_model}"
                except Exception:
                    logging.exception("Gemini 分析失敗，嘗試回退規則模式: %s", video_id)

            if analysis is None and use_rules and usable_text(text, minimum):
                try:
                    analysis = analyze_rules(
                        video.get("title", ""),
                        video.get("description", ""),
                        text,
                        channel.keywords,
                    )
                    analysis_source = "rules"
                    logging.info("Rules analysis complete: %s", video_id)
                except Exception as exc:
                    logging.warning("Rules 也無法整理 %s：%s", video_id, exc)
                    if not test_mode:
                        mark_processed(state, video_id, "no_substantive_content")
                        save_state(state)
                    continue

            if not analysis:
                continue

            message = format_message(video, analysis)
            try:
                send_message(
                    telegram_token,
                    telegram_chat_id,
                    message,
                    int(settings.get("telegram", {}).get("max_message_chars", 3900)),
                )
                sent += 1
                logging.info("Telegram sent: %s | source=%s | text=%s", video_id, analysis_source, source)
            except Exception:
                logging.exception("Telegram failed: %s", video_id)
                continue

            if not test_mode:
                mark_processed(state, video_id, "sent")
                save_state(state)

    if not test_mode:
        state["initialized"] = True
        save_state(state)

    logging.info("Finished: sent=%s", sent)
    return 0


if __name__ == "__main__":
    sys.exit(main())
