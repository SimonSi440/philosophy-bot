import random
import pandas as pd
import json
from datetime import datetime
from telegram.ext import ApplicationBuilder, ContextTypes
import schedule
import asyncio
import time
import config

QUOTE_FILE = "mudrosti.csv"
LOG_FILE = "quotes_log.json"

def load_quotes():
    df = pd.read_csv(QUOTE_FILE, header=None)
    return df[0].dropna().tolist()

def load_log():
    try:
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def save_log(log):
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(log, f, ensure_ascii=False, indent=2)

def random_time(start_hour=8, end_hour=12):
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
        print(f"[{datetime.now()}] Цитата отправлена")
    except Exception as e:
        print(f"[{datetime.now()}] Ошибка при отправке: {e}")

async def job_wrapper(application: ApplicationBuilder):
    await send_quote(application)

def scheduled_job(application: ApplicationBuilder):
    asyncio.create_task(job_wrapper(application))

def main():
    application = ApplicationBuilder().token(config.BOT_TOKEN).build()

    def schedule_daily():
        daily_time = random_time()
        print(f"Цитата будет отправлена в {daily_time}")
        schedule.every().day.at(daily_time).do(scheduled_job, application=application)

    schedule_daily()

    application.run_polling(drop_pending_updates=True)

    while True:
        schedule.run_pending()
        time.sleep(1)

        now = datetime.now().time()
        if now.hour == 0 and now.minute < 2:
            schedule.clear()
            schedule_daily()
            time.sleep(120)

if __name__ == '__main__':
    main()
