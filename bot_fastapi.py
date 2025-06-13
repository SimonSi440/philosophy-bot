import os
import random
import json
from datetime import datetime, time as dt_time
from telegram.ext import ApplicationBuilder, ContextTypes
import schedule
import time
import asyncio
import logging
from fastapi import FastAPI

# --- Логирование ---
logging.basicConfig(level=logging.INFO)

# --- Конфиг ---
BOT_TOKEN = os.getenv("7402291623:AAFo_br8upbId8VKm_MUwAAM7LRH3aixQ0E")
CHANNEL_ID = os.getenv("CHANNEL_ID")

QUOTE_FILE = "quotes.txt"
LOG_FILE = "quotes_log.json"

app = FastAPI()

# --- Загрузка цитат ---
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

# --- Выбор случайного времени ---
def random_time(start_hour=10, end_hour=11):
    hour = random.randint(start_hour, end_hour)
    minute = random.randint(0, 59)
    return f"{hour:02d}:{minute:02d}"

# --- Получить новую цитату ---
def get_new_quote(quotes, log):
    used_quotes = [entry["quote"] for entry in log]
    available_quotes = [q for q in quotes if q not in used_quotes]

    if not available_quotes:
        save_log([])
        return random.choice(quotes)

    return random.choice(available_quotes)

# --- Отправка цитаты ---
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

# --- Настройка расписания ---
def setup_schedule(application: ApplicationBuilder):
    daily_time = random_time()
    print(f"Цитата будет отправлена в {daily_time}")
    schedule.every().day.at(daily_time).do(lambda: asyncio.create_task(send_quote(ContextTypes.DEFAULT_TYPE(application.bot))))

# --- Фоновая задача планировщика ---
async def scheduler_task(application: ApplicationBuilder):
    setup_schedule(application)
    while True:
        schedule.run_pending()
        time.sleep(1)

        now = dt_time(datetime.now().hour, datetime.now().minute)
        if now.hour == 0 and now.minute < 2:
            print("Сброс расписания на новый день")
            schedule.clear()
            setup_schedule(application)
            time.sleep(120)

# --- Тестовая отправка ---
async def test_send(application: ApplicationBuilder):
    print("[ТЕСТ] Отправляем тестовую цитату...")
    try:
        await send_quote(ContextTypes.DEFAULT_TYPE(application.bot))
    except Exception as e:
        print(f"[{datetime.now()}] Ошибка при тестовой отправке: {e}")

# --- FastAPI маршруты ---

@app.get("/")
async def root():
    return {"status": "Telegram Bot is running!"}

@app.get("/send")
async def manual_send():
    """Ручная отправка цитаты"""
    quotes = load_quotes()
    if not quotes:
        return {"error": "Нет доступных цитат"}

    application = ApplicationBuilder().token(BOT_TOKEN).build()
    await send_quote(ContextTypes.DEFAULT_TYPE(application.bot))

    return {"message": "Цитата отправлена вручную", "time": datetime.now().isoformat()}

@app.get("/status")
async def status():
    """Показывает статус бота и последнюю отправленную цитату"""
    log = load_log()
    last_quote = log[-1]["quote"] if log else None
    return {
        "status": "Bot is active",
        "current_time": datetime.now().isoformat(),
        "last_quote": last_quote,
        "total_quotes_sent": len(log),
        "next_send_time": schedule.next_run().strftime("%Y-%m-%d %H:%M:%S") if schedule.next_run() else "Не запланировано"
    }

# --- Точка входа ---
async def main():
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    # Запуск тестовой рассылки
    await test_send(application)

    # Запуск планировщика в фоне
    asyncio.create_task(scheduler_task(application))

    return app

# --- Для запуска через Gunicorn ---
if __name__ == "__main__":
    import uvicorn
    asyncio.run(main())
