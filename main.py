import os
import random
import json
from datetime import datetime
from telegram.ext import ApplicationBuilder, ContextTypes
import schedule
import asyncio
import time
import config
from flask import Flask

# Пути к файлам
QUOTE_FILE = "quotes.txt"
LOG_FILE = "quotes_log.json"

# Создание Flask-приложения
app = Flask(__name__)

# Загрузка цитат из CSV (как обычный текст)
def load_quotes():
    with open(QUOTE_FILE, "r", encoding="utf-8") as f:
        quotes = [line.strip() for line in f if line.strip()]
    return quotes

# Загрузка лога
def load_log():
    try:
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

# Сохранение лога
def save_log(log):
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(log, f, ensure_ascii=False, indent=2)

# Случайное время публикации
def random_time(start_hour=20, end_hour=21):
    hour = random.randint(start_hour, end_hour)
    minute = random.randint(0, 59)
    return f"{hour:02d}:{minute:02d}"

# Получить новую неповторённую цитату
def get_new_quote(quotes, log):
    used_quotes = [entry["quote"] for entry in log]
    available_quotes = [q for q in quotes if q not in used_quotes]

    if not available_quotes:
        save_log([])
        return random.choice(quotes)

    return random.choice(available_quotes)

# Отправка цитаты в Telegram
async def send_quote(application: ApplicationBuilder):
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
        print(f"[{datetime.now()}] Цитата успешно отправлена")
    except Exception as e:
        print(f"[{datetime.now()}] Ошибка при отправке: {e}")

# Обёртка для планировщика
async def job_wrapper(application: ApplicationBuilder):
    await send_quote(application)

# Функция для запуска задачи в планировщике
def scheduled_job(application: ApplicationBuilder):
    asyncio.create_task(job_wrapper(application))

# Основная функция запуска бота
def main():
    application = ApplicationBuilder().token(config.BOT_TOKEN).build()

    # Ежедневное расписание
    def schedule_daily():
        daily_time = random_time()
        print(f"Цитата будет отправлена в {daily_time}")
        schedule.every().day.at(daily_time).do(scheduled_job, application=application)

    schedule_daily()

    # Тестовая отправка при запуске
    print("[ТЕСТ] Отправляем тестовую цитату...")
    asyncio.run(send_quote(application))

    # Бесконечный цикл планировщика
    while True:
        schedule.run_pending()
        time.sleep(1)

        now = datetime.now().time()
        if now.hour == 0 and now.minute < 2:
            print("Сброс расписания на новый день")
            schedule.clear()
            schedule_daily()
            time.sleep(120)  # Чтобы не вызвать дважды

# Создаем маршрут для проверки работы сервера
@app.route('/')
def index():
    return 'Telegram Bot is running!'

# Запуск Flask-приложения
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
