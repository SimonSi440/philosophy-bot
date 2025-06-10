import random
from datetime import datetime
import schedule
import asyncio
import time
import json
import os
import requests
from telegram.ext import ApplicationBuilder

import config  # Убедись, что есть config.py с BOT_TOKEN и CHANNEL_ID

import logging
from flask import Flask

app = Flask(__name__)

@app.route('/')
def health_check():
    return 'OK', 200

# Загрузка цитат из Google Таблицы (CSV)
def load_quotes():
    try:
        response = requests.get(config.GOOGLE_SHEET_URL)
        if response.status_code == 200:
            return [line.strip() for line in response.text.splitlines() if line.strip()]
        else:
            print(f"[ОШИБКА] Не удалось загрузить цитаты")
            return []
    except Exception as e:
        print(f"[ОШИБКА] При загрузке цитат: {e}")
        return []

# Загрузка логов
def load_log():
    if os.path.exists("quotes_log.json"):
        with open("quotes_log.json", "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return []
    return []

# Сохранение лога
def save_log(log):
    with open("quotes_log.json", "w", encoding="utf-8") as f:
        json.dump(log, f, ensure_ascii=False, indent=2)

# Получить новую уникальную цитату
def get_new_quote(quotes, log):
    used_quotes = [entry["quote"] for entry in log]
    available_quotes = [q for q in quotes if q not in used_quotes]

    if not available_quotes:
        save_log([])
        return random.choice(quotes)

    return random.choice(available_quotes)

# Отправка цитаты
async def send_quote(application):
    quotes = load_quotes()
    log = load_log()

    quote = get_new_quote(quotes, log)

    try:
        await application.bot.send_message(chat_id=config.CHANNEL_ID, text=quote)
        log.append({
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "quote": quote
        })
        save_log(log)
        print(f"[{datetime.now()}] Цитата отправлена")
    except Exception as e:
        print(f"[{datetime.now()}] Ошибка при отправке: {e}")

# Обёртка для планировщика
async def job_wrapper(application):
    await send_quote(application)

def scheduled_job(application):
    asyncio.create_task(job_wrapper(application))

# Случайное время
def random_time(start_hour=8, end_hour=12):
    hour = random.randint(start_hour, end_hour)
    minute = random.randint(0, 59)
    return f"{hour:02d}:{minute:02d}"

# Главный запуск
def main():
    application = ApplicationBuilder().token(config.BOT_TOKEN).build()

    def schedule_daily():
        daily_time = random_time()
        print(f"Цитата будет отправлена в {daily_time}")
        schedule.every().day.at(daily_time).do(scheduled_job, application=application)

    # Тестовая отправка при старте
    print("[ТЕСТ] Отправляем тестовую цитату...")
    asyncio.run(send_quote(application))

    # Запуск планировщика
    schedule_daily()

    while True:
        schedule.run_pending()
        time.sleep(1)

        now = datetime.now().time()
        if now.hour == 0 and now.minute < 2:
            print("🔄 Сброс расписания на новый день")
            schedule.clear()
            schedule_daily()
            time.sleep(120)  # Защита от повторного сброса

if __name__ == '__main__':
    main()
