import random
from datetime import datetime
import schedule
import asyncio
import time
import json
import os
import requests
from telegram.ext import ApplicationBuilder


# === Конфиг из переменных окружения ===
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID", "@your_channel")
GOOGLE_SHEET_URL = os.getenv("GOOGLE_SHEET_URL", "https://docs.google.com/spreadsheets/d/.../export?format=csv&id=...&gid=0")

LOG_FILE = "quotes_log.json"


# === Тестовый список цитат === 
test_quotes = [
    "😎 Ты не контролируешь мир, поросёнок...",
    "💀 Люди жалуются на жизнь...",
    "⚔️ Делай дело, диванный эксперт...",
    "🧠 Ты — то, что ты делаешь регулярно, а не то, о чём мечтаешь в туалете.",
    "🤔 Если ты зависишь от одобрения других — ты раб, а не нормис. Даже если они тебя любят, тюбик",
    "🤯 Ты боишься смерти, голова говяжья? Тогда ты жив уже не первый год напрасно",
    "🎮 Всё, что тебя бесит — твоя проблема, психушка. Учись терпеть, АНАЛИТИК",
    "🌟 Счастье — не подарок судьбы, мемасоид. Это результат правильной жизни, а не мемасиков до утра"
]


# === Заглушка для тестирования ===
def load_quotes():
    # Используем тестовый список вместо Google Sheets
    return test_quotes


# === Логирование отправленных цитат ===
def load_log():
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return []
    return []


def save_log(log):
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(log, f, ensure_ascii=False, indent=2)


# === Получение уникальной цитаты ===
def get_new_quote(quotes, log):
    used_quotes = [entry["quote"] for entry in log]
    available_quotes = [q for q in quotes if q not in used_quotes]

    if not available_quotes:
        save_log([])
        return random.choice(quotes)

    return random.choice(available_quotes)


# === Отправка цитаты в Telegram ===
async def send_quote(application):
    quotes = load_quotes()
    log = load_log()

    quote = get_new_quote(quotes, log)

    try:
        # Очистка текста от "битых" символов
        cleaned_quote = quote.encode('utf-8', errors='ignore').decode('utf-8')
        await application.bot.send_message(chat_id=CHANNEL_ID, text=cleaned_quote)
        log.append({
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "quote": cleaned_quote
        })
        save_log(log)
        print(f"[{datetime.now()}] Цитата отправлена: {cleaned_quote}")
    except Exception as e:
        print(f"[{datetime.now()}] Ошибка при отправке: {e}")


# === Планировщик задач ===
async def job_wrapper(application):
    await send_quote(application)

def scheduled_job(application):
    asyncio.create_task(job_wrapper(application))


# === Расписание ===
def random_time(start_hour=8, end_hour=12):
    hour = random.randint(start_hour, end_hour)
    minute = random.randint(0, 59)
    return f"{hour:02d}:{minute:02d}"


# === Главная функция ===
def main():
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    def schedule_daily():
        daily_time = random_time()
        print(f"Цитата будет отправлена в {daily_time}")
        schedule.every().day.at(daily_time).do(scheduled_job, application=application)

    # Тестовая отправка при запуске
    print("[ТЕСТ] Отправляем тестовую цитату...")
    asyncio.run(send_quote(application))

    # Настраиваем расписание
    schedule_daily()

    # Бесконечный цикл планировщика
    while True:
        schedule.run_pending()
        time.sleep(1)

        now = datetime.now().time()
        if now.hour == 0 and now.minute < 2:
            print("🔄 Сброс расписания на новый день")
            schedule.clear()
            schedule_daily()
            time.sleep(120)  # Защита от дублирования


if __name__ == '__main__':
    main()
