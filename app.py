
import telebot
from flask import Flask
from pymongo import MongoClient
import random
import string
import os
import re

app = Flask(__name__)

# 1. اتصال به MongoDB
MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://mazizimarkazi1990:Mr%40003806206@telegrombot.vzxtank.mongodb.net/?retryWrites=true&w=majority&appName=TelegromBot")
client = MongoClient(MONGO_URI)
db = client['telegram_db']
collection = db['users']

# 2. مدیریت توکن‌ها و تشخیص پلتفرم
T_TOKEN = os.getenv("TELEGRAM_TOKEN")
B_TOKEN = os.getenv("BALE_TOKEN")

# اولویت با بله است اگر هر دو ست شده باشند، در غیر این صورت تلگرام
if B_TOKEN and ":" in B_TOKEN:
    PLATFORM_NAME = "Bale"
    BOT_TOKEN = B_TOKEN
elif T_TOKEN and ":" in T_TOKEN:
    PLATFORM_NAME = "Telegram"
    BOT_TOKEN = T_TOKEN
else:
    # برای جلوگیری از کرش در لحظه بیلد
    PLATFORM_NAME = "Telegram"
    BOT_TOKEN = "123456:FakeToken"

bot = telebot.TeleBot(BOT_TOKEN)

# 3. لینک‌های کانال‌ها
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

USER_TEMP_DATA = {}

def generate_unique_code(suffix):
    chars = string.ascii_uppercase + string.digits
    random_part = ''.join(random.choice(chars) for _ in range(4))
    return f"{random_part}{suffix}"

def is_valid_date(date_str):
    return re.match(r"^\d{4}/\d{2}/\d{2}$", date_str) is not None

# --- دستورات بات ---
@bot.message_handler(commands=['start'])
def send_welcome(message):
    chat_id = message.chat.id
    welcome = """دوست عزیز سلام ☺️
خیلی خوشحالیم که مجموعه خدمات مرکزی سمنان رو انتخاب کردید.
این ربات جهت مدیریت مخاطبین و انجام طرح های تخفیفی طراحی گردیده است. از اینکه وقت با ارزش خود را جهت تکمیل موارد خواسته شده صرف می کنید بسیار سپاسگزاریم 🙏🌹"""
    bot.send_message(chat_id, welcome)
    bot.send_message(chat_id, "لطفاً نام و نام خانوادگی خود را وارد کنید:")
    bot.register_next_step_handler(message, step_full_name)

def step_full_name(message):

    chat_id = message.chat.id
    USER_TEMP_DATA[chat_id] = {"full_name": message.text.strip()}
    bot.send_message(chat_id, "لطفاً شماره همراه خود را وارد کنید:")
    bot.register_next_step_handler(message, step_phone)

def step_phone(message):
    chat_id = message.chat.id
    USER_TEMP_DATA[chat_id]["phone"] = message.text.strip()
    bot.send_message(chat_id, "لطفاً تاریخ تولد خود را به صورت کامل وارد کنید (مثال: ۱۴۰۰/۰۱/۰۱):")
    bot.register_next_step_handler(message, step_birthdate)

def step_birthdate(message):
    chat_id = message.chat.id
    birthdate = message.text.strip()
    if not is_valid_date(birthdate):
        bot.send_message(chat_id, "فرمت اشتباه است (۱۴۰۰/۰۱/۰۱). دوباره وارد کنید:")
        bot.register_next_step_handler(message, step_birthdate)
        return
    USER_TEMP_DATA[chat_id]["birthdate"] = birthdate

    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton("🎓 دانشجو", callback_data="job_UID"))
    markup.add(telebot.types.InlineKeyboardButton("🎒 دانش‌آموز", callback_data="job_SID"))
    markup.add(telebot.types.InlineKeyboardButton("💼 شغل آزاد", callback_data="job_FID"))
    markup.add(telebot.types.InlineKeyboardButton("🏛️ کارمند دولت", callbackdata="job_GID"))
    markup.add(telebot.types.InlineKeyboardButton("📌 سایر", callback_data="job_AID"))
    bot.send_message(chat_id, "شما جزو کدام گروه هستید؟", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("job_"))
def handle_job(call):
    chat_id = call.message.chat.id
    suffix = call.data.split("_")[1]
    if chat_id not in USER_TEMP_DATA:
        bot.send_message(chat_id, "خطا! دوباره /start بزنید.")
        return

    info = USER_TEMP_DATA[chat_id]
    code = generate_unique_code(suffix)
    collection.insert_one({
        "user_id": chat_id, "full_name": info["full_name"], "phone": info["phone"],
        "birthdate": info["birthdate"], "code": code, "platform": PLATFORM_NAME
    })

    bot.send_message(chat_id, f"تبریک میگم به شما 👏🌹\nبه خانواده خدمات مرکزی خوش آمدید.\nشناسه اختصاصی شما: {code}")

    markup = telebot.types.InlineKeyboardMarkup()
    for item in CHANNELS[PLATFORM_NAME]:
        markup.add(telebot.types.InlineKeyboardButton(item["name"], url=item["url"]))
    bot.send_message(chat_id, "حالا تمایل دارید در کدام کانال عضو شوید؟", reply_markup=markup)

@app.route("/")
def index(): return "Bot is Running!"

if __name__ == "__main__":
    bot.infinity_polling()
