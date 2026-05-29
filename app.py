
from flask import Flask, request, jsonify
import sqlite3
import random

app = Flask(__name__)

# --- تنظیمات اصلی ---
TOKEN = "8746782518:AAFJSY20d2drM6XEJfrCL0n8ng2heES9lTA"
URL = f"https://api.telegram.org/bot{TOKEN}/"

# لینک‌های کانال‌ها طبق سناریو
CHANNEL_LINKS = [
    ("هاب مرکزی دانشجویان سمنان", "https://t.me/+h9Zkeu7nolZlOTVk"),
    ("بانک املاک سمنان", "https://t.me/+FiF2mt4xlyUwNDQ8"),
    ("بیلبورد سمنان", "https://t.me/+txeYXj6nz0I3Y2Q0"),
    ("تابلو اعلانات سمنان", "https://t.me/+ZasLGaGAUzk4OGFk")
]

# پیشوندهای کدها طبق سناریو
CODE_PREFIXES = {
    "دانشجو": "UID",
    "دانش آموز": "SID",
    "شغل آزاد": "FID",
    "کارمند دولت": "GID",
    "سایر": "AID"
}

# --- توابع کمکی دیتابیس ---
def get_db():
    conn = sqlite3.connect('users.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            chat_id INTEGER PRIMARY KEY,
            name TEXT,
            phone TEXT,
            birthdate TEXT,
            group TEXT,
            unique_code TEXT,
            step INTEGER DEFAULT 0
        )
    ''')
    conn.commit()
    conn.close()

def send_message(chat_id, text, reply_markup=None):
    payload = {'chat_id': chat_id, 'text': text}
    if reply_markup:
        payload['reply_markup'] = reply_markup
    # استفاده از requests برای ارسال به تلگرام
    import requests
    requests.post(URL + "sendMessage", json=payload)

def generate_unique_code(prefix):
    # تولید یک عدد ۵ رقمی تصادفی برای ادامه کد
    return f"{prefix}-{random.randint(10000, 99999)}"

# --- دکمه‌های کیبورد ---
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
        # دکمه‌ای که هم متن دارد و هم لینک مستقیم عضویت
        rows.append([{"text": title, "url": link}])
    return {
        "inline_keyboard": rows
    }

# --- منطق اصلی وب‌هوک ---
@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    if "message" in data:
        message = data["message"]
        chat_id = message["chat"]["id"]

        text = message.get("text")

        conn = get_db()
        cursor = conn.cursor()

        # بررسی وجود کاربر و گرفتن اطلاعات فعلی
        cursor.execute("SELECT  FROM users WHERE chat_id=?", (chat_id,))
        user = cursor.fetchone()

        # اگر کاربر جدید است یا دکمه شروع زده شده
        if text == "/start":
            # پیام خوش‌آمدگویی سناریو
            welcome_msg = """دوست عزیز سلام ☺️
خیلی خوشحالیم که مجموعه خدمات مرکزی سمنان رو انتخاب کردید.
این ربات جهت مدیریت مخاطبین و انجام طرح های تخفیفی طراحی گردیده است. از اینکه وقت با ارزش خود را جهت تکمیل موارد خواسته شده صرف می کنید بسیار سپاسگزاریم 🙏🌹"""
            send_message(chat_id, welcome_msg)

            # شروع مرحله ۱: پرسیدن نام
            if not user:
                cursor.execute("INSERT INTO users (chat_id, step) VALUES (?, ?)", (chat_id, 1))
                conn.commit()
                send_message(chat_id, "لطفاً نام و نام خانوادگی خود را وارد کنید:")
            else:
                # اگر قبلا ثبت شده، ریست نمی‌کنیم، فقط پیام می‌دهیم
                cursor.execute("UPDATE users SET step=1 WHERE chat_id=?", (chat_id,))
                conn.commit()
                send_message(chat_id, "لطفاً نام و نام خانوادگی خود را وارد کنید:")

        else:
            # اگر کاربر قبلی است و در مراحل گیر کرده
            if not user:
                # نباید پیش بیاید اما برای اطمینان
                return "ok", 200

            current_step = user["step"]

            # مرحله ۱: دریافت نام (Step 1)
            if current_step == 1:
                cursor.execute("UPDATE users SET name=?, step=2 WHERE chat_id=?", (text, chat_id))
                conn.commit()
                send_message(chat_id, "لطفاً شماره همراه خود را وارد کنید:")

            # مرحله ۲: دریافت شماره همراه (Step 2)
            elif current_step == 2:
                cursor.execute("UPDATE users SET phone=?, step=3 WHERE chat_id=?", (text, chat_id))
                conn.commit()
                send_message(chat_id, "تاریخ تولد خود را به صورت کامل وارد کنید (مثلا ۱۴۰۰/۰۱/۰۱):")

            # مرحله ۳: دریافت تاریخ تولد (Step 3)
            elif current_step == 3:
                cursor.execute("UPDATE users SET birthdate=?, step=4 WHERE chat_id=?", (text, chat_id))
                conn.commit()
                send_message(chat_id, "شما جزو کدام گروه هستید؟", reply_markup=get_group_keyboard())

            # مرحله ۴: انتخاب گروه (Step 4)
            elif current_step == 4:
                group_name = text
                prefix = CODE_PREFIXES.get(group_name, "AID") # پیشفرض AID
                unique_code = generate_unique_code(prefix)

                # ذخیره گروه و کد
                cursor.execute("""
                    UPDATE users 
                    SET group=?, unique_code=?, step=5 
                    WHERE chat_id=?
                """, (group_name, unique_code, chat_id))
                conn.commit()

                # پیام تبریک و کد (سناریو مرحله ۶)
                congrats_msg = f"""تبریک میگم به شما 👏🌹
به خانواده خدمات مرکزی خوش آمدید.
شناسه اختصاصی شما به شرح کد زیر است، این کد را یادداشت نمایید: 
{unique_code}*"""
                send_message(chat_id, congrats_msg)


                # مرحله ۵: نمایش دکمه‌های کانال (سناریو مرحله ۷)
                channel_msg = "تمایل دارید در کدام کانال مجموعه خدمات مرکزی عضو شوید؟"
                send_message(chat_id, channel_msg, reply_markup=get_channel_keyboard())

                # چون با دکمه Inline کار می‌کنیم، کاربر دیگر پیام متنی نمی‌فرستد، 
                # بنابراین مرحله بعدی نیاز به دریافت متن ندارد.
                # می‌توانیم step را روی 99 بگذاریم که یعنی پایان کار

    return "ok", 200

if name == "__main__":
    init_db()
    app.run(host='0.0.0.0', port=5000)
