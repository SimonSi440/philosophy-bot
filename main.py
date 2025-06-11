import random
import pandas as pd
import json
from datetime import datetime, timedelta
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import asyncio
import os
from aiohttp import web
from github import Github

# === Конфиг из переменных окружения ===
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID", "@your_channel")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "YOUR_GITHUB_TOKEN")
REPO_OWNER = os.getenv("REPO_OWNER", "SimonSi440")
REPO_NAME = os.getenv("REPO_NAME", "philosophy-bot")
QUOTE_FILE = "mudrosti.csv"
LOG_FILE = "quotes_log.json"
LOG_LOG_FILE = "quotes_log.log"  # Локальный путь к файлу логов

# === Инициализация GitHub ===
def init_github():
    try:
        g = Github(GITHUB_TOKEN)
        repo = g.get_repo(f"{REPO_OWNER}/{REPO_NAME}")
        log_info("Успешно инициализирован GitHub репозиторий", repo)
        return repo
    except Exception as e:
        log_error(f"Ошибка при инициализации GitHub: {e}")
        return None

# === Логирование в файл ===
def log_info(message, repo=None):
    print(f"[INFO] {datetime.now()} - {message}")  # Вывод в консоль для отладки
    with open(LOG_LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[INFO] {datetime.now()} - {message}\n")
    if repo:
        buffer_log(repo)

def log_error(message, repo=None):
    print(f"[ERROR] {datetime.now()} - {message}")  # Вывод в консоль для отладки
    with open(LOG_LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[ERROR] {datetime.now()} - {message}\n")
    if repo:
        buffer_log(repo)

# === Буферизация логов ===
log_buffer = []
BUFFER_SIZE = 30  # Количество записей для буферизации
BUFFER_INTERVAL = 300  # Интервал обновления логов на GitHub (в секундах)

def buffer_log(repo):
    global log_buffer
    log_buffer.append(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    if len(log_buffer) >= BUFFER_SIZE:
        save_log_to_github(repo, LOG_LOG_FILE)
        log_buffer = []

async def save_log_to_github(repo, log_path):
    try:
        log_content = ""
        if os.path.exists(log_path):
            with open(log_path, "r", encoding="utf-8") as f:
                log_content = f.read()
        
        try:
            contents = repo.get_contents(log_path)
            repo.update_file(
                path=log_path,
                message="Обновление логов",
                content=log_content,
                sha=contents.sha
            )
        except Exception as e:
            repo.create_file(
                path=log_path,
                message="Создание логов",
                content=log_content
            )
        log_info("Логи успешно обновлены на GitHub", repo)
    except Exception as e:
        log_error(f"Не удалось сохранить логи на GitHub: {e}", repo)

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

async def send_quote(application: ApplicationBuilder, repo):
    quotes = load_quotes()
    log = load_log()

    if not quotes:
        log_error("Нет доступных цитат", repo)
        return

    quote = get_new_quote(quotes, log)

    try:
        log_info(f"Попытка отправки цитаты: {quote}", repo)
        await application.bot.send_message(chat_id=CHANNEL_ID, text=quote)
        log.append({
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "quote": quote
        })
        save_log(log)
        log_info(f"Цитата успешно отправлена: {quote}", repo)
    except Exception as e:
        log_error(f"Ошибка при отправке цитаты: {e}", repo)

async def job_wrapper(application: ApplicationBuilder, repo):
    await send_quote(application, repo)

async def start_web_server(port, repo):
    app = web.Application()
    app.router.add_get('/', handle_request)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host='0.0.0.0', port=port)
    await site.start()
    log_info(f"HTTP-сервер запущен на порту {port}", repo)

async def handle_request(request):
    return web.Response(text="OK")

# === Команды для управления ботом ===
async def start(update, context: ContextTypes.DEFAULT_TYPE, repo):
    await update.message.reply_text("Привет! Я бот для отправки цитат.")
    log_info(f"Команда /start от {update.effective_user.username}", repo)

async def send_test_quote(update, context: ContextTypes.DEFAULT_TYPE, repo):
    application = context.application
    await send_quote(application, repo)
    await update.message.reply_text("Тестовая цитата отправлена!")
    log_info(f"Команда /send_test_quote от {update.effective_user.username}", repo)

async def reset_logs(update, context: ContextTypes.DEFAULT_TYPE, repo):
    save_log([])
    await update.message.reply_text("Логи сброшены.")
    log_info(f"Команда /reset_logs от {update.effective_user.username}", repo)

async def main():
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    # Инициализация GitHub
    repo = init_github()

    # Добавление команд
    application.add_handler(CommandHandler("start", lambda update, context: start(update, context, repo)))
    application.add_handler(CommandHandler("send_test_quote", lambda update, context: send_test_quote(update, context, repo)))
    application.add_handler(CommandHandler("reset_logs", lambda update, context: reset_logs(update, context, repo)))
    log_info("Команды успешно зарегистрированы", repo)

    # Получаем порт из переменных окружения Render
    port = int(os.getenv('PORT', 8080))

    # Запуск HTTP-сервера
    await start_web_server(port, repo)

    # Запуск бота
    await application.run_polling(drop_pending_updates=True)

    # Планирование отправки цитат
    while True:
        now = datetime.now()
        next_send_time = datetime.combine(now.date(), datetime.strptime(random_time(), "%H:%M").time())
        if now.time() >= next_send_time:
            log_info(f"Начало отправки цитаты в {now.time()}", repo)
            await job_wrapper(application, repo)
            log_info(f"Окончание отправки цитаты в {now.time()}", repo)
            next_send_time += timedelta(days=1)  # Смещаем время на следующий день
        await asyncio.sleep(60)  # Проверяем каждую минуту

if __name__ == '__main__':
    repo = init_github()
    asyncio.run(main())
