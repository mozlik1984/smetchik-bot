import base64
import requests
import json
import os
from pdf2image import convert_from_path
from PIL import Image
import config

def extract_google_file_id(url):
    if config.GOOGLE_DRIVE_MARKER not in url:
        return None
    try:
        if config.PATH_MARKER_FILE_D in url:
            start = url.find(config.PATH_MARKER_FILE_D) + len(config.PATH_MARKER_FILE_D)
            end = url.find(config.URL_SLASH, start)
            if end == -1: end = url.find(config.URL_QUESTION, start)
            return url[start:] if end == -1 else url[start:end]
        elif config.PARAM_ID_EQUAL in url:
            start = url.find(config.PARAM_ID_EQUAL) + len(config.PARAM_ID_EQUAL)
            end = url.find(config.URL_AND, start)
            return url[start:] if end == -1 else url[start:end]
    except Exception:
        return None
    return None

def analyze_project_file_with_ai(file_path, price_list_text):
    """
    Нарезает PDF на сжатые картинки и отправляет их в недорогую gpt-4o-mini.
    Это экономит баланс и позволяет ИИ видеть все выноски и закладные.
    """
    headers = {
        "Authorization": f"Bearer {config.OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    
    os.makedirs("temp/images", exist_ok=True)
    
    try:
        # Конвертируем страницы PDF в картинки с невысоким DPI для экономии токенов
        pages = convert_from_path(file_path, dpi=100)
        
        all_items = []
        
        # Перебираем страницы проекта
        for page_num, page in enumerate(pages):
            img_path = f"temp/images/page_{page_num}.jpg"
            # Сжимаем качество картинки до 70%, чтобы запрос стоил копейки
            page.save(img_path, "JPEG", quality=70)
            
            with open(img_path, "rb") as f:
                img_base64 = base64.b64encode(f.read()).decode("utf-8")
            
            prompt = (
                f"Ты — опытный инженер-сметчик. Изучи этот лист дизайн-проекта (Страница {page_num + 1}).\n"
                "Внимательно рассмотри чертеж, все выноски, комментарии дизайнера (например, про закладные, инсталляции, усиления) и ведомости.\n\n"
                f"Используй этот прайс-лист:\n{price_list_text}\n\n"
                "Найди работы с этого листа, посчитай их точные объемы и верни ответ СТРОГО в формате JSON-массива объектов.\n"
                "Если на этом листе нет отделочных работ из прайса, верни просто пустой массив [].\n"
                "Формат: [{\"name\": \"название\", \"unit\": \"кв.м\", \"count\": 10, \"price\": 900, \"total\": 9000}]"
            )
            
            data = {
                "model": "gpt-4o-mini", # Экономичная зрячая модель
                "messages": [
                    {"role": "system", "content": "Ты сметный калькулятор. Отвечаешь только чистым JSON-массивом."},
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:image/jpeg;base64,{img_base64}"}
                            }
                        ]
                    }
                ],
                "temperature": 0.1
            }
            
            response = requests.post(config.AI_COMPLETIONS_URL, headers=headers, json=data, timeout=60)
            
            if response.status_code == 200:
                raw_content = response.json()["choices"]["message"]["content"].strip()
                if raw_content.startswith("```"):
                    raw_content = raw_content.strip("```").strip("json").strip()
                
                try:
                    page_data = json.loads(raw_content)
                    if isinstance(page_data, list):
                        all_items.extend(page_data)
                except Exception:
                    pass
            
            # Удаляем отработанную картинку листа
            if os.path.exists(img_path): os.remove(img_path)
            
        return all_items
        
    except Exception as e:
        return {"error": f"Ошибка анализа страниц: {str(e)}"}

def analyze_project_url_by_downloading(project_url, price_list_text):
    file_id = extract_google_file_id(project_url)
    if not file_id:
        return {"error": "Не удалось распознать ID файла."}
        
    download_url = (
        f"{config.API_GOOGLE_UC}{config.URL_QUESTION}"
        f"{config.PARAM_EXPORT_DOWNLOAD}{config.URL_AND}"
        f"id{config.URL_EQUAL}{file_id}"
    )
    
    os.makedirs("temp", exist_ok=True)
    temp_download_path = f"temp/downloaded_{file_id}.pdf"
    
    try:
        with requests.get(download_url, stream=True, timeout=60) as r:
            if r.status_code != 200:
                return {"error": f"Не удалось скачать файл. Статус: {r.status_code}."}
            with open(temp_download_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
                    
        result = analyze_project_file_with_ai(temp_download_path, price_list_text)
        
        if os.path.exists(temp_download_path): os.remove(temp_download_path)
        return result
        
    except Exception as e:
        if os.path.exists(temp_download_path): os.remove(temp_download_path)
        return {"error": str(e)}
        
