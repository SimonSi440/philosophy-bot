# Используем официальный образ Python
FROM python:3.11-slim

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем зависимости
COPY requirements.txt .

# Устанавливаем зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Копируем исходные файлы
COPY quotes.txt

# Команда запуска через Gunicorn (с поддержкой async)
CMD ["sh", "-c", "gunicorn -w 1 -k uvicorn.workers.UvicornWorker bot_fastapi:app --bind 0.0.0.0:${PORT:-5000}"]
