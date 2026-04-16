import os
import re
import pytesseract
import fitz  # PyMuPDF
from PIL import Image, ImageOps, ImageEnhance
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
from flask import Flask
from threading import Thread

# --- ОБМАНКА ДЛЯ RENDER ---
app = Flask('')
@app.route('/')
def home(): return "Бот-сметчик в сети!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# --- ЛОГИКА БОТА ---
pytesseract.pytesseract.tesseract_cmd = '/usr/bin/tesseract'

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Определяем тип файла
    is_pdf = False
    if update.message.document and update.message.document.mime_type == 'application/pdf':
        file = await update.message.document.get_file()
        is_pdf = True
    elif update.message.photo:
        file = await update.message.photo[-1].get_file()
    else:
        file = await update.message.document.get_file()

    file_path = "temp_file"
    await file.download_to_drive(file_path)
    await update.message.reply_text("📂 Файл принят. Начинаю глубокое сканирование...")

    try:
        # Если PDF - конвертируем первую страницу в картинку
        if is_pdf:
            doc = fitz.open(file_path)
            page = doc.load_page(0)
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2)) # Увеличиваем четкость
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        else:
            img = Image.open(file_path)

        # --- УЛУЧШЕНИЕ КАРТИНКИ ---
        img = img.convert('L') # В черно-белый
        img = ImageOps.autocontrast(img)
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(2.0) # Задираем контраст

        # Распознавание
        text = pytesseract.image_to_string(img, lang='rus+eng')
        
        # Логика поиска цифр (площади и стены)
        areas = re.findall(r'(\d+[.,]\d+)', text)
        sizes = re.findall(r'\b(\d{4})\b', text)

        res = "✅ **Результат анализа:**\n\n"
        valid_areas = [a for a in areas if 1.5 < float(a.replace(',', '.')) < 250.0]
        if valid_areas:
            res += f"📐 Площади: {', '.join(valid_areas)} м²\n"
        
        if sizes:
            m_sizes = [float(s)/1000 for s in sizes]
            unique_s = list(set(m_sizes))
            perim = sum(unique_s)
            res += f"🧱 Стены (м): {', '.join(map(str, sorted(unique_s)))}\n"
            res += f"🏃 **Периметр: {perim:.2f} м**\n"
            res += f"🎨 **Шпаклевка (h=2.7): {perim * 2.7:.2f} м²**"

        await update.message.reply_text(res if (valid_areas or sizes) else "🤖 Не смог разобрать цифры. Попробуй скинуть PDF файлом или скриншот покрупнее.")

    except Exception as e:
        await update.message.reply_text(f"Ошибка: {e}")
    finally:
        if os.path.exists(file_path): os.remove(file_path)

if __name__ == '__main__':
    Thread(target=run_flask).start()
    TOKEN = "8693522094:AAFv_YYf1bxLrslkhawmEhSujTUdOr75dTM"
    bot = ApplicationBuilder().token(TOKEN).build()
    # Слушаем всё: фото и любые документы
    bot.add_handler(MessageHandler(filters.PHOTO | filters.Document.ALL, handle_document))
    bot.run_polling()
