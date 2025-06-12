import asyncio
from datetime import datetime, time as dt_time
from telegram.ext import ApplicationBuilder

# === Конфиг из переменных окружения ===
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID", "@your_channel")

# === Отправка цитаты в Telegram ===
async def send_quote(application):
    # Здесь можно загрузить цитату из файла или базы данных
    quote = "Вот ваша цитата на сегодня!"

    try:
        await application.bot.send_message(chat_id=CHANNEL_ID, text=quote)
        print(f"[INFO] {datetime.now()} - Цитата успешно отправлена: {quote}")
    except Exception as e:
        print(f"[ERROR] {datetime.now()} - Ошибка при отправке цитаты: {e}")

# === Главная функция ===
async def main():
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    # Запуск HTTP-сервера (для Render)
    async def start_web_server(port):
        app = web.Application()
        app.router.add_get('/', handle_request)
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, host='0.0.0.0', port=port)
        await site.start()
        print(f"[INFO] {datetime.now()} - HTTP-сервер запущен на порту {port}")

    async def handle_request(request):
        return web.Response(text="OK")

    # Получаем порт из переменных окружения Render
    port = int(os.getenv('PORT', 8080))

    # Запуск HTTP-сервера
    await start_web_server(port)

    # Проверяем текущее время каждую минуту
    while True:
        now = datetime.now()
        target_time = dt_time(10, 0)  # Время отправки цитаты — 10:35

        if now.time() >= target_time and now.date() > datetime.now().date():  # Убедимся, что это новый день
            print(f"[INFO] {datetime.now()} - Начало отправки цитаты в {target_time}")
            await send_quote(application)
            print(f"[INFO] {datetime.now()} - Окончание отправки цитаты в {target_time}")
            break  # Выходим из цикла после отправки

        await asyncio.sleep(60)  # Проверяем каждую минуту

if __name__ == '__main__':
    asyncio.run(main())
