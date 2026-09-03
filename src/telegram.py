import requests
def send_message(token,chat_id,message,max_chars=3900):
    url=f"https://api.telegram.org/bot{token}/sendMessage"
    for i in range(0,len(message),max_chars):
        r=requests.post(url,json={"chat_id":chat_id,"text":message[i:i+max_chars],"disable_web_page_preview":True},timeout=30); r.raise_for_status()
