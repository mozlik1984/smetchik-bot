import os
import threading
import time
from flask import Flask
import telebot
import config
import ai_service
import file_generator

app = Flask(__name__)
bot = telebot.TeleBot(config.BOT_TOKEN)

@app.route('/')
def health_check():
    return "Bot is alive!", 200

def get_price_list_content():
    file_name = "price_list.txt"
    if os.path.exists(file_name):
        with open(file_name, "r", encoding="utf-8") as f:
            return f.read()
    return "Прайс-лист пуст."

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    welcome_text = (
        "👋 **Бот-сметчик запущен в зрячем боевом режиме!**\n\n"
        "📥 **Как составить смету:**\n"
        "Отправьте мне ссылку на Google Диск с вашим дизайн-проектом (PDF).\n"
        "Убедитесь, что доступ открыт для всех по ссылке."
    )
    bot.reply_to(message, welcome_text, parse_mode="Markdown")

@bot.message_handler(func=lambda message: True)
def handle_project_link(message):
    user_text = message.text.strip()
    
    if config.GOOGLE_DRIVE_MARKER not in user_text:
        bot.reply_to(message, "❌ Пожалуйста, отправьте корректную ссылку на Google Диск.")
        return
        
    status_message = bot.reply_to(
        message, 
        "⏳ **Ссылка принята!**\nСкачиваю чертежи проекта на сервер и передаю в зрячую модель для визуального анализа выносок и размеров..."
    )
    
    price_list = get_price_list_content()
    ai_response = ai_service.analyze_project_url_by_downloading(user_text, price_list)
    
    if isinstance(ai_response, dict) and "error" in ai_response:
        bot.edit_message_text(
            chat_id=message.chat.id, 
            message_id=status_message.message_id, 
            text=f"❌ Ошибка ИИ:\n`{ai_response['error']}`", 
            parse_mode="Markdown"
        )
        return

    if not ai_response:
        bot.edit_message_text(
            chat_id=message.chat.id, 
            message_id=status_message.message_id, 
            text="⚠️ ИИ вернул пустой результат."
        )
        return

    try:
        txt_file, xlsx_file = file_generator.generate_files(ai_response, base_name=f"смета_{message.chat.id}")
        bot.edit_message_text(
            chat_id=message.chat.id, 
            message_id=status_message.message_id, 
            text="✅ **Смета успешно сформирована!**\nОтправляю файлы..."
        )
        
        with open(txt_file, "rb") as txt, open(xlsx_file, "rb") as xlsx:
            bot.send_document(message.chat.id, txt, caption="📄 Смета в текстовом формате")
            bot.send_document(message.chat.id, xlsx, caption="📊 Итоговая таблица Excel")
            
        if os.path.exists(txt_file): os.remove(txt_file)
        if os.path.exists(xlsx_file): os.remove(xlsx_file)
    except Exception as e:
        bot.edit_message_text(
            chat_id=message.chat.id, 
            message_id=status_message.message_id, 
            text=f"❌ Ошибка сборки файлов: {str(e)}"
        )

def run_bot_polling():
    """Фоновая функция для безопасного запуска бота после открытия порта"""
    time.sleep(3)  # Даем Flask 3 секунды гарантированно занять порт Render
    try:
        bot.remove_webhook()
        bot.infinity_polling(skip_pending=True, timeout=60, long_polling_timeout=30)
    except Exception:
        pass

if __name__ == "__main__":
    # 1. Сначала запускаем фоновый поток для Telegram-бота
    bot_thread = threading.Thread(target=run_bot_polling)
    bot_thread.daemon = True
    bot_thread.start()
    
    # 2. Мгновенно открываем веб-порт в основном потоке, чтобы Render одобрил деплой
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
    
