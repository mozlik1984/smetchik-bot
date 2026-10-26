import os
import threading
from flask import Flask
import telebot
import config
import ai_service
import file_generator

# 1. Настройка заглушки веб-сервера для Render
app = Flask(__name__)

@app.route('/')
def health_check():
    return "Bot is alive!", 200

def run_web_server():
    # Render автоматически передает порт в переменную окружения PORT
    port = int(os.environ.get("PORT", 8080))
    # Запускаем на 0.0.0.0, чтобы Render снаружи мог достучаться
    app.run(host="0.0.0.0", port=port)

# 2. Инициализация Telegram бота
bot = telebot.TeleBot(config.BOT_TOKEN)

def get_price_list_content():
    file_name = "price_list.txt"
    if os.path.exists(file_name):
        with open(file_name, "r", encoding="utf-8") as f:
            return f.read()
    return "Прайс-лист пуст или отсутствует."

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    welcome_text = (
        "👋 Приветствую! Я ваш бот-сметчик.\n\n"
        "📥 Отправьте мне прямую ссылку на дизайн-проект из Google Диска."
    )
    bot.reply_to(message, welcome_text)

@bot.message_handler(func=lambda message: True)
def handle_project_link(message):
    user_text = message.text.strip()
    if config.GOOGLE_DRIVE_MARKER not in user_text:
        bot.reply_to(message, "❌ Отправьте корректную ссылку на Google Диск.")
        return
        
    status_message = bot.reply_to(message, "⏳ Анализирую проект и прайс-лист...")
    price_list = get_price_list_content()
    ai_response = ai_service.analyze_project_with_ai(user_text, price_list)
    
    if isinstance(ai_response, dict) and "error" in ai_response:
        bot.edit_message_text(chat_id=message.chat.id, message_id=status_message.message_id, text=f"❌ Ошибка ИИ: {ai_response['error']}")
        return

    try:
        txt_file, xlsx_file = file_generator.generate_files(ai_response, base_name=f"смета_{message.chat.id}")
        bot.edit_message_text(chat_id=message.chat.id, message_id=status_message.message_id, text="✅ Смета готова! Отправляю...")
        
        with open(txt_file, "rb") as txt, open(xlsx_file, "rb") as xlsx:
            bot.send_document(message.chat.id, txt)
            bot.send_document(message.chat.id, xlsx)
            
        if os.path.exists(txt_file): os.remove(txt_file)
        if os.path.exists(xlsx_file): os.remove(xlsx_file)
    except Exception as e:
        bot.edit_message_text(chat_id=message.chat.id, message_id=status_message.message_id, text=f"❌ Ошибка файлов: {str(e)}")

# 3. Запуск всего приложения
if __name__ == "__main__":
    # Запускаем веб-сервер в отдельном фоновом потоке
    server_thread = threading.Thread(target=run_web_server)
    server_thread.daemon = True
    server_thread.start()
    
    # Запускаем опрос Telegram (с автоматическим пропуском старых апдейтов, чтобы убрать ошибку 409)
    bot.remove_webhook()
    bot.infinity_polling(skip_pending=True)
    
