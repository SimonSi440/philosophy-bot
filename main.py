import random
from datetime import datetime, time as dt_time
import asyncio
import json
import os
from telegram.ext import ApplicationBuilder, CommandHandler
from github import Github

# === Конфиг из переменных окружения ===
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID", "@your_channel")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "YOUR_GITHUB_TOKEN")
REPO_OWNER = os.getenv("REPO_OWNER", "SimonSi440")
REPO_NAME = os.getenv("REPO_NAME", "philosophy-bot")
LOG_FILE = "quotes_log.json"
QUOTES_FILE = "quotes.txt"
LOG_PATH = "bot.log"

# === Инициализация GitHub ===
def init_github():
    g = Github(GITHUB_TOKEN)
    repo = g.get_repo(f"{REPO_OWNER}/{REPO_NAME}")
    return repo

# === Логирование в файл и на GitHub ===
def log_info(message, repo):
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(f"[INFO] {datetime.now()} - {message}\n")
    save_log_to_github(repo, LOG_PATH)

def log_error(message, repo):
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(f"[ERROR] {datetime.now()} - {message}\n")
    save_log_to_github(repo, LOG_PATH)

def save_log_to_github(repo, log_path):
    try:
        log_content = ""
        if os.path.exists(log_path):
            with open(log_path, "r", encoding="utf-8") as f:
                log_content = f.read()
        
        try:
            contents = repo.get_contents(LOG_PATH)
            repo.update_file(
                path=LOG_PATH,
                message="Обновление логов",
                content=log_content,
                sha=contents.sha
            )
        except Exception as e:
            repo.create_file(
                path=LOG_PATH,
                message="Создание логов",
                content=log_content
            )
        log_info("Логи успешно обновлены на GitHub", repo)
    except Exception as e:
        log_error(f"Не удалось сохранить логи на GitHub: {e}", repo)

# === Загрузка цитат из файла quotes.txt ===
def load_quotes():
    try:
        with open(QUOTES_FILE, "r", encoding="utf-8") as f:
            quotes = [line.strip() for line in f if line.strip()]
            log_info(f"Загружено {len(quotes)} цитат", repo)
            return quotes
    except Exception as e:
        log_error(f"Не удалось загрузить цитаты: {e}", repo)
        return []

# === Логирование отправленных цитат ===
def load_log(repo):
    try:
        contents = repo.get_contents(LOG_FILE)
        log_data = contents.decoded_content.decode('utf-8')
        log = json.loads(log_data)
        log_info(f"Загружено {len(log)} записей из логов", repo)
        return log
    except Exception as e:
        log_error(f"Не удалось загрузить логи: {e}", repo)
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
        log_info("Логи успешно обновлены", repo)
    except Exception as e:
        log_error(f"Не удалось сохранить логи: {e}", repo)

# === Получение уникальной цитаты ===
def get_new_quote(quotes, log):
    used_quotes = [entry["quote"] for entry in log]
    available_quotes = [q for q in quotes if q not in used_quotes]

    if not available_quotes:
        log_info("Нет доступных новых цитат, сбрасываем логи и выбираем случайную цитату", repo)
        save_log(repo, [])
        return random.choice(quotes)

    log_info(f"Выбрана уникальная цитата из {len(available_quotes)} доступных цитат", repo)
    return random.choice(available_quotes)

# === Отправка цитаты в Telegram ===
async def send_quote(application, repo):
    quotes = load_quotes()
    if not quotes:
        log_error("Нет доступных цитат", repo)
        return

    log = load_log(repo)
    quote = get_new_quote(quotes, log)

    try:
        cleaned_quote = quote.encode('utf-8', errors='ignore').decode('utf-8')
        log_info(f"Попытка отправки цитаты: {cleaned_quote}", repo)
        await application.bot.send_message(chat_id=CHANNEL_ID, text=cleaned_quote)
        log.append({
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "quote": cleaned_quote
        })
        await save_log(repo, log)
        log_info(f"Цитата отправлена: {cleaned_quote}", repo)
    except Exception as e:
        log_error(f"Ошибка при отправке: {e}", repo)

# === Генерация случайного времени ===
def random_time(start_hour=14, end_hour=15):
    hour = random.randint(start_hour, end_hour)
    minute = random.randint(0, 59)
    return f"{hour:02d}:{minute:02d}"

# === Планировщик задач ===
async def schedule_daily(application, repo):
    daily_time = random_time()
    log_info(f"Цитата будет отправлена в {daily_time}", repo)
    send_time = datetime.strptime(daily_time, "%H:%M").time()
    while True:
        now = datetime.now().time()
        if now >= send_time:
            log_info(f"Начало отправки цитаты в {now}", repo)
            await send_quote(application, repo)
            log_info(f"Окончание отправки цитаты в {now}", repo)
            break
        await asyncio.sleep(60)  # Проверяем каждую минуту

# === Команды для управления ботом ===
async def start(update, context):
    await update.message.reply_text("Привет! Я бот для отправки цитат.")
    log_info(f"Команда /start от {update.effective_user.username}", repo)

async def send_test_quote(update, context):
    application = context.application
    repo = init_github()
    await send_quote(application, repo)
    await update.message.reply_text("Тестовая цитата отправлена!")
    log_info(f"Команда /send_test_quote от {update.effective_user.username}", repo)

async def reset_logs(update, context):
    repo = init_github()
    await save_log(repo, [])
    await update.message.reply_text("Логи сброшены.")
    log_info(f"Команда /reset_logs от {update.effective_user.username}", repo)

# === Главная функция ===
async def main():
    global repo
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    repo = init_github()

    # Добавление команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("send_test_quote", send_test_quote))
    application.add_handler(CommandHandler("reset_logs", reset_logs))

    # Настраиваем расписание
    await schedule_daily(application, repo)

    # Бесконечный цикл планировщика
    while True:
        now = datetime.now().time()
        if now.hour == 0 and now.minute < 2:
            log_info("🔄 Сброс расписания на новый день", repo)
            await schedule_daily(application, repo)
        await asyncio.sleep(60)  # Проверяем каждую минуту

if __name__ == '__main__':
    asyncio.run(main())
