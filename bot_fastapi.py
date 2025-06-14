from fastapi import FastAPI, HTTPException
import os
import random
import asyncio
from datetime import datetime, time as dt_time, timedelta
from telegram.ext import ApplicationBuilder, ContextTypes
import json
import pytz
from google.oauth2 import service_account
from google.cloud import logging as cloud_logging

# --- Конфиг ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
QUOTE_FILE = "quotes.txt"
LOG_DIR = "logs"  # Директория для логов
LOG_FILE = os.path.join(LOG_DIR, "quotes_log.json")  # Путь к файлу логов
LOG_NAME = "philosophy-bot"  # Имя журнала
app = FastAPI()

# --- Глобальные переменные ---
application = None
next_run_time = None  # Добавляем глобальную переменную для хранения времени следующей отправки
startup_time = None  # Время запуска бота
error_count = 0  # Счетчик ошибок при отправке
last_send_date = None  # Дата последней отправки цитаты

# --- Часовой пояс +3 часа ---
TIMEZONE = pytz.timezone('Etc/GMT-3')  # GMT-3 соответствует UTC+3

# --- Инициализация клиента Google Cloud Logging ---
def initialize_google_logging():
    credentials_json = os.getenv("GOOGLE_APPLICATION_CREDENTIALS_JSON")
    if not credentials_json:
        raise ValueError("GOOGLE_APPLICATION_CREDENTIALS_JSON не установлен")
    credentials_info = json.loads(credentials_json)
    credentials = service_account.Credentials.from_service_account_info(credentials_info)
    client = cloud_logging.Client(credentials=credentials, project=os.getenv("PROJECT_ID"))
    logger = client.logger(LOG_NAME)
    return logger

logger = initialize_google_logging()

def log_message(message):
    try:
        logger.log_struct({
            "timestamp": datetime.now(TIMEZONE).isoformat(),
            "message": message
        })
    except Exception as e:
        print(f"[ТЕСТ] Ошибка при отправке лога в Google Cloud Logging: {e}")

@app.on_event("startup")
async def startup_event():
    global application, startup_time, last_send_date
    if not BOT_TOKEN or not CHANNEL_ID:
        raise ValueError("BOT_TOKEN или CHANNEL_ID не установлены")
    # Создаем и инициализируем бота один раз при старте
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    await application.initialize()
    log_message("[ТЕСТ] Бот успешно инициализирован")
    # Запоминаем время запуска
    startup_time = datetime.now(TIMEZONE)
    # Загружаем дату последней отправки из логов
    log = load_log()
    if log:
        last_send_date = datetime.strptime(log[-1]["timestamp"], "%Y-%m-%d %H:%M:%S").date()
    else:
        last_send_date = None
    # Запуск ежедневной рассылки в фоне
    asyncio.create_task(daily_quote_scheduler())

# --- Загрузка цитат ---
def load_quotes():
    try:
        with open(QUOTE_FILE, "r", encoding="utf-8") as f:
            return [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        log_message(f"[{datetime.now(TIMEZONE)}] Файл {QUOTE_FILE} не найден.")
        return []

# --- Загрузка логов ---
def load_log():
    try:
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        log_message(f"[{datetime.now(TIMEZONE)}] Файл {LOG_FILE} не найден. Создаем новый лог.")
        return []

# --- Сохранение логов ---
def save_log(log):
    try:
        # Убедимся, что директория существует
        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
        with open(LOG_FILE, "w", encoding="utf-8") as f:
            json.dump(log, f, ensure_ascii=False, indent=2)
        log_message(f"[{datetime.now(TIMEZONE)}] Лог успешно сохранен.")
    except Exception as e:
        log_message(f"[{datetime.now(TIMEZONE)}] Ошибка при сохранении лога: {e}")

# --- Получить новую цитату ---
def get_new_quote(quotes, log):
    used_quotes = [entry["quote"] for entry in log]
    available_quotes = [q for q in quotes if q not in used_quotes]
    if not available_quotes:
        save_log([])
        return random.choice(quotes)
    return random.choice(available_quotes)

# --- Подсчет оставшихся уникальных цитат ---
def get_remaining_unique_quotes(quotes, log):
    used_quotes = [entry["quote"] for entry in log]
    available_quotes = [q for q in quotes if q not in used_quotes]
    return len(available_quotes)

# --- Отправка цитаты ---
async def send_quote():
    global error_count, last_send_date
    quotes = load_quotes()
    log = load_log()
    current_date = datetime.now(TIMEZONE).date()
    # Проверяем, была ли уже отправлена цитата сегодня
    if last_send_date and last_send_date == current_date:
        log_message(f"[{datetime.now(TIMEZONE)}] Цитата уже была отправлена сегодня.")
        return
    if not quotes:
        log_message(f"[{datetime.now(TIMEZONE)}] Нет доступных цитат.")
        return
    quote = get_new_quote(quotes, log)
    try:
        await application.bot.send_message(chat_id=CHANNEL_ID, text=quote)
        log.append({
            "timestamp": datetime.now(TIMEZONE).strftime("%Y-%m-%d %H:%M:%S"),
            "quote": quote
        })
        save_log(log)
        last_send_date = current_date  # Обновляем дату последней отправки
        log_message(f"[{datetime.now(TIMEZONE)}] Цитата успешно отправлена")
    except Exception as e:
        log_message(f"[{datetime.now(TIMEZONE)}] Ошибка при отправке: {e}")
        error_count += 1

# --- Время следующей отправки ---
def get_next_send_time(start_hour=18, end_hour=18):
    now = datetime.now(TIMEZONE)  # Используем offset-aware datetime
    hour = random.randint(start_hour, end_hour)
    minute = random.randint(26, 31)
    next_time = datetime.combine(now.date(), dt_time(hour, minute))
    next_time = TIMEZONE.localize(next_time)  # Добавляем часовой пояс к next_time
    if next_time <= now:
        next_time += timedelta(days=1)  # Если уже прошло — переносим на завтра
    return next_time

# --- Асинхронный планировщик ---
async def daily_quote_scheduler():
    global next_run_time  # Используем глобальную переменную
    while True:
        # Получаем время следующей отправки
        next_run_time = get_next_send_time()  # Обновляем глобальную переменную
        wait_seconds = (next_run_time - datetime.now(TIMEZONE)).total_seconds()
        log_message(f"[ПЛАНИРОВЩИК] Следующая рассылка запланирована на {next_run_time} (~{int(wait_seconds)} секунд)")
        # Ждём до нужного времени
        await asyncio.sleep(wait_seconds)
        # Отправляем цитату
        await send_quote()

# --- Тестовая отправка ---
@app.get("/send")
async def manual_send():
    await send_quote()
    return {"message": "Цитата отправлена вручную", "time": datetime.now(TIMEZONE).isoformat()}

# --- Статус бота ---
@app.get("/status")
async def status():
    log = load_log()
    quotes = load_quotes()
    total_quotes = len(quotes)
    used_quotes = len(log)
    remaining_unique_quotes = get_remaining_unique_quotes(quotes, log)
    last_quote = log[-1]["quote"] if log else None
    next_run = next_run_time
    return {
        "status": "Bot is active",
        "current_time": datetime.now(TIMEZONE).isoformat(),
        "startup_time": startup_time.isoformat() if startup_time else "Не определено",
        "last_quote": last_quote,
        "total_quotes": total_quotes,
        "used_quotes": used_quotes,
        "remaining_unique_quotes": remaining_unique_quotes,
        "total_quotes_sent": len(log),
        "quote_usage_percentage": f"{(used_quotes / total_quotes * 100):.2f}%" if total_quotes > 0 else "0%",
        "next_send_time": next_run.strftime("%Y-%m-%d %H:%M:%S") if next_run else "Не определено",
        "last_send_date": last_send_date.isoformat() if last_send_date else "Не определено",
        "error_count": error_count
    }

# --- Маршрут для корневого URL ---
@app.get("/")
async def root():
    return {"message": "Добро пожаловать в Philosophy Bot API", "endpoints": ["/status", "/send"]}

# --- Точка входа ---
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("bot_fastapi:app", host="0.0.0.0", port=5000)
