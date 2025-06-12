import asyncio
from datetime import datetime, time as dt_time
from telegram.ext import ApplicationBuilder
from github import Github

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
        await application.bot.send_message(chat_id=CHANNEL_ID, text=quote)
        log.append({
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "quote": quote
        })
        save_log(repo, log)
        log_info(f"Цитата успешно отправлена: {quote}")
    except Exception as e:
        log_error(f"Ошибка при отправке цитаты: {e}")

# === Главная функция ===
async def main():
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    repo = init_github()

    # Добавление команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("send_test_quote", send_test_quote))
    application.add_handler(CommandHandler("reset_logs", reset_logs))
    log_info("Команды успешно зарегистрированы")

    # Планирование отправки цитат
    target_time = dt_time(10, 0)  # Время отправки цитаты — 10:00
    while True:
        now = datetime.now()
        if now.time() >= target_time and now.date() > datetime.now().date():  # Убедимся, что это новый день
            log_info(f"Начало отправки цитаты в {target_time}")
            await send_quote(application, repo)
            log_info(f"Окончание отправки цитаты в {target_time}")
            break  # Выходим из цикла после отправки

        await asyncio.sleep(60)  # Проверяем каждую минуту

# === Команды для управления ботом ===
async def start(update, context):
    await update.message.reply_text("Привет! Я бот для отправки цитат.")
    log_info(f"Команда /start от {update.effective_user.username}")

async def send_test_quote(update, context):
    application = context.application
    repo = init_github()
    await send_quote(application, repo)
    await update.message.reply_text("Тестовая цитата отправлена!")
    log_info(f"Команда /send_test_quote от {update.effective_user.username}")

async def reset_logs(update, context):
    repo = init_github()
    save_log(repo, [])
    await update.message.reply_text("Логи сброшены.")
    log_info(f"Команда /reset_logs от {update.effective_user.username}")

if __name__ == '__main__':
    asyncio.run(main())
