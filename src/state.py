import json
from pathlib import Path
FILE=Path(__file__).resolve().parents[1]/"state.json"
def load_state():
    if not FILE.exists(): return {"initialized":False,"processed":{}}
    try:
        d=json.loads(FILE.read_text(encoding="utf-8")); d.setdefault("processed",{}); return d
    except Exception: return {"initialized":False,"processed":{}}
def save_state(s): FILE.write_text(json.dumps(s,ensure_ascii=False,indent=2),encoding="utf-8")
def is_processed(s,v): return v in s.get("processed",{})
def mark_processed(s,v,status,score=None): s.setdefault("processed",{})[v]={"status":status,"score":score}
