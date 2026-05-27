import os
import json
import logging
from flask import Flask, request
import requests

logging.basicConfig(level=logging.INFO)
app = Flask(__name__)

TOKEN = os.environ.get("BOT_TOKEN", "")
MASTER_CHAT_ID = os.environ.get("MASTER_CHAT_ID", "")
TELEGRAM_API = f"https://api.telegram.org/bot{TOKEN}"


def send_message(chat_id, text):
    requests.post(f"{TELEGRAM_API}/sendMessage", json={
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML"
    })


@app.route(f"/webhook/{TOKEN}", methods=["POST"])
def webhook():
    data = request.json
    if not data:
        return "ok"

    message = data.get("message", {})
    chat_id = message.get("chat", {}).get("id")
    text = message.get("text", "")

    # Команда /start — клиентка открывает бота
    if text == "/start":
        send_message(chat_id,
            "🌸 <b>Добро пожаловать в Nail Studio!</b>\n\n"
            "Нажмите кнопку <b>Меню</b> внизу слева, чтобы открыть каталог услуг и записаться."
        )
        return "ok"

    # Данные из Web App (tg.sendData)
    web_app_data = message.get("web_app_data", {}).get("data")
    if web_app_data:
        try:
            booking = json.loads(web_app_data)

            # Сообщение мастеру
            master_text = (
                "🌸 <b>Новая запись!</b>\n\n"
                f"💅 <b>Услуга:</b> {booking.get('service', '—')}\n"
                f"📅 <b>Дата:</b> {booking.get('date', '—')} в {booking.get('time', '—')}\n"
                f"👤 <b>Клиент:</b> {booking.get('client', '—')}\n"
                f"📞 <b>Телефон:</b> {booking.get('phone', '—')}"
            )
            if booking.get("comment"):
                master_text += f"\n💬 <b>Пожелания:</b> {booking['comment']}"

            if MASTER_CHAT_ID:
                send_message(MASTER_CHAT_ID, master_text)

            # Подтверждение клиентке
            send_message(chat_id,
                "✅ <b>Запись принята!</b>\n\n"
                f"💅 {booking.get('service', '—')}\n"
                f"📅 {booking.get('date', '—')} в {booking.get('time', '—')}\n\n"
                "Я свяжусь с вами для подтверждения. До встречи! 🌸"
            )

        except Exception as e:
            logging.error(f"Error parsing booking: {e}")

    return "ok"


@app.route("/", methods=["GET"])
def index():
    return "Nail Studio Bot is running 🌸"


@app.route("/set_webhook", methods=["GET"])
def set_webhook():
    url = os.environ.get("WEBHOOK_URL", "")
    if not url:
        return "WEBHOOK_URL not set", 400
    resp = requests.post(f"{TELEGRAM_API}/setWebhook", json={
        "url": f"{url}/webhook/{TOKEN}"
    })
    return resp.json()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
