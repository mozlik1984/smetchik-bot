import os
import re
import pytesseract
from PIL import Image
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
from flask import Flask
from threading import Thread

# --- ОБМАНКА ДЛЯ RENDER (чтобы не перезагружал) ---
app = Flask('')
@app.route('/')
def home(): return "Бот-сметчик в сети!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# --- ЛОГИКА БОТА ---
pytesseract.pytesseract.tesseract_cmd = '/usr/bin/tesseract'

async def handle_project(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.photo:
        file = await update.message.photo[-1].get_file()
    else:
        file = await update.message.document.get_file()
    
    file_path = "plan.jpg"
    await file.download_to_drive(file_path)
    await update.message.reply_text("🔎 Вижу чертеж, считаю объемы...")

    try:
        text = pytesseract.image_to_string(Image.open(file_path), lang='rus+eng')
        # Ищем цифры площадей и размеров
        areas = re.findall(r'(\d+[.,]\d+)', text)
        sizes = re.findall(r'\b(\d{4})\b', text)

        res = "✅ **Результат замера:**\n\n"
        valid_areas = [a for a in areas if 1.5 < float(a.replace(',', '.')) < 200.0]
        if valid_areas:
            res += f"📐 Найденные площади: {', '.join(valid_areas)} м²\n"
        
        if sizes:
            m_sizes = [float(s)/1000 for s in sizes]
            unique_s = list(set(m_sizes))
            perim = sum(unique_s)
            res += f"🧱 Стены (м): {', '.join(map(str, sorted(unique_s)))}\n"
            res += f"🏃 **Общий периметр: {perim:.2f} м**\n"
            res += f"🎨 **Стены (h=2.7м): {perim * 2.7:.2f} м²**"
        
        await update.message.reply_text(res if (valid_areas or sizes) else "Цифр не нашел, попробуй фото четче.")
    except Exception as e:
        await update.message.reply_text(f"Ошибка: {e}")
    finally:
        if os.path.exists(file_path): os.remove(file_path)

if __name__ == '__main__':
    # Запускаем обманку в фоне
    Thread(target=run_flask).start()
    # Запускаем бота
    TOKEN = "8693522094:AAFv_YYf1bxLrslkhawmEhSujTUdOr75dTM"
    bot = ApplicationBuilder().token(TOKEN).build()
    bot.add_handler(MessageHandler(filters.PHOTO | filters.Document.IMAGE, handle_project))
    bot.run_polling()
