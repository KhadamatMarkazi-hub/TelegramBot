import os
import random
import string
from flask import Flask, request
import telebot
from pymongo import MongoClient

# تنظیمات اولیه
TOKEN = os.environ.get('TOKEN')
MONGO_URI = os.environ.get('MONGO_URI')
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# اتصال به دیتابیس MongoDB
client = MongoClient(MONGO_URI)
db = client['telegram_db']
users_collection = db['users']

# تابع تولید کد اختصاصی تصادفی
def generate_unique_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

@app.route('/webhook', methods=['POST'])
def receive_update():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return ''
    else:
        return 'Forbidden', 403

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    username = message.from_user.username
    
    # چک کردن اینکه آیا کاربر قبلاً در دیتابیس هست؟
    user_data = users_collection.find_one({"user_id": user_id})
    
    if user_data:
        # اگر کاربر قبلاً ثبت شده بود، کد قبلی را به او نشان بده
        assigned_code = user_data['code']
        bot.reply_to(message, f"سلام محمد جان (یا کاربر عزیز)! خوش اومدی.\nکد اختصاصی شما قبلاً صادر شده: {assigned_code}")
    else:
        # اگر کاربر جدید است، یک کد بساز و ذخیره کن
        new_code = generate_unique_code()
        users_collection.insert_one({
            "user_id": user_id,
            "username": username,
            "code": new_code
        })
        bot.reply_to(message, f"خوش اومدی! این اولین بار هست که پیام میدی.\nکد اختصاصی شما ساخته شد: {new_code}")

@app.route('/')
def index():
    return "Bot is Running!"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get('PORT', 5000)))
