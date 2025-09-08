import os
import json
import requests

BOT_TOKEN = os.getenv("BOT_TOKEN")
TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

def handler(request):
    if request.method == "POST":
        body = request.get_json()
        if "message" in body:
            chat_id = body["message"]["chat"]["id"]
            text = body["message"].get("text", "")
            # Simple reply
            requests.post(f"{TELEGRAM_API}/sendMessage", json={
                "chat_id": chat_id,
                "text": f"You said: {text}"
            })
        return {"statusCode": 200, "body": "ok"}
    else:
        return {"statusCode": 200, "body": "Webhook running"}
