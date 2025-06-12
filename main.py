import asyncio
from datetime import datetime, time as dt_time, timedelta
import os
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from aiohttp import web
from github import Github
import json
import random

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

def log_error(message):
    print(f"[ERROR] {datetime.now()} - {message}")  # Вывод в консоль для отладки

# === Инициализация GitHub ===
def init_github():
    try:
        g = Github(GITHUB_TOKEN)
        repo = g.get_repo(f"{REPO_OWNER}/{REPO_NAME}")
        log_info("Успешно инициализирован GitHub репозиторий")
        return repo
    except Exception as e:
        log_error(f"Ошибка при инициализации GitHub: {e}")
        return None

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

# === Загрузка логов отправленных цитат ===
def load_log(repo):
    try:
        contents = repo.get_contents(LOG_FILE)
        log_data = json.loads(contents.decoded_content.decode('utf-8'))
        log_info(f"Загружено {len(log_data)} записей из логов")
        return log_data
    except Exception as e:
        log_error(f"Не удалось загрузить логи: {e}")
        return []

# === Сохранение логов отправленных цитат ===
def save_log(repo, log):
    try:
        contents = repo.get_contents(LOG_FILE)
        repo.update_file(
            path=LOG_FILE,
            message="Обновление логов",
            content=json.dumps(log, ensure_ascii=False, indent=2),
            sha=contents.sha
        )
        log_info("Логи успешно обновлены на GitHub")
    except Exception as e:
        log_error(f"Не удалось сохранить логи: {e}")

# === Отправка цитаты в Telegram ===
async def send_quote(application, repo):
    quotes = load_quotes()
    log = load_log(repo)

    if not quotes:
        log_error("Нет доступных цитат")
        return

    quote = random.choice(quotes)

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

# === Команды для управления ботом ===
async def start(update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Я бот для отправки цитат.")
    log_info(f"Команда /start от {update.effective_user.username}")

async def send_test_quote(update, context: ContextTypes.DEFAULT_TYPE):
    application = context.application
    repo = init_github()
    await send_quote(application, repo)
    await update.message.reply_text("Тестовая цитата отправлена!")
    log_info(f"Команда /send_test_quote от {update.effective_user.username}")

async def reset_logs(update, context: ContextTypes.DEFAULT_TYPE):
    repo = init_github()
    save_log(repo, [])
    await update.message.reply_text("Логи сброшены.")
    log_info(f"Команда /reset_logs от {update.effective_user.username}")

# === HTTP-сервер ===
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

# === Главная функция ===
async def main():
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    repo = init_github()

    # Добавление команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("send_test_quote", send_test_quote))
    application.add_handler(CommandHandler("reset_logs", reset_logs))
    log_info("Команды успешно зарегистрированы")

    # Получаем порт из переменных окружения Render
    port = int(os.getenv('PORT', 8080))

    # Запуск HTTP-сервера
    await start_web_server(port)

    # Планирование отправки цитат
    target_time = dt_time(10, 0)  # Время отправки цитаты — 11:40
    while True:
        now = datetime.now()
        today_target_time = datetime.combine(now.date(), target_time)
        if now >= today_target_time and not any(entry["timestamp"].startswith(now.strftime("%Y-%m-%d")) for entry in load_log(repo)):
            log_info(f"Начало отправки цитаты в {today_target_time.time()}")
            await send_quote(application, repo)
            log_info(f"Окончание отправки цитаты в {today_target_time.time()}")
        await asyncio.sleep(60)  # Проверяем каждую минуту

if __name__ == '__main__':
    asyncio.run(main())
