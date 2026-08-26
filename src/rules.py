from __future__ import annotations
import re

STOCK_NAMES = {
    "1101":"台泥","1216":"統一","1301":"台塑","1303":"南亞","1402":"遠東新",
    "1476":"儒鴻","1590":"亞德客-KY","2002":"中鋼","2207":"和泰車",
    "2301":"光寶科","2303":"聯電","2308":"台達電","2317":"鴻海","2327":"國巨",
    "2330":"台積電","2344":"華邦電","2353":"宏碁","2357":"華碩","2376":"技嘉",
    "2382":"廣達","2395":"研華","2408":"南亞科","2454":"聯發科","2603":"長榮",
    "2609":"陽明","2615":"萬海","3008":"大立光","3034":"聯詠","3037":"欣興",
    "3044":"健鼎","3231":"緯創","3443":"創意","3661":"世芯-KY","3711":"日月光投控",
    "4938":"和碩","5269":"祥碩","5483":"中美晶","5871":"中租-KY","5880":"合庫金",
    "6176":"瑞儀","6213":"聯茂","6239":"力成","6274":"台燿","6669":"緯穎",
    "6770":"力積電","6805":"富世達","6922":"宸曜","8996":"高力",
}
ALIASES = {"台積":"台積電","聯發":"聯發科","廣達電腦":"廣達","緯創資通":"緯創"}
NAME_TO_CODE = {v:k for k,v in STOCK_NAMES.items()}

def _sentences(text):
    return [x.strip() for x in re.split(r"[。！？!?；;\n\r]+", text or "") if len(x.strip()) >= 8]

def extract_stocks(text):
    found = []
    for code in re.findall(r"(?<!\d)(\d{4})(?!\d)", text or ""):
        if code in STOCK_NAMES: found.append((code, STOCK_NAMES[code]))
    for name, code in NAME_TO_CODE.items():
        if name in (text or ""): found.append((code, name))
    for alias, name in ALIASES.items():
        if alias in (text or "") and name in NAME_TO_CODE:
            found.append((NAME_TO_CODE[name], name))
    out, seen = [], set()
    for code, name in found:
        if (code,name) not in seen:
            seen.add((code,name)); out.append({"code":code,"name":name})
    return out[:8]

def _future(sentences):
    words = ["後續","未來","展望","接下來","今年","明年","下半年","下一季","訂單","需求","成長","擴產","新產品","新產能","法說","營收","獲利","出貨","接單","趨勢"]
    ranked = [(sum(w in s for w in words), len(s), s) for s in sentences]
    ranked.sort(reverse=True)
    return ranked[0][2] if ranked and ranked[0][0] else ""

def analyze_rules(title, description, transcript, keywords, channel_name="", **_):
    text = f"{title}\n{description}\n{transcript}"
    stocks = extract_stocks(text)
    results = []
    for stock in stocks:
        sentences = [s for s in _sentences(text) if stock["name"] in s or stock["code"] in s]
        dev = _future(sentences) or "影片中未找到明確的後續發展描述。"
        results.append({"code":stock["code"],"name":stock["name"],"development":dev[:240],"view":sentences[0][:200] if sentences else ""})
    score = min(100, 20 + sum(4 for w in ["營收","獲利","EPS","展望","訂單","需求","成長","AI","半導體"] if w.lower() in text.lower()))
    return {"score":score,"channel_name":channel_name,"stocks":results[:5],"summary":"僅整理影片中可辨識的個股及後續描述。","source":"rules"}
