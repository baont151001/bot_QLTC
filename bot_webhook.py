from flask import Flask, request
import pandas as pd
import re
from datetime import datetime
import os
import requests

# --- Cấu hình ---
TOKEN = "7750239013:AAFJ3sR_gyZIKl6dpjYqivGkX9BFiH3hcXc"
CHAT_ID = "7093031113"
CSV_FILE = "finance_log.csv"
WEBHOOK_SECRET = "yoursecret"  # Dùng để bảo vệ endpoint webhook

TELEGRAM_API_URL = f"https://api.telegram.org/bot{TOKEN}"

app = Flask(__name__)

# --- Ghi giao dịch ---
def log_transaction(date, category, type_, amount):
    try:
        df = pd.read_csv(CSV_FILE)
    except FileNotFoundError:
        df = pd.DataFrame(columns=['date', 'category', 'type', 'amount'])

    new_row = pd.DataFrame([{
        'date': date,
        'category': category,
        'type': type_,
        'amount': amount
    }])
    df = pd.concat([df, new_row], ignore_index=True)
    df.to_csv(CSV_FILE, index=False)

# --- Tổng kết ngày ---
def get_daily_summary():
    today = datetime.now().strftime('%Y-%m-%d')
    df = pd.read_csv(CSV_FILE, parse_dates=['date'])
    today_df = df[df['date'] == today]
    income = today_df[today_df['type'] == 'income']['amount'].sum()
    expense = today_df[today_df['type'] == 'expense']['amount'].sum()
    remain = income - expense
    return today, income, expense, remain

# --- Tổng kết tháng ---
def get_monthly_summary():
    now = datetime.now()
    df = pd.read_csv(CSV_FILE, parse_dates=['date'])
    this_month_df = df[(df['date'].dt.month == now.month) & (df['date'].dt.year == now.year)]
    income = this_month_df[this_month_df['type'] == 'income']['amount'].sum()
    expense = this_month_df[this_month_df['type'] == 'expense']['amount'].sum()
    remain = income - expense
    return now.strftime('%m/%Y'), income, expense, remain

# --- Gửi tin nhắn ---
def send_message(text):
    requests.post(f"{TELEGRAM_API_URL}/sendMessage", json={
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "Markdown"
    })

# --- Xử lý message từ Telegram ---
@app.route(f"/{WEBHOOK_SECRET}", methods=["POST"])
def webhook():
    data = request.get_json()

    if "message" not in data:
        return "ok"

    msg = data["message"]
    text = msg.get("text", "")
    today = datetime.now().strftime('%Y-%m-%d')

    if text.startswith("#Thu"):
        match = re.search(r"-n\s+(.+?)\s+(\d+)", text)
        if match:
            category = match.group(1)
            amount = int(match.group(2))
            log_transaction(today, category, "income", amount)
            send_message(f"✅ Thu nhập '{category}' +{amount:,}đ đã ghi.")
        else:
            send_message("❌ Cú pháp sai. Dùng: `#Thu -n Lương 10000000`")

    elif text.startswith("#Chi"):
        match = re.search(r"-n\s+(.+?)\s+(\d+)", text)
        if match:
            category = match.group(1)
            amount = int(match.group(2))
            log_transaction(today, category, "expense", amount)
            send_message(f"🧾 Chi tiêu '{category}' -{amount:,}đ đã ghi.")
        else:
            send_message("❌ Cú pháp sai. Dùng: `#Chi -n Cafe 20000`")

    elif text.startswith("#Tổng"):
        date, income, expense, remain = get_daily_summary()
        send_message(
            f"📅 Tổng kết ngày {date}:\n"
            f"📈 Thu nhập: {income:,} đ\n"
            f"📉 Chi tiêu: {expense:,} đ\n"
            f"💰 Còn lại: {remain:,} đ"
        )
    else:
        send_message("Lệnh hợp lệ:\n#Thu -n Tên 100000\n#Chi -n Tên 50000\n#Tổng")

    return "ok"

# --- Khởi động Flask ---
@app.route("/")
def index():
    return "Bot tài chính đang chạy bằng Webhook!"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
