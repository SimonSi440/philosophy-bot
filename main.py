import random
import pandas as pd
import json
from datetime import datetime, timedelta
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import asyncio
import os
from aiohttp import web

# Определяем LOG_PATH сразу после импорта os
LOG_PATH = os.getenv("RENDER_TMP_DIR", "./")

QUOTE_FILE = "mudrosti.csv"
LOG_FILE = os.path.join(LOG_PATH, "quotes_log.json")
LOG_LOG_FILE = os.path.join(LOG_PATH, "quotes_log.log")  # Путь к файлу логов

# === Логирование в файл ===
def log_info(message):
    print(f"[INFO] {datetime.now()} - {message}")  # Вывод в консоль для отладки
    try:
        with open(LOG_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"[INFO] {datetime.now()} - {message}\n")
    except Exception as e:
        print(f"Ошибка при записи лога: {e}")

def log_error(message):
    print(f"[ERROR] {datetime.now()} - {message}")  # Вывод в консоль для отладки
    try:
        with open(LOG_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"[ERROR] {datetime.now()} - {message}\n")
    except Exception as e:
        print(f"Ошибка при записи лога: {e}")

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
        log_info(f"Попытка отправки цитаты: {quote}")
        await application.bot.send_message(chat_id=config.CHANNEL_ID, text=quote)
        log.append({
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "quote": quote
        })
        save_log(log)
        log_info(f"Цитата успешно отправлена: {quote}")
    except Exception as e:
        log_error(f"Ошибка при отправке цитаты: {e}")

async def job_wrapper(application: ApplicationBuilder):
    await send_quote(application)

async def start_web_server(port):
    app = web.Application()
    app.router.add_get('/', handle_request)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host='0.0.0.0', port=port)
    await site.start()
    log_info(f"HTTP-сервер запущен на порту {port}")

async def handle_request(request):
    return web.Response(text="OK")

async def main():
    application = ApplicationBuilder().token(config.BOT_TOKEN).build()

    # Добавление команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("send_test_quote", send_test_quote))
    application.add_handler(CommandHandler("reset_logs", reset_logs))
    log_info("Команды успешно зарегистрированы")

    # Получаем порт из переменных окружения Render
    port = int(os.getenv('PORT', 8080))

    # Запуск HTTP-сервера
    await start_web_server(port)

    # Запуск бота
    asyncio.create_task(application.run_polling(drop_pending_updates=True))

    # Планирование отправки цитат
    while True:
        now = datetime.now()
        next_send_time = datetime.combine(now.date(), datetime.strptime(random_time(), "%H:%M").time())
        if now.time() >= next_send_time:
            log_info(f"Начало отправки цитаты в {now.time()}")
            await job_wrapper(application)
            log_info(f"Окончание отправки цитаты в {now.time()}")
            next_send_time += timedelta(days=1)  # Смещаем время на следующий день
        await asyncio.sleep(60)  # Проверяем каждую минуту

if __name__ == '__main__':
    asyncio.run(main())
