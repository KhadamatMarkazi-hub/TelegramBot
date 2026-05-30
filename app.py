
import telebot
from flask import Flask
from pymongo import MongoClient
import random
import string
import os
import re

# ---------------- 1. تنظیمات اولیه ----------------
app = Flask(__name__)

# اتصال به MongoDB
MONGO_URI = os.getenv("MONGO_URI") or "mongodb+srv://mazizimarkazi1990:Mr%40003806206@telegrombot.vzxtank.mongodb.net/?retryWrites=true&w=majority&appName=TelegromBot"
client = MongoClient(MONGO_URI)
db = client['telegram_db']
collection = db['users']

# توکن‌ها
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
BALE_TOKEN = os.getenv("BALE_TOKEN")

# تشخیص پلتفرم و انتخاب بات
if BALE_TOKEN:
    PLATFORM = "Bale"
    bot = telebot.TeleBot(BALE_TOKEN)
else:
    PLATFORM = "Telegram"
    bot = telebot.TeleBot(TELEGRAM_TOKEN if TELEGRAM_TOKEN else "YOUR_TELEGRAM_TOKEN")

# دیکشنری برای ذخیره موقت داده‌ها (در حافظه RAM)
USER_TEMP_DATA = {}

# ---------------- 2. لینک‌های کانال‌ها ----------------
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

# ---------------- 3. توابع کمکی ----------------

def generate_unique_code(suffix):
    chars = string.ascii_uppercase + string.digits
    random_part = ''.join(random.choice(chars) for _ in range(4))
    return f"{random_part}{suffix}"

def is_valid_date(date_str):
    pattern = r"^\d{4}/\d{2}/\d{2}$"
    return re.match(pattern, date_str) is not None

# ---------------- 4. شروع فرآیند ----------------

@bot.message_handler(commands=['start'])
def send_welcome(message):
    chat_id = message.chat.id

    # پیام خوش‌آمدگویی
    welcome_msg = """دوست عزیز سلام ☺️
خیلی خوشحالیم که مجموعه خدمات مرکزی سمنان رو انتخاب کردید.
این ربات جهت مدیریت مخاطبین و انجام طرح های تخفیفی طراحی گردیده است. از اینکه وقت با ارزش خود را جهت تکمیل موارد خواسته شده صرف می کنید بسیار سپاسگزاریم 🙏🌹"""

    bot.send_message(chat_id, welcome_msg)
    bot.send_message(chat_id, "لطفاً نام و نام خانوادگی خود را وارد کنید:")
    bot.register_next_step_handler(message, step_full_name)

def step_full_name(message):
    chat_id = message.chat.id
    full_name = message.text.strip()

    USER_TEMP_DATA[chat_id] = {"full_name": full_name}

    bot.send_message(chat_id, "لطفاً شماره همراه خود را وارد کنید:")
    bot.register_next_step_handler(message, step_phone)

def step_phone(message):
    chat_id = message.chat.id
    phone = message.text.strip()
    USER_TEMP_DATA[chat_id]["phone"] = phone

    bot.send_message(chat_id, "لطفاً تاریخ تولد خود را به صورت کامل وارد کنید. مثلا ۱۴۰۰/۰۱/۰۱:")
    bot.register_next_step_handler(message, step_birthdate)

def step_birthdate(message):
    chat_id = message.chat.id
    birthdate = message.text.strip()

    if not is_valid_date(birthdate):
        bot.send_message(chat_id, "فرمت اشتباه است. لطفاً دوباره وارد کنید (مثال: ۱۴۰۰/۰۱/۰۱):")
        bot.register_next_step_handler(message, step_birthdate)
        return

    USER_TEMP_DATA[chat_id]["birthdate"] = birthdate

    # ساخت کیبورد برای انتخاب شغل
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton("🎓 دانشجو", callback_data="job_UID"))
    markup.add(telebot.types.InlineKeyboardButton("🎒 دانش‌آموز", callback_data="job_SID"))
    markup.add(telebot.types.InlineKeyboardButton("💼 شغل آزاد", callback_data="job_FID"))
    markup.add(telebot.types.InlineKeyboardButton("🏛️ کارمند دولت", callbackdata="job_GID"))
    markup.add(telebot.types.InlineKeyboardButton("📌 سایر", callback_data="job_AID"))

    bot.send_message(chat_id, "شما جزو کدام گروه هستید؟", reply_markup=markup)

# ---------------- 5. ثبت نهایی ----------------

@bot.callback_query_handler(func=lambda call: call.data.startswith("job_"))
def handle_job_selection(call):
    chat_id = call.message.chat.id
    suffix = call.data.split("_")[1] # استخراج UID, SID و ...

    if chat_id not in USER_TEMP_DATA:
        bot.send_message(chat_id, "خطایی رخ داد. لطفاً دوباره /start بزنید.")
        return

    user_info = USER_TEMP_DATA[chat_id]
    unique_code = generate_unique_code(suffix)

    # ذخیره در دیتابیس
    data = {
        "user_id": chat_id,
        "full_name": user_info["full_name"],
        "phone": user_info["phone"],
        "birthdate": user_info["birthdate"],
        "code": unique_code,
        "platform": PLATFORM
    }
    collection.insert_one(data)

    # پیام تبریک
    success_text = f"""تبریک میگم به شما 👏🌹
به خانواده خدمات مرکزی خوش آمدید.
شناسه اختصاصی شما به شرح کد زیر است، این کد را یادداشت نمایید.

🎟️ کد شما: {uniquecode}"""
    bot.send_message(chat_id, success_text)

    # نمایش کانال‌ها
    send_channel_links(chat_id)

def send_channel_links(chat_id):
    markup = telebot.types.InlineKeyboardMarkup()
    links = CHANNELS[PLATFORM]

    for item in links:
        markup.add(telebot.types.InlineKeyboardButton(item["name"], url=item["url"]))

    msg = "حالا تمایل دارید در کدام کانال مجموعه خدمات مرکزی عضو شوید؟ با انتخاب هر کدام می توانید عضو کانال شده و از امکانات و خدمات آن بهره مند شوید"
    bot.send_message(chat_id, msg, reply_markup=markup)

# ---------------- 6. اجرای سرور ----------------
@app.route("/")
def index():
    return "Bot is Running!"

if __name__ == "__main__":
    bot.infinity_polling()
