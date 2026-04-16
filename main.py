import os
import re
import pytesseract
from PIL import Image
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

# --- НАСТРОЙКИ ДЛЯ RENDER.COM ---
# Указываем путь к исполняемому файлу Tesseract в Linux
pytesseract.pytesseract.tesseract_cmd = '/usr/bin/tesseract'

async def handle_project(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Пытаемся взять файл либо из фото, либо из документа
    if update.message.photo:
        file = await update.message.photo[-1].get_file()
    elif update.message.document:
        file = await update.message.document.get_file()
    else:
        return

    file_path = "plan_to_scan.jpg"
    await file.download_to_drive(file_path)
    
    await update.message.reply_text("🔎 Сканирую чертеж внутренним сканером (на Render)...")

    try:
        # Открываем изображение через Pillow
        img = Image.open(file_path)
        
        # Распознаем текст (используем русский и английский для цифр)
        # На Render мы установим пакеты rus и eng через Build Command
        text = pytesseract.image_to_string(img, lang='rus+eng')
        
        # 1. Ищем площади (например, 71.6 или 12,5)
        # Регулярка ищет цифры с точкой или запятой
        areas = re.findall(r'(\d+[.,]\d+)', text)
        
        # 2. Ищем размеры стен (обычно это четырехзначные числа в мм: 4415, 3440)
        wall_sizes = re.findall(r'\b(\d{4})\b', text)

        response = "📊 **Отчет по чертежу (Render ИИ):**\n\n"
        
        # Фильтруем площади (от 2 до 200 м2), чтобы не цеплять лишнее
        valid_areas = [a for a in areas if 2.0 < float(a.replace(',', '.')) < 200.0]
        
        if valid_areas:
            response += f"📐 Нашел площади (м²): {', '.join(valid_areas)}\n"
        
        if wall_sizes:
            # Переводим мм в метры
            walls_m = [float(w)/1000 for w in wall_sizes]
            # Убираем дубликаты, чтобы не считать одну стену дважды
            unique_walls = list(set(walls_m))
            perimeter = sum(unique_walls)
            
            response += f"🧱 Найденные стены (м): {', '.join(map(str, sorted(unique_walls)))}\n"
            response += f"🏃 **Примерный периметр: {perimeter:.2f} пог. м.**\n"
            
            # Стандартная высота потолка для отделочника (можно менять прямо тут)
            h = 2.7
            response += f"🎨 **Площадь стен (шпаклевка, h={h}м): {perimeter * h:.2f} м²**\n"
        
        if not valid_areas and not wall_sizes:
            response = "🤖 Текст нашел, но размеры не опознал. Попробуй сделать скриншот четче или обрезать лишние поля."
            # Для отладки можно добавить вывод распознанного текста:
            # response += f"\n\n(Тех.инфо: {text[:100]}...)"

        await update.message.reply_text(response, parse_mode='Markdown')

    except Exception as e:
        await update.message.reply_text(f"⚠️ Ошибка сканера: {e}\nПроверь установку tesseract в Build Command.")
    finally:
        # Удаляем временный файл, чтобы не занимать место
        if os.path.exists(file_path):
            os.remove(file_path)

if __name__ == '__main__':
    # ВСТАВЬ СВОЙ ТОКЕН НИЖЕ
    TOKEN = "8693522094:AAFv_YYf1bxLrslkhawmEhSujTUdOr75dTM"
    
    app = ApplicationBuilder().token(TOKEN).build()
    
    # Обрабатываем и сжатые фото, и картинки-файлы
    app.add_handler(MessageHandler(filters.PHOTO | filters.Document.IMAGE, handle_project))
    
    print("Бот-сметчик запущен на Render...")
    app.run_polling()
