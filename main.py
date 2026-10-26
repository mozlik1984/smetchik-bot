import os
import threading
from flask import Flask
import telebot
import config
import ai_service
import file_generator

# 1. За заглушка веб-сервера для работы на бесплатном тарифе Render Web Service
app = Flask(__name__)

@app.route('/')
def health_check():
    return "Bot is alive!", 200

def run_web_server():
    # Render автоматически передает порт в переменную PORT
    port = int(os.environ.get("PORT", 8080))
    # Запускаем сервер на 0.0.0.0, чтобы Render снаружи видел его
    app.run(host="0.0.0.0", port=port)

# 2. Инициализация Telegram бота по токену из конфига
bot = telebot.TeleBot(config.BOT_TOKEN)

def get_price_list_content():
    """Считывает прайс-лист из локального текстового файла проекта."""
    file_name = "price_list.txt"
    if os.path.exists(file_name):
        with open(file_name, "r", encoding="utf-8") as f:
            return f.read()
    return "Прайс-лист пуст или отсутствует на сервере."

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    welcome_text = (
        "👋 Приветствую! Я ваш автоматический бот-сметчик.\n\n"
        "📥 **Как составить смету:**\n"
        "Отправьте мне прямую ссылку на дизайн-проект, загруженный в Google Диск.\n\n"
        "⚠️ Убедитесь, что доступ к файлу открыт для всех по ссылке («Все, у кого есть ссылка» в режиме читателя)."
    )
    bot.reply_to(message, welcome_text, parse_mode="Markdown")

@bot.message_handler(func=lambda message: True)
def handle_project_link(message):
    user_text = message.text.strip()
    
    # Проверка на наличие маркера Google Диска в ссылке
    if config.GOOGLE_DRIVE_MARKER not in user_text:
        bot.reply_to(
            message, 
            "❌ Это не похоже на ссылку Google Диска. Пожалуйста, отправьте корректную ссылку на файл проекта."
        )
        return
        
    status_message = bot.reply_to(
        message, 
        "⏳ **Ссылка принята!**\nАнализирую проект и сопоставляю с прайс-листом. Это занимает около 1 минуты, пожалуйста, подождите..."
    )
    
    # Читаем локальный прайс-лист
    price_list = get_price_list_content()
    
    # Отправляем запрос в нейросеть
    ai_response = ai_service.analyze_project_with_ai(user_text, price_list)
    
    # Проверяем, вернулась ли техническая ошибка API
    if isinstance(ai_response, dict) and "error" in ai_response:
        bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=status_message.message_id,
            text=f"❌ Ошибка ИИ:\n`{ai_response['error']}`",
            parse_mode="Markdown"
        )
        return

    # Проверяем на пустой ответ от ИИ (если сметные строки не сгенерировались)
    if not ai_response or len(ai_response) == 0:
        bot.edit_message_text(
            chat_id=message.chat.id, 
            message_id=status_message.message_id, 
            text="⚠️ ИИ вернул пустой результат.\n\nВозможные причины:\n1. Доступ к файлу по ссылке закрыт.\n2. В файле прайс-листа `price_list.txt` нет данных."
        )
        return

    # Генерация файлов (.txt и .xlsx)
    try:
        txt_file, xlsx_file = file_generator.generate_files(ai_response, base_name=f"смета_{message.chat.id}")
        
        bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=status_message.message_id,
            text="✅ **Смета успешно сформирована!**\nОтправляю документы в чат..."
        )
        
        # Отправка документов пользователю
        with open(txt_file, "rb") as txt, open(xlsx_file, "rb") as xlsx:
            bot.send_document(message.chat.id, txt, caption="📄 Текстовый вариант сметы")
            bot.send_document(message.chat.id, xlsx, caption="📊 Таблица Excel со всеми расчетами")
            
        # Удаляем временные файлы с сервера после отправки
        if os.path.exists(txt_file): os.remove(txt_file)
        if os.path.exists(xlsx_file): os.remove(xlsx_file)
            
    except Exception as e:
        bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=status_message.message_id,
            text=f"❌ Ошибка при сборке файлов сметы: {str(e)}"
        )

# 3. Точка входа приложения
if __name__ == "__main__":
    # Запуск веб-сервера Flask в фоновом потоке для прохождения проверок портов Render
    server_thread = threading.Thread(target=run_web_server)
    server_thread.daemon = True
    server_thread.start()
    
    # Сброс старых вебхуков и запуск бесконечного цикла прослушивания
    bot.remove_webhook()
    bot.infinity_polling(skip_pending=True)
    
