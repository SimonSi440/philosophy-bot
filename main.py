import asyncio
from datetime import datetime, time as dt_time, timezone, timedelta
import os
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from aiohttp import web
from github import Github
import json
import random

# === Импорт необходимых модулей ===
import os

# === Конфигурация ===
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID", "@your_channel")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "YOUR_GITHUB_TOKEN")
REPO_OWNER = os.getenv("REPO_OWNER", "SimonSi440")
REPO_NAME = os.getenv("REPO_NAME", "philosophy-bot")
LOG_FILE = "quotes_log.json"
QUOTES_FILE = "quotes.txt"

# === Логирование ===
def log_info(message):
    print(f"[INFO] {datetime.now()} - {message}")

def log_error(message):
    print(f"[ERROR] {datetime.now()} - {message}")

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

# === Загрузка цитат ===
def load_quotes():
    try:
        with open(QUOTES_FILE, "r", encoding="utf-8") as f:
            quotes = [line.strip() for line in f if line.strip()]
            log_info(f"Загружено {len(quotes)} цитат")
            return quotes
    except Exception as e:
        log_error(f"Ошибка при загрузке цитат: {e}")
        return []

# === Загрузка логов ===
def load_log(repo):
    try:
        contents = repo.get_contents(LOG_FILE)
        log_data = json.loads(contents.decoded_content.decode('utf-8'))
        log_info(f"Загружено {len(log_data)} записей из логов")
        return log_data
    except Exception as e:
        log_error(f"Ошибка при загрузке логов: {e}")
        return []

# === Сохранение логов ===
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
        log_error(f"Ошибка при сохранении логов: {e}")

# === Отправка цитаты ===
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
        log_error(f"Ошибка при отправке цитаты: {e}")

# === Команды ===
async def start(update, context):
    await update.message.reply_text("Привет! Я бот для отправки цитат.")
    log_info(f"Команда /start от {update.effective_user.username}")

async def send_test_quote(update, context, repo):
    await send_quote(context.application, repo)
    await update.message.reply_text("Тестовая цитата отправлена!")
    log_info(f"Тестовая цитата отправлена пользователем {update.effective_user.username}")

async def reset_logs(update, context, repo):
    save_log(repo, [])
    await update.message.reply_text("Логи успешно сброшены.")
    log_info(f"Логи сброшены пользователем {update.effective_user.username}")

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

    # Регистрация команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("send_test_quote", lambda update, context: asyncio.create_task(send_test_quote(update, context, repo))))
    application.add_handler(CommandHandler("reset_logs", lambda update, context: asyncio.create_task(reset_logs(update, context, repo))))

    log_info("Команды успешно зарегистрированы")

    # Получаем порт из переменных окружения Render
    port = int(os.getenv('PORT', 8080))

    # Запуск HTTP-сервера
    await start_web_server(port)

    # Запуск бота
    bot_task = asyncio.create_task(application.run_polling(drop_pending_updates=True))

    # Планирование отправки цитат
    target_time = dt_time(12, 50)  # Время отправки — 14:25

    while True:
        now = datetime.now(timezone.utc).astimezone()  # Получаем текущее время с учетом временной зоны
        today_target_time = datetime.combine(now.date(), target_time)

        if now >= today_target_time and not any(entry["timestamp"].startswith(now.strftime("%Y-%m-%d")) for entry in load_log(repo)):
            log_info(f"Начало отправки цитаты в {today_target_time.time()}")
            await send_quote(application, repo)
            log_info(f"Окончание отправки цитаты в {today_target_time.time()}")
            # Ждем до следующего дня
            next_send_time = today_target_time + timedelta(days=1)
            while datetime.now(timezone.utc).astimezone() < next_send_time:
                await asyncio.sleep(60)  # Ждем каждую минуту
        await asyncio.sleep(60)  # Проверяем каждую минуту

if __name__ == '__main__':
    asyncio.run(main())
