import os
import random
import json
from datetime import datetime, time as dt_time
from telegram.ext import ApplicationBuilder, ContextTypes
import schedule
import asyncio
import time as t
import logging

# --- Конфиг ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")

QUOTE_FILE = "quotes.txt"
LOG_FILE = "quotes_log.json"

# --- Логирование ---
logging.basicConfig(level=logging.INFO)

# --- Функции ---
def load_quotes():
    try:
        with open(QUOTE_FILE, "r", encoding="utf-8") as f:
            return [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        print(f"[{datetime.now()}] Файл {QUOTE_FILE} не найден.")
        return []

def load_log():
    try:
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def save_log(log):
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(log, f, ensure_ascii=False, indent=2)

def random_time(start_hour=20, end_hour=21):
    hour = random.randint(start_hour, end_hour)
    minute = random.randint(0, 59)
    return f"{hour:02d}:{minute:02d}"

def get_new_quote(quotes, log):
    used_quotes = [entry["quote"] for entry in log]
    available_quotes = [q for q in quotes if q not in used_quotes]

    if not available_quotes:
        save_log([])
        return random.choice(quotes)

    return random.choice(available_quotes)

async def send_quote(context: ContextTypes.DEFAULT_TYPE):
    quotes = load_quotes()
    log = load_log()

    if not quotes:
        print(f"[{datetime.now()}] Нет доступных цитат.")
        return

    quote = get_new_quote(quotes, log)

    try:
        await context.bot.send_message(chat_id=CHANNEL_ID, text=quote)
        log.append({
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "quote": quote
        })
        save_log(log)
        print(f"[{datetime.now()}] Цитата успешно отправлена")
    except Exception as e:
        print(f"[{datetime.now()}] Ошибка при отправке: {e}")

# --- Запуск бота ---
async def main():
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    # Тестовая отправка
    print("[ТЕСТ] Отправляем тестовую цитату...")
    try:
        await send_quote(ContextTypes.DEFAULT_TYPE(application.bot_data))
    except Exception as e:
        print(f"[{datetime.now()}] Ошибка при тестовой отправке: {e}")

    # Ежедневное расписание
    def schedule_jobs():
        daily_time = random_time()
        print(f"Цитата будет отправлена в {daily_time}")
        schedule.every().day.at(daily_time).do(lambda: asyncio.create_task(send_quote(ContextTypes.DEFAULT_TYPE(application.bot_data))))

    schedule_jobs()

    # Бесконечный цикл планировщика
    while True:
        schedule.run_pending()
        t.sleep(1)

        now = dt_time(datetime.now().hour, datetime.now().minute)
        if now.hour == 0 and now.minute < 2:
            print("Сброс расписания на новый день")
            schedule.clear()
            schedule_jobs()
            t.sleep(120)

# --- Точка входа ---
if __name__ == "__main__":
    asyncio.run(main())
