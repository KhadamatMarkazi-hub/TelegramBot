```python
import os
import re
import random
import string
import threading
from datetime import datetime

import telebot
from flask import Flask
from pymongo import MongoClient
from pymongo.errors import PyMongoError

# -------------------------
# Flask
# -------------------------
app = Flask(__name__)

# -------------------------
# MongoDB
# -------------------------
MONGO_URI = os.getenv("MONGO_URI")

if not MONGO_URI:
    raise ValueError("MONGO_URI is not configured.")

client = MongoClient(
    MONGO_URI,
    serverSelectionTimeoutMS=5000
)

db = client["telegram_db"]
collection = db["users"]

# ایندکس‌ها
try:
    collection.create_index("user_id", unique=True)
    collection.create_index("code", unique=True)
except Exception:
    pass

# -------------------------
# Tokens
# -------------------------
T_TOKEN = os.getenv("TELEGRAM_TOKEN")
B_TOKEN = os.getenv("BALE_TOKEN")

if B_TOKEN and ":" in B_TOKEN:
    PLATFORM_NAME = "Bale"
    BOT_TOKEN = B_TOKEN
elif T_TOKEN and ":" in T_TOKEN:
    PLATFORM_NAME = "Telegram"
    BOT_TOKEN = T_TOKEN
else:
    raise ValueError("No valid bot token found.")

bot = telebot.TeleBot(BOT_TOKEN)

# -------------------------
# Channels
# -------------------------
CHANNELS = {
    "Telegram": [
        {
            "name": "هاب مرکزی دانشجویان",
            "url": "https://t.me/+h9Zkeu7nolZlOTVk"
        },
        {
            "name": "بانک املاک سمنان",
            "url": "https://t.me/+FiF2mt4xlyUwNDQ8"
        },
        {
            "name": "بیلبورد سمنان",
            "url": "https://t.me/+txeYXj6nz0I3Y2Q0"
        },
        {
            "name": "تابلو اعلانات سمنان",
            "url": "https://t.me/+ZasLGaGAUzk4OGFk"
        }
    ],
    "Bale": [
        {
            "name": "هاب مرکزی دانشجویان",
            "url": "https://ble.ir/join/HbmyWPubkV"
        },
        {
            "name": "بانک املاک سمنان",
            "url": "https://ble.ir/join/HLQLNt2UAr"
        },
        {
            "name": "بیلبورد سمنان",
            "url": "https://ble.ir/join/B3BRAQXo6W"
        },
        {
            "name": "تابلو اعلانات سمنان",
            "url": "https://ble.ir/join/4VbzRsNvS8"
        }
    ]
}

PHONE_REGEX = r"^09\d{9}$"
DATE_REGEX = r"^\d{4}/\d{2}/\d{2}$"

# -------------------------
# Helper Functions
# -------------------------
def save_user(chat_id, data):
    data["updated_at"] = datetime.utcnow()

    collection.update_one(
        {"user_id": chat_id},
        {"$set": data},
        upsert=True
    )


def get_user(chat_id):
    return collection.find_one({"user_id": chat_id})


def generate_unique_code(suffix):
    chars = string.ascii_uppercase + string.digits

    while True:
        code = "".join(
            random.choice(chars)
            for _ in range(4)
        ) + suffix

        if not collection.find_one({"code": code}):
            return code


# -------------------------
# Start
# -------------------------
@bot.message_handler(commands=["start"])
def start(message):

    chat_id = message.chat.id

    user = get_user(chat_id)

    if user and user.get("step") == "completed":

        bot.send_message(
            chat_id,
            f"شما قبلاً ثبت‌نام کرده‌اید.\n\nکد شما:\n{user['code']}"
        )

        return

    save_user(
        chat_id,
        {
            "user_id": chat_id,
            "platform": PLATFORM_NAME,
            "step": "name"
        }
    )

    bot.send_message(
        chat_id,
        "دوست عزیز سلام ☺️\n"
        "لطفاً نام و نام خانوادگی خود را وارد کنید:"
    )


# -------------------------
# Step Processor
# -------------------------
@bot.message_handler(func=lambda m: True)
def process_steps(message):

    chat_id = message.chat.id

    user = get_user(chat_id)

    if not user:
        return

    step = user.get("step")

    # نام
    if step == "name":

        name = message.text.strip()

        if len(name) < 3:

            bot.send_message(
                chat_id,
                "نام معتبر وارد کنید."
            )

            return

        save_user(
            chat_id,
            {
                "name": name,
                "step": "phone"
            }
        )

        bot.send_message(
            chat_id,
            "شماره موبایل خود را وارد کنید:"
        )

        return

    # موبایل
    if step == "phone":

        phone = message.text.strip()

        if not re.match(PHONE_REGEX, phone):

            bot.send_message(
                chat_id,
                "شماره موبایل معتبر نیست.\nمثال: 09123456789"
            )

            return

        save_user(
            chat_id,
            {
                "phone": phone,
                "step": "date"
            }
        )

        bot.send_message(
            chat_id,
            "تاریخ تولد را وارد کنید:\n1400/01/01"
        )

        return

    # تاریخ
    if step == "date":

        date = message.text.strip()

        if not re.match(DATE_REGEX, date):

            bot.send_message(
                chat_id,
                "فرمت تاریخ صحیح نیست.\nمثال: 1400/01/01"
            )

            return

        save_user(
            chat_id,
            {
                "date": date,
                "step": "job"
            }
        )

        markup = telebot.types.InlineKeyboardMarkup()

        markup.add(
            telebot.types.InlineKeyboardButton(
                "🎓 دانشجو",
                callback_data="job_UID"
            )
        )

        markup.add(
            telebot.types.InlineKeyboardButton(
                "🎒 دانش‌آموز",
                callback_data="job_SID"
            )
        )

        markup.add(
            telebot.types.InlineKeyboardButton(
                "💼 شغل آزاد",
                callback_data="job_FID"
            )
        )

        markup.add(
            telebot.types.InlineKeyboardButton(
                "🏛️ کارمند دولت",
                callback_data="job_GID"
            )
        )

        markup.add(
            telebot.types.InlineKeyboardButton(
                "📌 سایر",
                callback_data="job_AID"
            )
        )

        bot.send_message(
            chat_id,
            "گروه شغلی شما را انتخاب کنید:",
            reply_markup=markup
        )

        return


# -------------------------
# Job Selection
# -------------------------
@bot.callback_query_handler(
    func=lambda c: c.data.startswith("job_")
)
def handle_job(call):

    chat_id = call.message.chat.id

    user = get_user(chat_id)

    if not user:
        return

    suffix = call.data.split("_")[1]

    code = generate_unique_code(suffix)

    try:

        collection.update_one(
            {"user_id": chat_id},
            {
                "$set": {
                    "job": suffix,
                    "code": code,
                    "step": "completed",
                    "completed_at": datetime.utcnow()
                }
            }
        )

        bot.send_message(
            chat_id,
            f"تبریک 🎉\n\nکد اختصاصی شما:\n{code}"
        )

        markup = telebot.types.InlineKeyboardMarkup()

        for item in CHANNELS[PLATFORM_NAME]:

            markup.add(
                telebot.types.InlineKeyboardButton(
                    item["name"],
                    url=item["url"]
                )
            )

        bot.send_message(
            chat_id,
            "لطفاً در کانال‌های زیر عضو شوید:",
            reply_markup=markup
        )

    except PyMongoError:

        bot.send_message(
            chat_id,
            "خطا در ذخیره اطلاعات. دوباره تلاش کنید."
        )


# -------------------------
# Flask Route
# -------------------------
@app.route("/")
def home():
    return "Bot is Active!"


# -------------------------
# Run Bot
# -------------------------
def run_bot():

    while True:

        try:

            bot.infinity_polling(
                timeout=30,
                long_polling_timeout=30
            )

        except Exception as e:

            print("Polling Error:", e)


# -------------------------
# Main
# -------------------------
if __name__ == "__main__":

    threading.Thread(
        target=run_bot,
        daemon=True
    ).start()

    port = int(
        os.environ.get("PORT", 8080)
    )

    app.run(
        host="0.0.0.0",
        port=port
    )
```
