from __future__ import annotations
import json, re
try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None
    types = None

def _json(text):
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", (text or "").strip(), flags=re.I)
    try: return json.loads(text)
    except Exception:
        m = re.search(r"\{.*\}", text, re.S)
        if not m: raise RuntimeError("Gemini 回傳不是有效 JSON")
        return json.loads(m.group(0))

def analyze_gemini(api_key, model, video, text, max_chars=50000, channel_name="", **_):
    if not api_key: raise RuntimeError("GEMINI_API_KEY 未設定")
    if genai is None: raise RuntimeError("請安裝 google-genai")
    client = genai.Client(api_key=api_key)
    prompt = f"""你是台股 YouTube 影片重點整理器。
只列出影片中「明確被強調、討論或重點分析」的股票，最多5檔。
每檔必須有中文名稱；能確認代號才填4碼。不要把日期、時間、網址誤認股票。
不要只因 hashtag 出現就列入。不要自行預測股價，不要補充影片沒有說的資訊。
development 只寫影片提到的後續發展、營收、訂單、需求、產品、產能、產業趨勢或公司展望。
view 只寫影片對該股的主要觀點。
沒有明確個股時 stocks 必須為空陣列。
只回傳 JSON：
{{"score":50,"summary":"一句話摘要","stocks":[{{"code":"2330","name":"台積電","development":"後續發展","view":"影片觀點"}}]}}

頻道：{channel_name}
標題：{video.get("title","")}
Description：
{video.get("description","")}
字幕/文字：
{(text or "")[:max_chars]}"""
    response = client.models.generate_content(
        model=model, contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.1, max_output_tokens=1800,
            response_mime_type="application/json"
        )
    )
    raw = getattr(response, "text", None)
    if not raw: raise RuntimeError("Gemini 沒有回傳文字")
    data = _json(raw)
    stocks = []
    seen = set()
    for s in data.get("stocks", []):
        if not isinstance(s, dict): continue
        name = str(s.get("name","")).strip()
        code = str(s.get("code","")).strip()
        if not name or (code,name) in seen: continue
        seen.add((code,name))
        stocks.append({"code":code,"name":name,
                       "development":str(s.get("development","")).strip()[:260],
                       "view":str(s.get("view","")).strip()[:220]})
    return {"score":max(0,min(100,int(data.get("score",50) or 50))),
            "channel_name":channel_name,"stocks":stocks[:5],
            "summary":str(data.get("summary","")).strip()[:300],"source":"gemini"}
