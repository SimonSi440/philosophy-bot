# Используем официальный образ Python
FROM python:3.11-slim

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем зависимости
COPY requirements.txt .

# Устанавливаем зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Копируем исходные файлы
COPY . .

# Команда запуска через Gunicorn (с поддержкой async)
CMD ["uvicorn", "bot_fastapi:app", "--host", "0.0.0.0", "--port", "5000"]
