import random
import requests
from datetime import datetime, time
import schedule
import asyncio
import json
import os

from telegram.ext import ApplicationBuilder, ContextTypes


# === Загрузка цитат из Google Sheets ===
def load_quotes():
    try:
        response = requests.get(os.getenv("GOOGLE_SHEET_URL"))
        if response.status_code == 200:
            return [line.strip() for line in response.text.splitlines() if line.strip()]
        else:
            print(f"[ОШИБКА] Не удалось загрузить цитаты. Код ответа: {response.status_code}")
            return []
    except Exception as e:
        print(f"[ОШИБКА] Ошибка подключения к Google Sheets: {e}")
        return []


# === Логирование ===
def load_log():
    if os.path.exists("quotes_log.json"):
        with open("quotes_log.json", "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return []
    return []


def save_log(log):
    with open("quotes_log.json", "w", encoding="utf-8") as f:
        json.dump(log, f, ensure_ascii=False, indent=2)


# === Получение уникальной цитаты ===
def get_new_quote(quotes, log):
    used_quotes = [entry["quote"] for entry in log]
    available_quotes = [q for q in quotes if q not in used_quotes]

    if not available_quotes:
        save_log([])
        return random.choice(quotes)
    
    return random.choice(available_quotes)


# === Функция отправки цитаты ===
async def send_quote(application):
    quotes = load_quotes()
    log = load_log()

    quote = get_new_quote(quotes, log)

    if quote:
        try:
            await application.bot.send_message(chat_id=os.getenv("CHANNEL_ID"), text=quote)
            log.append({
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "quote": quote
            })
            save_log(log)
            print(f"[{datetime.now()}] Цитата успешно отправлена")
        except Exception as e:
            print(f"[{datetime.now()}] Ошибка при отправке: {e}")
    else:
        print("[ЛОГ] Нет доступных цитат для отправки")


# === Обёртка для планировщика ===
async def job_wrapper(application):
    await send_quote(application)


def scheduled_job(application):
    asyncio.create_task(job_wrapper(application))


# === Случайное время ===
def random_time(start_hour=8, end_hour=12):
    hour = random.randint(start_hour, end_hour)
    minute = random.randint(0, 59)
    return f"{hour:02d}:{minute:02d}"


# === Основная функция бота ===
def main():
    application = ApplicationBuilder().token(os.getenv("BOT_TOKEN")).build()

    def schedule_daily():
        daily_time = random_time()
        print(f"Цитата будет отправлена в {daily_time}")
        schedule.every().day.at(daily_time).do(scheduled_job, application=application)

    # Тестовая отправка при запуске
    print("[ТЕСТ] Отправляем тестовую цитату...")
    asyncio.run(send_quote(application))

    # Установка расписания
    schedule_daily()

    # Бесконечный цикл
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
