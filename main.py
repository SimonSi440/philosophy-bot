import random
import pandas as pd
import json
from datetime import datetime, time as dt_time
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import schedule
import asyncio
import time
import config

QUOTE_FILE = "mudrosti.csv"
LOG_FILE = "quotes_log.json"

# === Логирование в файл ===
def log_info(message):
    with open(LOG_FILE.replace(".json", ".log"), "a", encoding="utf-8") as f:
        f.write(f"[INFO] {datetime.now()} - {message}\n")

def log_error(message):
    with open(LOG_FILE.replace(".json", ".log"), "a", encoding="utf-8") as f:
        f.write(f"[ERROR] {datetime.now()} - {message}\n")

def load_quotes():
    try:
        df = pd.read_csv(QUOTE_FILE, header=None)
        quotes = df[0].dropna().tolist()
        log_info(f"Загружено {len(quotes)} цитат")
        return quotes
    except Exception as e:
        log_error(f"Не удалось загрузить цитаты: {e}")
        return []

def load_log():
    try:
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            log_data = json.load(f)
            log_info(f"Загружено {len(log_data)} записей из логов")
            return log_data
    except (FileNotFoundError, json.JSONDecodeError):
        log_info("Логи пусты, создаю новый лог")
        return []

def save_log(log):
    try:
        with open(LOG_FILE, "w", encoding="utf-8") as f:
            json.dump(log, f, ensure_ascii=False, indent=2)
        log_info("Логи успешно обновлены")
    except Exception as e:
        log_error(f"Не удалось сохранить логи: {e}")

def random_time(start_hour=8, end_hour=12):
    hour = random.randint(start_hour, end_hour)
    minute = random.randint(0, 59)
    return f"{hour:02d}:{minute:02d}"

def get_new_quote(quotes, log):
    used_quotes = [entry["quote"] for entry in log]
    available_quotes = [q for q in quotes if q not in used_quotes]

    if not available_quotes:
        log_info("Нет доступных новых цитат, сбрасываем логи и выбираем случайную цитату")
        save_log([])
        return random.choice(quotes)
    
    log_info(f"Выбрана уникальная цитата из {len(available_quotes)} доступных цитат")
    return random.choice(available_quotes)

async def send_quote(application: ApplicationBuilder):
    quotes = load_quotes()
    log = load_log()

    if not quotes:
        log_error("Нет доступных цитат")
        return

    quote = get_new_quote(quotes, log)

    try:
        await application.bot.send_message(chat_id=config.CHANNEL_ID, text=quote)
        log.append({
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "quote": quote
        })
        save_log(log)
        log_info(f"Цитата отправлена: {quote}")
    except Exception as e:
        log_error(f"Ошибка при отправке: {e}")

async def job_wrapper(application: ApplicationBuilder):
    await send_quote(application)

def scheduled_job(application: ApplicationBuilder):
    asyncio.create_task(job_wrapper(application))

# === Команды для управления ботом ===
async def start(update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Я бот для отправки цитат.")
    log_info(f"Команда /start от {update.effective_user.username}")

async def send_test_quote(update, context: ContextTypes.DEFAULT_TYPE):
    application = context.application
    await send_quote(application)
    await update.message.reply_text("Тестовая цитата отправлена!")
    log_info(f"Команда /send_test_quote от {update.effective_user.username}")

async def reset_logs(update, context: ContextTypes.DEFAULT_TYPE):
    save_log([])
    await update.message.reply_text("Логи сброшены.")
    log_info(f"Команда /reset_logs от {update.effective_user.username}")

def main():
    application = ApplicationBuilder().token(config.BOT_TOKEN).build()

    # Добавление команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("send_test_quote", send_test_quote))
    application.add_handler(CommandHandler("reset_logs", reset_logs))
    log_info("Команды успешно зарегистрированы")

    def schedule_daily():
        daily_time = random_time()
        log_info(f"Цитата будет отправлена в {daily_time}")
        schedule.every().day.at(daily_time).do(scheduled_job, application=application)

    schedule_daily()

    # Запуск бота
    application.run_polling(drop_pending_updates=True)

    while True:
        schedule.run_pending()
        time.sleep(1)

        now = datetime.now().time()
        if now.hour == 0 and now.minute < 2:
            log_info("🔄 Сброс расписания на новый день")
            schedule.clear()
            schedule_daily()
            time.sleep(120)

if __name__ == '__main__':
    main()
