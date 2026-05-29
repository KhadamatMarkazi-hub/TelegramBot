import os
import random
import requests
from flask import Flask, request

app = Flask(__name__)

TOKEN = os.environ.get('TOKEN')
URL = f"https://api.telegram.org/bot{TOKEN}/"

CHANNEL_LINKS = [
    ("هاب مرکزی دانشجویان سمنان", "https://t.me/+h9Zkeu7nolZlOTVk"),
    ("بانک املاک سمنان", "https://t.me/+FiF2mt4xlyUwNDQ8"),
    ("بیلبورد سمنان", "https://t.me/+txeYXj6nz0I3Y2Q0"),
    ("تابلو اعلانات سمنان", "https://t.me/+ZasLGaGAUzk4OGFk")
]

CODE_PREFIXES = {
    "دانشجو": "UID",
    "دانش آموز": "SID",
    "شغل آزاد": "FID",
    "کارمند دولت": "GID",
    "سایر": "AID"
}

users_db = {}

def send_message(chat_id, text, reply_markup=None):
    payload = {'chat_id': chat_id, 'text': text}
    if reply_markup:
        payload['reply_markup'] = reply_markup
    requests.post(URL + "sendMessage", json=payload)

def get_group_keyboard():
    return {
        "keyboard": [
            ["دانشجو"],
            ["دانش آموز"],
            ["شغل آزاد"],
            ["کارمند دولت"],
            ["سایر"]
        ],
        "one_time_keyboard": True,
        "resize_keyboard": True
    }

def get_channel_keyboard():
    rows = []
    for title, link in CHANNEL_LINKS:
        rows.append([{"text": title, "url": link}])
    return {"inline_keyboard": rows}

def generate_unique_code(prefix):
    return f"{prefix}-{random.randint(10000, 99999)}"

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    if "message" in data:
        message = data["message"]
        chat_id = message["chat"]["id"]
        text = message.get("text")

        if chat_id not in users_db:
            users_db[chat_id] = {"step": 0, "name": "", "phone": "", "birthdate": "", "group": "", "unique_code": ""}

        user = users_db[chat_id]

        if text == "/start":
            welcome_msg = """دوست عزیز سلام ☺️
خیلی خوشحالیم که مجموعه خدمات مرکزی سمنان رو انتخاب کردید.
این ربات جهت مدیریت مخاطبین و انجام طرح های تخفیفی طراحی گردیده است. از اینکه وقت با ارزش خود را جهت تکمیل موارد خواسته شده صرف می کنید بسیار سپاسگزاریم 🙏🌹"""
            send_message(chat_id, welcome_msg)
            user["step"] = 1
            send_message(chat_id, "لطفاً نام و نام خانوادگی خود را وارد کنید:")

        else:
            current_step = user["step"]

            if current_step == 1:
                user["name"] = text
                user["step"] = 2
                send_message(chat_id, "لطفاً شماره همراه خود را وارد کنید:")

            elif current_step == 2:
                user["phone"] = text
                user["step"] = 3

                send_message(chat_id, "تاریخ تولد خود را به صورت کامل وارد کنید (مثلا ۱۴۰۰/۰۱/۰۱):")

            elif current_step == 3:
                user["birthdate"] = text
                user["step"] = 4
                send_message(chat_id, "شما جزو کدام گروه هستید؟", reply_markup=get_group_keyboard())

            elif current_step == 4:
                group_name = text
                prefix = CODE_PREFIXES.get(group_name, "AID")
                unique_code = generate_unique_code(prefix)

                user["group"] = group_name
                user["unique_code"] = unique_code
                user["step"] = 5

                congrats_msg = f"""تبریک میگم به شما 👏🌹
به خانواده خدمات مرکزی خوش آمدید.
شناسه اختصاصی شما به شرح کد زیر است، این کد را یادداشت نمایید: 
{unique_code}"""
                send_message(chat_id, congrats_msg)

                channel_msg = "تمایل دارید در کدام کانال مجموعه خدمات مرکزی عضو شوید؟"
                send_message(chat_id, channel_msg, reply_markup=get_channel_keyboard())

    return "ok", 200

# خط زیر بسیار مهم است: دو زیرخط قبل و بعد از name
__if name == "__main__":
    app.run(host='0.0.0.0', port=5000)
