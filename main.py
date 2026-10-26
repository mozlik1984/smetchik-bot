import os
import threading
from flask import Flask
import telebot
import config
import ai_service
import file_generator

app = Flask(__name__)

@app.route('/')
def health_check():
    return "Bot is alive!", 200

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

bot = telebot.TeleBot(config.BOT_TOKEN)

def get_price_list_content():
    file_name = "price_list.txt"
    if os.path.exists(file_name):
        with open(file_name, "r", encoding="utf-8") as f:
            return f.read()
    return "Прайс-лист пуст."

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    welcome_text = (
        "🏗️ **Бот запущен в тестовом режиме DeepSeek!**\n\n"
        "📥 Отправьте мне параметры объекта обычным текстом, и я соберу для вас Excel.\n"
        "**Пример текста:**\n"
        "`Площадь пола 50 кв.м, площадь стен 120 кв.м, дверей скрытых 4 шт`"
    )
    bot.reply_to(message, welcome_text, parse_mode="Markdown")

@bot.message_handler(func=lambda message: True)
def handle_text_data(message):
    user_text = message.text.strip()
    
    if config.TEXT_DATA_MARKER not in user_text.lower():
        bot.reply_to(message, "❌ Пожалуйста, укажите параметры объекта (например: Площадь пола...)")
        return
        
    status_message = bot.reply_to(message, "⏳ Передаю параметры в DeepSeek. Формирую Excel...")
    
    price_list = get_price_list_content()
    ai_response = ai_service.analyze_project_text_with_deepseek(user_text, price_list)
    
    if isinstance(ai_response, dict) and "error" in ai_response:
        bot.edit_message_text(chat_id=message.chat.id, message_id=status_message.message_id, text=f"❌ Ошибка: {ai_response['error']}")
        return

    try:
        txt_file, xlsx_file = file_generator.generate_files(ai_response, base_name=f"тест_смета_{message.chat.id}")
        bot.edit_message_text(chat_id=message.chat.id, message_id=status_message.message_id, text="✅ Таблица Excel успешно собрана!")
        
        with open(txt_file, "rb") as txt, open(xlsx_file, "rb") as xlsx:
            bot.send_document(message.chat.id, txt, caption="📄 Текстовая смета")
            bot.send_document(message.chat.id, xlsx, caption="📊 Готовый Excel файл")
            
        if os.path.exists(txt_file): os.remove(txt_file)
        if os.path.exists(xlsx_file): os.remove(xlsx_file)
    except Exception as e:
        bot.edit_message_text(chat_id=message.chat.id, message_id=status_message.message_id, text=f"❌ Ошибка генерации файлов: {str(e)}")

if __name__ == "__main__":
    server_thread = threading.Thread(target=run_web_server)
    server_thread.daemon = True
    server_thread.start()
    bot.remove_webhook()
    bot.infinity_polling(skip_pending=True)
    
