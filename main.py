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
    return "Прайс-лист пуст или отсутствует."

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    welcome_text = (
        "👋 **Приветствую! Я ваш автоматический бот-сметчик.**\n\n"
        "📥 **Как составить смету:**\n"
        "1. Отправьте мне **PDF-файл** дизайн-проекта прямо в чат (если он весит меньше 20 МБ).\n"
        "2. Если файл крупный (больше 20 МБ), загрузите его на Google Диск и **отправьте ссылку** сюда. "
        "Убедитесь, что доступ по ссылке открыт («Все, у кого есть ссылка»)."
    )
    bot.reply_to(message, welcome_text, parse_mode="Markdown")

# Обработчик входящих файлов/документов
@bot.message_handler(content_types=['document'])
def handle_project_document(message):
    file_name = message.document.file_name
    if not file_name.lower().endswith('.pdf'):
        bot.reply_to(message, "❌ Пожалуйста, отправьте проект в формате PDF.")
        return
        
    # Проверяем размер файла на стороне Telegram до скачивания
    if message.document.file_size > 20 * 1024 * 1024:
        bot.reply_to(
            message, 
            "⚠️ **Файл слишком большой (> 20 МБ)!**\n"
            "Telegram запрещает ботам скачивать файлы такого размера напрямую.\n\n"
            "👉 Пожалуйста, загрузите этот PDF на Google Диск и пришлите мне текстовую ссылку на него."
        )
        return
        
    status_message = bot.reply_to(message, "⏳ **Файл получен!** Передаю в нейросеть для анализа...")
    
    os.makedirs("temp", exist_ok=True)
    local_pdf_path = f"temp/{message.document.file_id}.pdf"
    
    try:
        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        with open(local_pdf_path, "wb") as f:
            f.write(downloaded_file)
            
        price_list = get_price_list_content()
        ai_response = ai_service.analyze_project_file_with_ai(local_pdf_path, price_list)
        
        if os.path.exists(local_pdf_path): os.remove(local_pdf_path)
        
        process_ai_result(message, status_message, ai_response)
            
    except Exception as e:
        if os.path.exists(local_pdf_path): os.remove(local_pdf_path)
        bot.edit_message_text(chat_id=message.chat.id, message_id=status_message.message_id, text=f"❌ Ошибка: {str(e)}")

# Обработчик входящих ссылок
@bot.message_handler(func=lambda message: True)
def handle_text_links(message):
    user_text = message.text.strip()
    
    if config.GOOGLE_DRIVE_MARKER not in user_text:
        bot.reply_to(message, "❌ Отправьте PDF-файл или корректную ссылку на Google Диск.")
        return
        
    status_message = bot.reply_to(message, "⏳ **Ссылка принята!** Загружаю большой PDF на сервер и отправляю в ИИ...")
    price_list = get_price_list_content()
    
    # Отправляем ссылку в обновленный сервис, который скачает файл
    ai_response = ai_service.analyze_project_url_by_downloading(user_text, price_list)
    
    process_ai_result(message, status_message, ai_response)

def process_ai_result(message, status_message, ai_response):
    """Общая функция для генерации файлов и отправки пользователю"""
    if isinstance(ai_response, dict) and "error" in ai_response:
        bot.edit_message_text(chat_id=message.chat.id, message_id=status_message.message_id, text=f"❌ Ошибка ИИ:\n`{ai_response['error']}`", parse_mode="Markdown")
        return

    if not ai_response:
        bot.edit_message_text(chat_id=message.chat.id, message_id=status_message.message_id, text="⚠️ ИИ вернул пустой результат.")
        return

    try:
        txt_file, xlsx_file = file_generator.generate_files(ai_response, base_name=f"смета_{message.chat.id}")
        bot.edit_message_text(chat_id=message.chat.id, message_id=status_message.message_id, text="✅ **Смета успешно сформирована!**")
        
        with open(txt_file, "rb") as txt, open(xlsx_file, "rb") as xlsx:
            bot.send_document(message.chat.id, txt, caption="📄 Смета TXT")
            bot.send_document(message.chat.id, xlsx, caption="📊 Смета Excel")
            
        if os.path.exists(txt_file): os.remove(txt_file)
        if os.path.exists(xlsx_file): os.remove(xlsx_file)
    except Exception as e:
        bot.edit_message_text(chat_id=message.chat.id, message_id=status_message.message_id, text=f"❌ Ошибка файлов: {str(e)}")

if __name__ == "__main__":
    server_thread = threading.Thread(target=run_web_server)
    server_thread.daemon = True
    server_thread.start()
    bot.remove_webhook()
    bot.infinity_polling(skip_pending=True)
    
