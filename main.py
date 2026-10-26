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
    GOOGLE_DOWNLOAD_BASE, 
    GOOGLE_DRIVE_MARKER
)
from converter import convert_pdf_to_images
from ai_service import analyze_project_page

logging.basicConfig(level=logging.INFO)
dp = Dispatcher()

def convert_to_direct_download_url(url: str) -> str:
    url = url.strip()
    
    if GOOGLE_DRIVE_MARKER in url:
        marker = "/file/d/"
        start_idx = url.find(marker)
        if start_idx != -1:
            # Вырезаем строку начиная с ID
            id_start = start_idx + len(marker)
            tail = url[id_start:]
            
            # Находим конец ID перед следующим слэшем или вопросом
            end_idx = tail.find("/")
            if end_idx == -1:
                end_idx = tail.find("?")
                
            # Забираем чистый ID без использования списков и сплитов
            file_id = tail[:end_idx] if end_idx != -1 else tail
            if file_id:
                return f"{GOOGLE_DOWNLOAD_BASE}{file_id}"
    return url

async def run_full_pipeline(file_path: str, safe_filename: str, message: types.Message, status_message: types.Message):
    try:
        await status_message.edit_text("PDF downloaded. Converting pages...")
        image_paths = convert_pdf_to_images(file_path)
        
        if not image_paths:
            await status_message.edit_text("Error: PDF file is empty or corrupted.")
            return

        await status_message.edit_text(f"Pages: {len(image_paths)}. Connecting AI Vision...")
        
        # Для отладки берем строго первую страницу из созданного списка
        img_path = image_paths[0]
        
        await status_message.edit_text("Testing AI Vision on Page 1...")
        page_data = await analyze_project_page(img_path)
        debug_output = page_data.get("debug_text", "No debug text returned.")
        
        await status_message.delete()
        await message.answer(f"AI DIAGNOSTICS RESULT (Page 1):\n\n{debug_output}")

    except Exception as e:
        error_details = traceback.format_exc()
        await status_message.edit_text(f"Pipeline error:\n{error_details}")

@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    await message.answer("Welcome! Send me a Google Drive link.")

@dp.message(F.text & (F.text.contains("http://") | F.text.contains("https://")))
async def handle_pdf_link(message: types.Message):
    raw_url = message.text.strip()
    status_message = await message.answer("Checking link...")
    
    try:
        direct_url = convert_to_direct_download_url(raw_url)
        safe_filename = f"project_{message.from_user.id}.pdf"
        file_path = os.path.join(DOWNLOADS_DIR, safe_filename)
        
        headers = {"User-Agent": "Mozilla/5.0"}
        timeout = aiohttp.ClientTimeout(total=300, connect=30)
        
        async with aiohttp.ClientSession(headers=headers, timeout=timeout) as session:
            await status_message.edit_text("Downloading file...")
            async with session.get(direct_url) as response:
                if response.status == 200:
                    with open(file_path, "wb") as f:
                        f.write(await response.read())
                    await run_full_pipeline(file_path, safe_filename, message, status_message)
                else:
                    await status_message.edit_text(f"Download failed. Status: {response.status}")
    except Exception as e:
        error_details = traceback.format_exc()
        await status_message.edit_text(f"Network error:\n{error_details}")

async def main():
    bot = Bot(token=BOT_TOKEN)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
    
