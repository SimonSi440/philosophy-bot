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
    try:
        g = Github(GITHUB_TOKEN)
        repo = g.get_repo(f"{REPO_OWNER}/{REPO_NAME}")
        log_info(f"Успешно инициализирован GitHub репозиторий: {REPO_OWNER}/{REPO_NAME}", repo)
        return repo
    except Exception as e:
        log_error(f"Ошибка при инициализации GitHub: {e}", repo)
        return None

# === Логирование в файл и на GitHub ===
def log_info(message, repo=None):
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(f"[INFO] {datetime.now()} - {message}\n")
    if repo:
        save_log_to_github(repo, LOG_PATH)

def log_error(message, repo=None):
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(f"[ERROR] {datetime.now()} - {message}\n")
    if repo:
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
            log_info(f"Загружено {len(quotes)} цитат")
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
        log_info(f"Загружено {len(log)} записей из логов")
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
        log_error(f"Не удалось сохранить логи: {e}")

# === Получение уникальной цитаты ===
def get_new_quote(quotes, log):
    used_quotes = [entry["quote"] {
