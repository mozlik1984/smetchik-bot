import os
import telebot
import config
import ai_service
import file_generator

# Инициализируем бота по токену из переменных окружения
bot = telebot.TeleBot(config.BOT_TOKEN)

def get_price_list_content():
    """Безопасно считывает прайс-лист из локального текстового файла."""
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
        "Отправьте мне прямую ссылку на дизайн-проект, загруженный в Google Диск или Google Документы.\n\n"
        "⚠️ Убедитесь, что доступ к файлу по ссылке открыт для всех (читатель/редактор), чтобы нейросеть смогла его изучить."
    )
    bot.reply_to(message, welcome_text, parse_mode="Markdown")

@bot.message_handler(func=lambda message: True)
def handle_project_link(message):
    user_text = message.text.strip()
    
    # Строгая проверка: содержит ли сообщение маркер Google Диска/Документов из config.py
    if config.GOOGLE_DRIVE_MARKER not in user_text:
        bot.reply_to(
            message, 
            "❌ Это не похоже на ссылку Google Диска. Пожалуйста, отправьте корректную ссылку на проект."
        )
        return
        
    status_message = bot.reply_to(
        message, 
        "⏳ **Ссылка принята!**\nСчитываю прайс-лист и передаю проект нейросети на анализ. Это может занять до 1-2 минут, пожалуйста, подождите..."
    )
    
    # 1. Читаем прайс-лист
    price_list = get_price_list_content()
    
    # 2. Отправляем данные в нейросеть через наш сервис
    ai_response = ai_service.analyze_project_with_ai(user_text, price_list)
    
    # Проверяем, вернулась ли ошибка при запросе
    if isinstance(ai_response, dict) and "error" in ai_response:
        bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=status_message.message_id,
            text=f"❌ Произошла ошибка при анализе ИИ:\n`{ai_response['error']}`",
            parse_mode="Markdown"
        )
        return

    # 3. Генерируем файлы сметы (.txt и .xlsx)
    try:
        txt_file, xlsx_file = file_generator.generate_files(ai_response, base_name=f"смета_{message.chat.id}")
        
        bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=status_message.message_id,
            text="✅ **Смета успешно сформирована!**\nОтправляю готовые документы..."
        )
        
        # 4. Отправляем файлы пользователю в чат
        with open(txt_file, "rb") as txt, open(xlsx_file, "rb") as xlsx:
            bot.send_document(message.chat.id, txt, caption="📄 Смета в текстовом формате")
            bot.send_document(message.chat.id, xlsx, caption="📊 Смета в формате Excel таблицы")
            
        # Зачищаем временные файлы с диска после отправки для экономии места
        if os.path.exists(txt_file): os.remove(txt_file)
        if os.path.exists(xlsx_file): os.remove(xlsx_file)
            
    except Exception as e:
        bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=status_message.message_id,
            text=f"❌ Ошибка генерации или отправки файлов сметы: {str(e)}"
        )

if __name__ == "__main__":
    # Запуск бесконечного цикла прослушивания бота
    bot.infinity_polling()
    
