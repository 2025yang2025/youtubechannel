from __future__ import annotations
import logging, sys
from .config import get_env, load_channels, load_settings, required_env
from .formatter import format_message, split_message
from .gemini import analyze_gemini
from .rules import analyze_rules
from .state import is_processed, load_state, mark_processed, save_state
from .telegram import send_message
from .transcript import get_transcript
from .youtube import get_latest_videos

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")

def main() -> int:
    settings = load_settings()
    youtube_key = required_env("YOUTUBE_API_KEY")
    telegram_token = required_env("TELEGRAM_BOT_TOKEN")
    telegram_chat_id = required_env("TELEGRAM_CHAT_ID")
    gemini_key = get_env("GEMINI_API_KEY")
    gemini_model = get_env("GEMINI_MODEL", settings.get("ai", {}).get("default_gemini_model", "gemini-3.7-flash"))
    use_gemini = bool(settings.get("free_mode", {}).get("use_gemini_if_available", True))
    fallback_rules = bool(settings.get("free_mode", {}).get("fallback_to_rules", True))
    test_mode = bool(settings.get("monitor", {}).get("test_mode", False))

    if test_mode:
        logging.warning("=" * 40)
        logging.warning("TEST MODE 已啟用")
        logging.warning("將忽略 state.json 的已處理紀錄")
        logging.warning("=" * 40)

    channels = [c for c in load_channels() if c.enabled]
    if not channels:
        logging.error("沒有啟用有效 YouTube 頻道。")
        return 1

    state = load_state()
    max_videos = int(settings.get("monitor", {}).get("max_videos_per_channel", 1))
    bootstrap = bool(settings.get("monitor", {}).get("bootstrap", {}).get("mark_existing_as_processed", False))
    languages = settings.get("transcript", {}).get("languages", ["zh-TW", "zh-Hant", "zh", "en"])
    fallback_description = bool(settings.get("transcript", {}).get("fallback_to_description", True))
    max_chars = int(settings.get("ai", {}).get("max_transcript_chars", 50000))
    telegram_limit = int(settings.get("telegram", {}).get("max_message_chars", 3900))

    logging.info("AI mode: Gemini available" if gemini_key and use_gemini else "AI mode: FREE RULES ONLY")
    total_new = total_sent = 0

    for channel in channels:
        logging.info("Checking: %s", channel.name)
        try:
            videos = get_latest_videos(youtube_key, channel, max_videos)
            logging.info("Found %s videos: %s", len(videos), channel.name)
        except Exception as exc:
            logging.error("YouTube API failed: %s | %s", channel.name, exc)
            continue

        for video in videos:
            video_id = video["video_id"]
            if not test_mode and is_processed(state, video_id):
                continue
            total_new += 1
            logging.info("Processing video: %s", video["title"])

            if not test_mode and not state.get("initialized", False) and bootstrap:
                mark_processed(state, video_id, "bootstrap_skipped", None)
                save_state(state)
                continue

            try:
                transcript, source = get_transcript(video_id, languages)
            except Exception as exc:
                logging.warning("字幕取得失敗 %s: %s", video_id, exc)
                transcript, source = "", "description"

            if not transcript and fallback_description:
                transcript = video.get("description", "")
                source = "description"
                logging.info("使用影片 Description 作為分析文字: %s", video_id)

            if not transcript:
                logging.warning("沒有可分析文字，跳過: %s", video_id)
                continue

            analysis = None
            analysis_source = "rules"

            if gemini_key and use_gemini:
                try:
                    analysis = analyze_gemini(
                        api_key=gemini_key, model=gemini_model, video=video,
                        text=transcript, max_chars=max_chars, channel_name=channel.name
                    )
                    analysis_source = "gemini"
                except Exception:
                    logging.exception("Gemini 分析失敗，回退 Rules: %s", video_id)

            if analysis is None and fallback_rules:
                try:
                    analysis = analyze_rules(
                        title=video.get("title", ""),
                        description=video.get("description", ""),
                        transcript=transcript,
                        keywords=channel.keywords,
                        channel_name=channel.name,
                    )
                except Exception:
                    logging.exception("Rules analysis failed: %s", video_id)

            if analysis is None:
                continue

            stocks = analysis.get("stocks", [])
            if not stocks:
                logging.info("沒有明確強調個股，不發送 Telegram: %s", video_id)
                if not test_mode:
                    mark_processed(state, video_id, f"no_stock_{analysis_source}", analysis.get("score", 0))
                    save_state(state)
                continue

            message = format_message(video=video, analysis=analysis, channel_name=channel.name)
            try:
                for chunk in split_message(message, telegram_limit):
                    send_message(telegram_token, telegram_chat_id, chunk, telegram_limit)
                total_sent += 1
            except Exception:
                logging.exception("Telegram failed: %s", video_id)
                continue

            if not test_mode:
                mark_processed(state, video_id, f"sent_{analysis_source}", analysis.get("score", 0))
                save_state(state)

    state["initialized"] = True
    save_state(state)
    logging.info("Finished: new=%s sent=%s", total_new, total_sent)
    return 0

if __name__ == "__main__":
    sys.exit(main())
