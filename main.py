import random
from datetime import datetime
import schedule
import asyncio
import time
import json
import os
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


# === Инициализация GitHub ===
def init_github():
    g = Github(GITHUB_TOKEN)
    repo = g.get_repo(f"{REPO_OWNER}/{REPO_NAME}")
    return repo


# === Загрузка цитат из файла quotes.txt ===
def load_quotes():
    try:
        with open(QUOTES_FILE, "r", encoding="utf-8") as f:
            return [line.strip() for line in f if line.strip()]
    except Exception as e:
        print(f"[ОШИБКА] Не удалось загрузить цитаты: {e}")
        return []


# === Логирование отправленных цитат ===
def load_log(repo):
    try:
        contents = repo.get_contents(LOG_FILE)
        log_data = contents.decoded_content.decode('utf-8')
        return json.loads(log_data)
    except Exception as e:
        print(f"[ОШИБКА] Не удалось загрузить логи: {e}")
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
        print(f"[{datetime.now()}] Логи успешно обновлены")
    except Exception as e:
        print(f"[ОШИБКА] Не удалось сохранить логи: {e}")


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
        print("[ОШИБКА] Нет доступных цитат")
        return

    quote = get_new_quote(quotes, log)

    try:
        # Очистка текста от "битых" символов
        cleaned_quote = quote.encode('utf-8', errors='ignore').decode('utf-8')
        await application.bot.send_message(chat_id=CHANNEL_ID, text=cleaned_quote)
        log.append({
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "quote": cleaned_quote
        })
        save_log(repo, log)
        print(f"[{datetime.now()}] Цитата отправлена: {cleaned_quote}")
    except Exception as e:
        print(f"[{datetime.now()}] Ошибка при отправке: {e}")


# === Планировщик задач ===
async def job_wrapper(application, repo):
    await send_quote(application, repo)

def scheduled_job(application, repo):
    asyncio.create_task(job_wrapper(application, repo))


# === Расписание ===
def random_time(start_hour=8, end_hour=12):
    hour = random.randint(start_hour, end_hour)
    minute = random.randint(0, 59)
    return f"{hour:02d}:{minute:02d}"


# === Главная функция ===
def main():
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    repo = init_github()

    def schedule_daily():
        daily_time = random_time()
        print(f"Цитата будет отправлена в {daily_time}")
        schedule.every().day.at(daily_time).do(scheduled_job, application=application, repo=repo)

    # Тестовая отправка при запуске
    print("[ТЕСТ] Отправляем тестовую цитату...")
    asyncio.run(send_quote(application, repo))

    # Настраиваем расписание
    schedule_daily()

    # Бесконечный цикл планировщика
    while True:
        schedule.run_pending()
        time.sleep(1)

        now = datetime.now().time()
        if now.hour == 0 and now.minute < 2:
            print("🔄 Сброс расписания на новый день")
            schedule.clear()
            schedule_daily()
            time.sleep(120)  # Защита от дублирования


if __name__ == '__main__':
    main()
