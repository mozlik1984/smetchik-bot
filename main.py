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
from calculator import calculate_project_estimate

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

async def run_full_pipeline(file_path: str, safe_filename: str, message: types.Message, status_message: types.Message):
    try:
        await status_message.edit_text("🔄 **Проект успешно скачан.** Начинаю постраничную конвертацию в изображения...")
        image_paths = convert_pdf_to_images(file_path)
        
        if not image_paths:
            await status_message.edit_text("❌ Ошибка конвертации PDF. Убедитесь, что файл не поврежден.")
            return

        await status_message.edit_text(f"🧠 Найдено страниц: {len(image_paths)}. Подключаю ИИ-Vision для сканирования...")
        total_extracted_volumes = {}

        for index, img_path in enumerate(image_paths):
            await status_message.edit_text(f"👁 Анализирую страницу {index + 1} из {len(image_paths)}...")
            page_data = await analyze_project_page(img_path)
            
            if page_data:
                for service_key, volume in page_data.items():
                    if service_key in total_extracted_volumes:
                        total_extracted_volumes[service_key] += volume
                    else:
                        total_extracted_volumes[service_key] = volume

        if not total_extracted_volumes:
            await status_message.edit_text("ℹ ИИ завершил анализ, но не обнаружил подходящих ведомостей отделки.")
            return

        await status_message.edit_text("🧮 Почти готово! Рассчитываю стоимость по прайс-листу...")

        project_name = os.path.splitext(safe_filename)[0]
        estimate_result = calculate_project_estimate(total_extracted_volumes, project_name)
        
        await status_message.delete()
        
        total_sum_formatted = f"{estimate_result['total_sum']:,.2f}"
        await message.answer(
            f"🎉 **Анализ проекта успешно завершен!**\n\n"
            f"💰 **Общая стоимость работ по прайсу:** {total_sum_formatted} руб.\n\n"
            f"👇 Ниже прикреплены подробные файлы сметы для печати и редактирования."
        )
        
        txt_file = types.FSInputFile(estimate_result["txt_file_path"])
        await message.answer_document(document=txt_file, caption="📄 Детальная смета (.txt)")
        
        excel_file = types.FSInputFile(estimate_result["excel_file_path"])
        await message.answer_document(document=excel_file, caption="📊 Таблица Excel с формулами (.xlsx)")

    except Exception as e:
        error_details = traceback.format_exc()
        await status_message.edit_text(f"❌ Ошибка в конвейере сметчика:\n```\n{error_details}\n```", parse_mode="Markdown")

@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    await message.answer(
        "👋 Рад приветствовать! Я специализированный ИИ-сметчик.\n\n"
        "📥 **Отправьте мне файл дизайн-проекта в формате PDF** (до 20 МБ).\n\n"
        "🔗 Если ваш файл **крупнее 20 МБ**, загрузите его на Google Диск, откройте публичный доступ и **отправьте мне ссылку**!"
    )

@dp.message(F.document & (F.document.mime_type == "application/pdf"))
async def handle_pdf_document(message: types.Message, bot: Bot):
    document = message.document
    status_message = await message.answer("🔄 **Файл получен.** Скачиваю проект через Telegram...")
    safe_filename = "".join([c for c in document.file_name if c.isalpha() or c.isdigit() or c in "._- "])
    file_path = os.path.join(DOWNLOADS_DIR, safe_filename)
    
    try:
        file_info = await bot.get_file(document.file_id)
        await bot.download_file(file_info.file_path, file_path)
        await run_full_pipeline(file_path, safe_filename, message, status_message)
    except Exception as e:
        await status_message.edit_text(f"❌ Ошибка Telegram API: {e}")

@dp.message(F.text & (F.text.contains("http://") | F.text.contains("https://")))
async def handle_pdf_link(message: types.Message):
    raw_url = message.text.strip()
    status_message = await message.answer("🌐 **Ссылка получена.** Проверяю облачный диск...")
    
    try:
        direct_url = convert_to_direct_download_url(raw_url)
        safe_filename = f"project_{message.from_user.id}.pdf"
        file_path = os.path.join(DOWNLOADS_DIR, safe_filename)
        
        headers = {"User-Agent": "Mozilla/5.0"}
        timeout = aiohttp.ClientTimeout(total=300, connect=30)
        
        async with aiohttp.ClientSession(headers=headers, timeout=timeout) as session:
            await status_message.edit_text("📥 Скачиваю тяжелый файл на сервер...")
            async with session.get(direct_url) as response:
                if response.status == 200:
                    with open(file_path, "wb") as f:
                        f.write(await response.read())
                    await run_full_pipeline(file_path, safe_filename, message, status_message)
                else:
                    await status_message.edit_text(f"❌ Не удалось скачать файл. Код сервера: {response.status}")
    except Exception as e:
        error_details = traceback.format_exc()
        await status_message.edit_text(f"❌ Ошибка сетевого скачивания:\n```\n{error_details}\n```", parse_mode="Markdown")

async def main():
    bot = Bot(token=BOT_TOKEN)
    # КРИТИЧЕСКАЯ МЕТЛА: drop_pending_updates=True наглухо вышибает зависшие сессии с Amvera
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
    
