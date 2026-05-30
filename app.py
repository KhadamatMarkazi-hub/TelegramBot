import telebot
from flask import Flask, request
from pymongo import MongoClient
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
import random
import string
import os
import re

# ---------------- 1. تنظیمات اولیه ----------------
app = Flask(__name__)

# اتصال به MongoDB (برای تست محلی یا اگر متغیر ست نشده باشد)
# در Render، این مقدار از Environment Variables خوانده می‌شود
MONGO_URI = os.getenv("MONGO_URI") or "mongodb+srv://mazizimarkazi1990:Mr%40003806206@telegrombot.vzxtank.mongodb.net/?retryWrites=true&w=majority&appName=TelegromBot"
client = MongoClient(MONGO_URI)
db = client['telegram_db']
collection = db['users']

# توکن‌ها را از محیط بگیر
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN") or "YOUR_TELEGRAM_TOKEN"
BALE_TOKEN = os.getenv("BALE_TOKEN") or "YOUR_BALE_TOKEN"

# تشخیص پلتفرم فعال
# اگر توکن بله ست شده و توکن تلگرام پیش‌فرض است، پلتفرم بله است و برعکس
if os.getenv("TELEGRAM_TOKEN") and os.getenv("TELEGRAM_TOKEN") != "YOUR_TELEGRAM_TOKEN":
    PLATFORM = "Telegram"
    bot = telebot.TeleBot(TELEGRAM_TOKEN)
elif os.getenv("BALE_TOKEN") and os.getenv("BALE_TOKEN") != "YOUR_BALE_TOKEN":
    PLATFORM = "Bale"
    bot = telebot.TeleBot(BALE_TOKEN)
else:
    # حالت پیش‌فرض برای تست
    PLATFORM = "Telegram"
    bot = telebot.TeleBot(TELEGRAM_TOKEN)

# ---------------- 2. لینک‌های کانال‌ها ----------------
CHANNELS = {
    "Telegram": [
        {"name": "هاب مرکزی دانشجویان", "url": "https://t.me/+h9Zkeu7nolZlOTVk"},
        {"name": "بانک املاک سمنان", "url": "https://t.me/+FiF2mt4xlyUwNDQ8"},
        {"name": "بیلبورد سمنان", "url": "https://t.me/+txeYXj6nz0I3Y2Q0"},
        {"name": "تابلو اعلانات سمنان", "url": "https://t.me/+ZasLGaGAUzk4OGFk"}
    ],
    "Bale": [
        {"name": "هاب مرکزی دانشجویان", "url": "ble.ir/join/HbmyWPubkV"},
        {"name": "بانک املاک سمنان", "url": "ble.ir/join/HLQLNt2UAr"},
        {"name": "بیلبورد سمنان", "url": "ble.ir/join/B3BRAQXo6W"},
        {"name": "تابلو اعلانات سمنان", "url": "ble.ir/join/4VbzRsNvS8"}
    ]
}

# ---------------- 3. توابع کمکی ----------------

def generate_unique_code(suffix):
    # تولید 4 کاراکتر رندوم
    chars = string.ascii_uppercase + string.digits
    random_part = ''.join(random.choice(chars) for _ in range(4))
    return f"{random_part}{suffix}"

def is_valid_date(date_str):
    # چک کردن فرمت تاریخ (مثلاً 1403/01/01)
    pattern = r"^\d{4}/\d{2}/\d{2}$"
    return re.match(pattern, date_str) is not None

def get_user_status(username=None, phone=None):

    """چک می‌کند آیا کاربر قبلاً ثبت‌نام کرده است؟"""
    if username:
        user = collection.find_one({"username": username})
        if user: return user
    if phone:
        # نرمالیزه کردن شماره برای جستجو
        clean_phone = phone.replace("+", "").replace("09", "98").replace("0", "")
        # جستجو با شماره ذخیره شده
        user = collection.find_one({"phone": clean_phone})
        return user
    return None

# ---------------- 4. دستور Start ----------------

@bot.message_handler(commands=['start'])
def send_welcome(message):
    chat_id = message.chat.id
    username = message.from_user.username

    # چک کردن اینکه آیا قبلاً ثبت‌نام کرده؟
    user_exists = get_user_status(username=username)

    if user_exists:
        bot.send_message(
            chat_id,
            f"👋 {user_exists['full_name']} عزیز،\nشما قبلاً با کد: {user_exists['code']} ثبت‌نام کرده‌اید.\n\nبرای عضویت در کانال‌ها از دکمه‌های زیر استفاده کنید:"
        )
        send_channel_buttons(chat_id)
        return

    # پیام خوش‌آمدگویی اولیه
    welcome_msg = """دوست عزیز سلام ☺️
خیلی خوشحالیم که مجموعه خدمات مرکزی سمنان رو انتخاب کردید.
این ربات جهت مدیریت مخاطبین و انجام طرح های تخفیفی طراحی گردیده است. از اینکه وقت با ارزش خود را جهت تکمیل موارد خواسته شده صرف می کنید بسیار سپاسگزاریم 🙏🌹"""

    bot.send_message(chat_id, welcome_msg)

    # شروع مرحله ۱: گرفتن نام
    bot.send_message(chat_id, "لطفاً نام و نام خانوادگی خود را وارد کنید:")
    bot.register_next_step_handler(message, step_full_name)

# ---------------- 5. مراحل جمع‌آوری اطلاعات ----------------

def step_full_name(message):
    chat_id = message.chat.id
    full_name = message.text.strip()

    if len(full_name) < 3:
        bot.send_message(chat_id, "نام باید حداقل ۳ کاراکتر باشد. لطفاً دوباره وارد کنید:")
        bot.register_next_step_handler(message, step_full_name)
        return

    # ذخیره موقت نام در context (با استفاده از یک متغیر سراسری ساده برای دمو)
    # در پروژه واقعی بهتر است از Redis یا Session استفاده کنی، اما اینجا ساده می‌کنیم
    bot.send_message(chat_id, "لطفاً شماره همراه خود را وارد کنید (مثلاً: 09123456789):")
    bot.register_next_step_handler(message, lambda msg: step_phone(msg, full_name))

def step_phone(message, full_name):
    chat_id = message.chat.id
    phone = message.text.strip()

    # چک کردن تکراری بودن شماره با کاربری که قبلاً ثبت شده (با نام متفاوت)
    existing_user = get_user_status(phone=phone)
    if existing_user:
        bot.send_message(chat_id, f"⚠️ این شماره قبلاً با نام {existing_user['full_name']} و کد {existing_user['code']} ثبت شده است.\nلطفاً با پشتیبانی تماس بگیرید.")
        return

    bot.send_message(chat_id, "لطفاً تاریخ تولد خود را به صورت کامل وارد کنید (مثلاً: 1400/01/01):")
    bot.register_next_step_handler(message, lambda msg: step_birthdate(msg, full_name, phone))

def step_birthdate(message, full_name, phone):
    chat_id = message.chat.id
    birthdate = message.text.strip()

    if not is_valid_date(birthdate):
        bot.send_message(chat_id, "فرمت تاریخ اشتباه است. لطفاً به صورت YYYY/MM/DD وارد کنید (مثلاً 1403/01/01):")
        bot.register_next_step_handler(message, lambda msg: step_birthdate(msg, full_name, phone))

        return

    bot.send_message(chat_id, "شما جزو کدام گروه هستید؟ لطفاً یکی از گزینه‌های زیر را انتخاب کنید:")
    send_job_selection_buttons(chat_id, full_name, phone, birthdate)

# ---------------- 6. انتخاب شغل و ساخت کد ----------------

def send_job_selection_buttons(chat_id, full_name, phone, birthdate):
    keyboard = InlineKeyboardMarkup(row_width=1)

    # تعریف دکمه‌ها
    jobs = [
        ("🎓 دانشجو", "job_student"),
        ("🎒 دانش‌آموز", "job_scholar"),
        ("💼 شغل آزاد", "job_free"),
        ("🏛️ کارمند دولت", "job_gov"),
        ("📌 سایر", "job_other")
    ]

    for text, callback in jobs:
        btn = InlineKeyboardButton(text, callback_data=callback)
        keyboard.add(btn)

    bot.send_message(chat_id, "لطفاً گزینه‌ای را انتخاب کنید:", reply_markup=keyboard)
    # ذخیره اطلاعات موقت برای استفاده در callback
    # چون callback_data محدود است، اطلاعات را در یک dict سراسری نگه نمی‌داریم، 
    # بلکه در مرحله callback دوباره از دیتابیس چک می‌کنیم یا از پیام‌های بعدی استفاده می‌کنیم.
    # اما برای سادگی، اینجا فرض می‌کنیم کاربر دکمه را می‌زند و ما مستقیماً پردازش می‌کنیم.
    # نکته: برای ذخیره اطلاعات قبل از زدن دکمه، بهتر است از یک dict موقت استفاده کنیم.
    temp_data = {full_name: {"phone": phone, "birthdate": birthdate}}
    # در کد واقعی، باید این temp_data را به یک شیء Session وصل کنی.
    # اینجا برای دمو، فرض می‌کنیم callback مستقیماً پردازش می‌شود.
    # برای حل مشکل "عدم دسترسی به متغیرها در callback"، ما از یک dict سراسری ساده استفاده می‌کنیم:
    global USER_TEMP_DATA
    USER_TEMP_DATA[chat_id] = {"full_name": full_name, "phone": phone, "birthdate": birthdate}

def handle_job_selection(call):
    chat_id = call.message.chat.id
    callback_data = call.data

    # بازیابی اطلاعات ذخیره شده
    if chat_id not in USER_TEMP_DATA:
        bot.answer_callback_query(call.id, "منقضی شد، لطفاً از اول شروع کنید (/start)", show_alert=True)
        return

    user_info = USER_TEMP_DATA.pop(chat_id) # حذف بعد از استفاده
    full_name = user_info["full_name"]
    phone = user_info["phone"]
    birthdate = user_info["birthdate"]
    username = call.from_user.username
    platform = PLATFORM

    # تعیین پسوندها
    suffix_map = {
        "job_student": "UID",
        "job_scholar": "SID",
        "job_free": "FID",
        "job_gov": "GID",
        "job_other": "AID"
    }

    suffix = suffix_map.get(callback_data, "AID")
    unique_code = generate_unique_code(suffix)

    # ذخیره نهایی در دیتابیس
    data = {
        "user_id": call.from_user.id,
        "username": username,
        "full_name": full_name,
        "phone": phone,
        "birthdate": birthdate,
        "job_type": callback_data,
        "code": unique_code,
        "platform": platform
    }
    collection.insert_one(data)

    # پیام تبریک
    success_msg = f"""تبریک میگم به شما 👏🌹
به خانواده خدمات مرکزی خوش آمدید.
شناسه اختصاصی شما به شرح کد زیر است، این کد را یادداشت نمایید. 

🎟️ کد شما: {unique_code}"""

    bot.send_message(chat_id, success_msg)

    # نمایش دکمه‌های کانال
    send_channel_buttons(chat_id)

def send_channel_buttons(chat_id):
    keyboard = InlineKeyboardMarkup(row_width=1)

    # دریافت لینک‌ها بر اساس پلتفرم

    links = CHANNELS[PLATFORM]

    for channel in links:
        btn = InlineKeyboardButton(f"عضویت در {channel['name']}", url=channel['url'])
        keyboard.add(btn)

    intro_msg = """حالا تمایل دارید در کدام کانال مجموعه خدمات مرکزی عضو شوید؟ 
با انتخاب هر کدام می توانید عضو کانال شده و از امکانات و خدمات آن بهره مند شوید."""

    bot.send_message(chat_id, intro_msg, reply_markup=keyboard)

# ---------------- 7. تنظیم Callback Handler ----------------
# تعریف dict سراسری برای نگهداری موقت داده‌ها
USER_TEMP_DATA = {}

bot.register_callback_query_handler(handle_job_selection)

# ---------------- 8. اجرای Flask ----------------
@app.route("/")
def ping():
    return "Bot is Alive!"

if name == "__main__":
    # این بخش فقط برای تست محلی است
    # در Render، gunicorn اجرا می‌شود
    bot.infinity_polling()
    app.run(host="0.0.0.0", port=8080)
