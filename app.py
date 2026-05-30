import telebot
from flask import Flask
from pymongo import MongoClient
import random
import string
import os
import re
import threading

app = Flask(__name__)

# 1. اتصال به MongoDB
MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://mazizimarkazi1990:Mr%40003806206@telegrombot.vzxtank.mongodb.net/?retryWrites=true&w=majority&appName=TelegromBot")
client = MongoClient(MONGO_URI)
db = client['telegram_db']
collection = db['users']

# 2. مدیریت توکن‌ها
T_TOKEN = os.getenv("TELEGRAM_TOKEN")
B_TOKEN = os.getenv("BALE_TOKEN")

# تشخیص پلتفرم
if B_TOKEN and ":" in B_TOKEN:
    PLATFORM_NAME = "Bale"
    BOT_TOKEN = B_TOKEN
elif T_TOKEN and ":" in T_TOKEN:
    PLATFORM_NAME = "Telegram"
    BOT_TOKEN = T_TOKEN
else:
    PLATFORM_NAME = "Telegram"
    BOT_TOKEN = "12345:Fake"

bot = telebot.TeleBot(BOT_TOKEN)
USER_TEMP_DATA = {}

# --- لینک کانال‌ها ---
CHANNELS = {
    "Telegram": [
        {"name": "هاب مرکزی دانشجویان", "url": "https://t.me/+h9Zkeu7nolZlOTVk"},
        {"name": "بانک املاک سمنان", "url": "https://t.me/+FiF2mt4xlyUwNDQ8"},
        {"name": "بیلبورد سمنان", "url": "https://t.me/+txeYXj6nz0I3Y2Q0"},
        {"name": "تابلو اعلانات سمنان", "url": "https://t.me/+ZasLGaGAUzk4OGFk"}
    ],
    "Bale": [
        {"name": "هاب مرکزی دانشجویان", "url": "https://ble.ir/join/HbmyWPubkV"},
        {"name": "بانک املاک سمنان", "url": "https://ble.ir/join/HLQLNt2UAr"},
        {"name": "بیلبورد سمنان", "url": "https://ble.ir/join/B3BRAQXo6W"},
        {"name": "تابلو اعلانات سمنان", "url": "https://ble.ir/join/4VbzRsNvS8"}
    ]
}

# --- توابع کمکی ---
def generate_unique_code(suffix):
    chars = string.ascii_uppercase + string.digits
    return ''.join(random.choice(chars) for _ in range(4)) + suffix

# --- هندلرهای ربات ---
@bot.message_handler(commands=['start'])
def start(message):
    chat_id = message.chat.id
    welcome = "دوست عزیز سلام ☺️\nخیلی خوشحالیم که مجموعه خدمات مرکزی سمنان رو انتخاب کردید.\nاین ربات جهت مدیریت مخاطبین طراحی شده است."
    bot.send_message(chat_id, welcome)
    bot.send_message(chat_id, "لطفاً نام و نام خانوادگی خود را وارد کنید:")
    bot.register_next_step_handler(message, step_name)

def step_name(message):
    chat_id = message.chat.id
    USER_TEMP_DATA[chat_id] = {"name": message.text}
    bot.send_message(chat_id, "لطفاً شماره همراه خود را وارد کنید:")
    bot.register_next_step_handler(message, step_phone)

def step_phone(message):
    chat_id = message.chat.id
    USER_TEMP_DATA[chat_id]["phone"] = message.text
    bot.send_message(chat_id, "لطفاً تاریخ تولد (۱۴۰۰/۰۱/۰۱) را وارد کنید:")
    bot.register_next_step_handler(message, step_date)

def step_date(message):
    chat_id = message.chat.id

    USER_TEMP_DATA[chat_id]["date"] = message.text
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton("🎓 دانشجو", callback_data="job_UID"))
    markup.add(telebot.types.InlineKeyboardButton("🎒 دانش‌آموز", callback_data="job_SID"))
    markup.add(telebot.types.InlineKeyboardButton("💼 شغل آزاد", callback_data="job_FID"))
    markup.add(telebot.types.InlineKeyboardButton("🏛️ کارمند دولت", callbackdata="job_GID"))
    markup.add(telebot.types.InlineKeyboardButton("📌 سایر", callback_data="job_AID"))
    bot.send_message(chat_id, "گروه شغلی شما؟", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("job_"))
def handle_job(call):
    chat_id = call.message.chat.id
    suffix = call.data.split("_")[1]
    info = USER_TEMP_DATA.get(chat_id, {})
    code = generate_unique_code(suffix)

    collection.insert_one({
        "user_id": chat_id, "name": info.get("name"), "phone": info.get("phone"),
        "date": info.get("date"), "code": code, "platform": PLATFORM_NAME
    })

    bot.send_message(chat_id, f"تبریک! کد شما: {code}")

    markup = telebot.types.InlineKeyboardMarkup()
    for item in CHANNELS[PLATFORM_NAME]:
        markup.add(telebot.types.InlineKeyboardButton(item["name"], url=item["url"]))
    bot.send_message(chat_id, "عضویت در کانال‌ها:", reply_markup=markup)

# --- اجرای همزمان Flask و Bot ---
@app.route("/")
def home():
    return "Bot is Active!"

def run_bot():
    bot.infinity_polling(non_stop=True)

if _name == "__main__":
    # اجرای ربات در یک Thread جداگانه
    threading.Thread(target=run_bot).start()
    # اجرای Flask روی پورتی که رندر می‌خواهد
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
