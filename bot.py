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

# Хранилище записей в памяти: booking_id -> {client_chat_id, booking}
pending_bookings = {}


def send_message(chat_id, text, reply_markup=None):
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML"
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup
    requests.post(f"{TELEGRAM_API}/sendMessage", json=payload)


def answer_callback(callback_id, text=""):
    requests.post(f"{TELEGRAM_API}/answerCallbackQuery", json={
        "callback_query_id": callback_id,
        "text": text
    })


def edit_message(chat_id, message_id, text):
    requests.post(f"{TELEGRAM_API}/editMessageText", json={
        "chat_id": chat_id,
        "message_id": message_id,
        "text": text,
        "parse_mode": "HTML"
    })


@app.route(f"/webhook/{TOKEN}", methods=["POST"])
def webhook():
    data = request.json
    if not data:
        return "ok"

    # Нажатие кнопки мастером
    callback = data.get("callback_query")
    if callback:
        callback_id = callback["id"]
        cb_data = callback.get("data", "")
        message_id = callback["message"]["message_id"]
        master_chat = callback["message"]["chat"]["id"]

        if cb_data.startswith("confirm:"):
            booking_id = cb_data.replace("confirm:", "")
            booking_info = pending_bookings.get(booking_id)

            if booking_info:
                client_chat_id = booking_info["client_chat_id"]
                booking = booking_info["booking"]

                # Сообщение клиентке
                send_message(client_chat_id,
                    "🌸 <b>Ваша запись подтверждена!</b>\n\n"
                    f"💅 {booking.get('service', '—')}\n"
                    f"📅 {booking.get('date', '—')} в {booking.get('time', '—')}\n\n"
                    "Ждём вас! Если планы изменятся — напишите заранее 🙏"
                )

                # Обновить сообщение мастеру — убрать кнопку
                edit_message(master_chat, message_id,
                    "✅ <b>Запись подтверждена!</b>\n\n"
                    f"💅 <b>Услуга:</b> {booking.get('service', '—')}\n"
                    f"📅 <b>Дата:</b> {booking.get('date', '—')} в {booking.get('time', '—')}\n"
                    f"👤 <b>Клиент:</b> {booking.get('client', '—')}\n"
                    f"📞 <b>Телефон:</b> {booking.get('phone', '—')}"
                    + (f"\n💬 <b>Пожелания:</b> {booking['comment']}" if booking.get('comment') else "")
                )

                answer_callback(callback_id, "✅ Клиентка уведомлена!")
                del pending_bookings[booking_id]
            else:
                answer_callback(callback_id, "Запись уже подтверждена")

        return "ok"

    # Обычное сообщение
    message = data.get("message", {})
    if not message:
        return "ok"

    chat_id = message.get("chat", {}).get("id")
    text = message.get("text", "")

    # /start
    if text == "/start":
        send_message(chat_id,
            "🌸 <b>Добро пожаловать в Nail Studio!</b>\n\n"
            "Нажмите кнопку <b>Меню</b> внизу слева, чтобы открыть каталог услуг и записаться."
        )
        return "ok"

    # Данные из Web App
    web_app_data = message.get("web_app_data", {}).get("data")
    if web_app_data:
        try:
            booking = json.loads(web_app_data)
            booking_id = str(message.get("message_id", "0"))

            # Сохраняем запись
            pending_bookings[booking_id] = {
                "client_chat_id": chat_id,
                "booking": booking
            }

            # Сообщение мастеру с кнопкой
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
                send_message(MASTER_CHAT_ID, master_text, reply_markup={
                    "inline_keyboard": [[
                        {"text": "✅ Подтвердить запись", "callback_data": f"confirm:{booking_id}"}
                    ]]
                })

            # Клиентке — запись принята
            send_message(chat_id,
                "⏳ <b>Запись принята!</b>\n\n"
                f"💅 {booking.get('service', '—')}\n"
                f"📅 {booking.get('date', '—')} в {booking.get('time', '—')}\n\n"
                "Мастер скоро подтвердит вашу запись. Ожидайте сообщения! 🌸"
            )

        except Exception as e:
            logging.error(f"Error: {e}")

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
