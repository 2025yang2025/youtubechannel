from __future__ import annotations
import os
from dataclasses import dataclass, field
from pathlib import Path
import yaml
from dotenv import load_dotenv
ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")
@dataclass
class Channel:
    name: str
    channel_id: str = ""
    handle: str = ""
    enabled: bool = True
    keywords: list[str] = field(default_factory=list)
    min_score: int = 0
def load_settings() -> dict:
    with open(ROOT / "config" / "settings.yaml", encoding="utf-8") as f: return yaml.safe_load(f) or {}
def load_channels() -> list[Channel]:
    with open(ROOT / "config" / "channels.yaml", encoding="utf-8") as f: raw = yaml.safe_load(f) or {}
    return [Channel(name=str(x.get("name","")).strip(), channel_id=str(x.get("channel_id","")).strip(), handle=str(x.get("handle","")).strip(), enabled=bool(x.get("enabled",True)), keywords=[str(k) for k in x.get("keywords",[])], min_score=int(x.get("min_score",0))) for x in raw.get("channels",[])]
def get_env(name: str, default: str = "") -> str:
    value = os.getenv(name, "").strip()
    return value if value else default
def required_env(name: str) -> str:
    v=get_env(name)
    if not v: raise RuntimeError(f"Missing required environment variable: {name}")
    return v
