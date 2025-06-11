import random
from datetime import datetime, time as dt_time, timedelta
import asyncio
import json
import os
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import schedule
import aiohttp.web

# === Конфиг из переменных окружения ===
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID", "@your_channel")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "YOUR_GITHUB_TOKEN")
REPO_OWNER = os.getenv("REPO_OWNER", "SimonSi440")
REPO_NAME = os.getenv("REPO_NAME", "philosophy-bot")
LOG_FILE = "quotes_log.json"
QUOTES_FILE = "quotes.txt"

# === Логирование в файл ===
def log_info(message):
    print(f"[INFO] {datetime.now()} - {message}")  # Вывод в консоль для отладки
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"[INFO] {datetime.now()} - {message}\n")
    except Exception as e:
        print(f"Ошибка при записи лога: {e}")

def log_error(message):
    print(f"[ERROR] {datetime.now()} - {message}")  # Вывод в консоль для отладки
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"[ERROR] {datetime.now()} - {message}\n")
    except Exception as e:
        print(f"Ошибка при записи лога: {e}")

# === Инициализация GitHub ===
def init_github():
    g = Github(GITHUB_TOKEN)
    repo = g.get_repo(f"{REPO_OWNER}/{REPO_NAME}")
    return repo

# === Загрузка цитат из файла quotes.txt ===
def load_quotes():
    try:
        with open(QUOTES_FILE, "r", encoding="utf-8") as f:
            quotes = [line.strip() for line in f if line.strip()]
            log_info(f"Загружено {len(quotes)} цитат")
            return quotes
    except Exception as e:
        log_error(f"Не удалось загрузить цитаты: {e}")
        return []

# === Логирование отправленных цитат ===
def load_log(repo):
    try:
        contents = repo.get_contents(LOG_FILE)
        log_data = contents.decoded_content.decode('utf-8')
        return json.loads(log_data)
    except Exception as e:
        log_error(f"Не удалось загрузить логи: {e}")
        return []

def save_log(repo, log):
    try:
        contents = repo.get_contents(LOG_FILE)
        repo.update_file(
            path=LOG_FILE,
            message="Обновление логов",
            content=json.dumps(log, ensure_ascii=False, indent=2),
            sha=contents.sha
        )
        log_info(f"Логи успешно обновлены на GitHub")
    except Exception as e:
        log_error(f"Не удалось сохранить логи: {e}")

# === Получение уникальной цитаты ===
def get_new_quote(quotes, log):
    used_quotes = [entry["quote"] for entry in log]
    available_quotes = [q for q in quotes if q not in used_quotes]

    if not available_quotes:
        save_log(repo, [])
        return random.choice(quotes)

    return random.choice(available_quotes)

# === Отправка цитаты в Telegram ===
async def send_quote(application, repo):
    quotes = load_quotes()
    log = load_log(repo)

    if not quotes:
        log_error("Нет доступных цитат")
        return

    quote = get_new_quote(quotes, log)

    try:
        cleaned_quote = quote.encode('utf-8', errors='ignore').decode('utf-8')
        await application.bot.send_message(chat_id=CHANNEL_ID, text=cleaned_quote)
        log.append({
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "quote": cleaned_quote
        })
        save_log(repo, log)
        log_info(f"Цитата успешно отправлена: {cleaned_quote}")
    except Exception as e:
        log_error(f"Ошибка при отправке: {e}")

# === Планировщик задач ===
async def job_wrapper(application, repo):
    await send_quote(application, repo)

async def scheduled_job(application, repo):
    asyncio.create_task(job_wrapper(application, repo))

# === Расписание ===
def random_time(start_hour=8, end_hour=12):
    hour = random.randint(start_hour, end_hour)
    minute = random.randint(0, 59)
    return f"{hour:02d}:{minute:02d}"

# === HTTP-сервер ===
async def start_web_server(port):
    app = aiohttp.web.Application()
    app.router.add_get('/', handle_request)
    runner = aiohttp.web.AppRunner(app)
    await runner.setup()
    site = aiohttp.web.TCPSite(runner, host='0.0.0.0', port=port)
    await site.start()
    log_info(f"HTTP-сервер запущен на порту {port}")

async def handle_request(request):
    return aiohttp.web.Response(text="OK")

# === Главная функция ===
async def main():
    application = ApplicationBuilder().token(BOT_TOKEN).build()

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
    repo = init_github()
    daily_time = random_time()
    log_info(f"Цитата будет отправлена в {daily_time}")
    next_send_time = datetime.combine(datetime.now(), dt_time.fromisoformat(daily_time))

    while True:
        now = datetime.now()
        if now >= next_send_time:
            log_info(f"Начало отправки цитаты в {now.time()}")
            await job_wrapper(application, repo)
            log_info(f"Окончание отправки цитаты в {now.time()}")
            next_send_time += timedelta(days=1)  # Планируем следующее время отправки
        await asyncio.sleep(60)  # Проверяем каждую минуту

# === Команды для управления ботом ===
async def start(update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Я бот для отправки цитат.")
    log_info(f"Команда /start от {update.effective_user.username}")

async def send_test_quote(update, context: ContextTypes.DEFAULT_TYPE):
    application = context.application
    await send_quote(application, init_github())
    await update.message.reply_text("Тестовая цитата отправлена!")
    log_info(f"Команда /send_test_quote от {update.effective_user.username}")

async def reset_logs(update, context: ContextTypes.DEFAULT_TYPE):
    save_log(init_github(), [])
    await update.message.reply_text("Логи сброшены.")
    log_info(f"Команда /reset_logs от {update.effective_user.username}")

if __name__ == '__main__':
    asyncio.run(main())
