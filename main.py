import asyncio
import logging
import os
import aiohttp
import traceback
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart

from config import (
    BOT_TOKEN, 
    DOWNLOADS_DIR,
    PRICE_LIST_PATH,
    GOOGLE_DOWNLOAD_BASE,
    GOOGLE_DRIVE_MARKER
)
from ai_service import analyze_project_via_link

logging.basicConfig(level=logging.INFO)
dp = Dispatcher()

def convert_to_direct_download_url(url: str) -> str:
    url = url.strip()
    if GOOGLE_DRIVE_MARKER in url:
        marker = "/file/d/"
        start_idx = url.find(marker)
        if start_idx != -1:
            id_start = start_idx + len(marker)
            tail = url[id_start:]
            end_idx = tail.find("/")
            if end_idx == -1:
                end_idx = tail.find("?")
            file_id = tail[:end_idx] if end_idx != -1 else tail
            if file_id:
                return f"{GOOGLE_DOWNLOAD_BASE}{file_id}"
    return url

@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    await message.answer(
        "👋 Рад приветствовать! Я специализированный ИИ-сметчик.\n\n"
        "🔗 Загрузите ваш дизайн-проект в формате PDF на Google Диск, откройте доступ по ссылке и **отправьте ссылку мне**.\n"
        "Я передам её нейросети вместе с прайс-листом и пришлю вам готовый детальный отчет!"
    )

@dp.message(F.text & (F.text.contains("http://") | F.text.contains("https://")))
async def handle_link(message: types.Message):
    raw_url = message.text.strip()
    status_message = await message.answer("🧠 **Ссылка получена.** Преобразую в поток данных и отправляю в ИИ OpenAI...")
    
    try:
        # Переводим ссылку в формат прямого скачивания файла для ИИ
        direct_url = convert_to_direct_download_url(raw_url)

        # Читаем наш полный русский прайс-лист из корня
        price_list_content = ""
        if os.path.exists(PRICE_LIST_PATH):
            with open(PRICE_LIST_PATH, "r", encoding="utf-8") as f:
                price_list_content = f.read()
                
        if not price_list_content:
            await status_message.edit_text("❌ Ошибка: Не найден файл price_list.txt в корне проекта.")
            return

        # Делаем сквозной запрос в ИИ
        ai_response = await analyze_project_via_link(direct_url, price_list_content)
        
        await status_message.delete()
        
        # Отправляем текстовый отчет сметы прямо в чат
        await message.answer(ai_response)
        
        # Создаем файлы отчета на лету
        txt_path = os.path.join(DOWNLOADS_DIR, f"estimate_{message.from_user.id}.txt")
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(ai_response)
            
        txt_file = types.FSInputFile(txt_path)
        await message.answer_document(document=txt_file, caption="📄 Файл сметы (.txt)")

    except Exception as e:
        error_details = traceback.format_exc()
        await status_message.edit_text(f"❌ Ошибка конвейера:\n```\n{error_details}\n```", parse_mode="Markdown")

async def main():
    bot = Bot(token=BOT_TOKEN)
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
    
