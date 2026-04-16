import os
import re
import pytesseract
from PIL import Image
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

async def handle_project(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file = await (update.message.photo[-1].get_file() if update.message.photo else update.message.document.get_file())
    file_path = "local_plan.jpg"
    await file.download_to_drive(file_path)
    
    await update.message.reply_text("🔎 Включаю внутренний сканер (без интернета)...")

    try:
        # Прямое чтение текста внутри сервера
        text = pytesseract.image_to_string(Image.open(file_path), lang='rus+eng')
        
        # Ищем цифры (площади и размеры)
        areas = re.findall(r'(\d+[.,]\d+)', text)
        sizes = re.findall(r'\b(\d{4})\b', text)

        res = "✅ **Локальный обсчёт:**\n\n"
        
        valid_areas = [a for a in areas if 2.0 < float(a.replace(',', '.')) < 150.0]
        if valid_areas:
            res += f"📐 Площади: {', '.join(valid_areas)} м²\n"
        
        if sizes:
            m_sizes = [float(s)/1000 for s in sizes]
            unique_s = list(set(m_sizes))
            perim = sum(unique_s)
            res += f"🧱 Размеры стен: {', '.join(map(str, sorted(unique_s)))} м\n"
            res += f"🏃 **Периметр: {perim:.2f} м**\n"
            res += f"🎨 **Стены (h=2.7): {perim * 2.7:.2f} м²**"
        
        if not valid_areas and not sizes:
            res = "Не увидел цифр. Возможно, чертеж слишком мелкий или темный."

        await update.message.reply_text(res, parse_mode='Markdown')

    except Exception as e:
        await update.message.reply_text(f"Ошибка сканера: {e}\n\nПохоже, Amvera не установила tesseract-ocr через apt.")
    finally:
        if os.path.exists(file_path): os.remove(file_path)

if __name__ == '__main__':
    TOKEN = "8693522094:AAFv_YYf1bxLrslkhawmEhSujTUdOr75dTM"
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.PHOTO | filters.Document.IMAGE, handle_project))
    app.run_polling()
