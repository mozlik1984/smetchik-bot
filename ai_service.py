import base64
import requests
import json
import os
import io
import pdfplumber
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
    Конвертирует листы чертежей PDF в RGB-картинки и отправляет их в gpt-4o-mini с жестким промптом.
    """
    headers = {
        "Authorization": f"Bearer {config.OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }

    try:
        # Усиленный сметный промпт (убирает галлюцинации ИИ)
        prompt_text = (
            "Ты — строгий и точный инженер-сметчик. Перед тобой графические листы дизайн-проекта.\n"
            "Твоя задача — составить смету СТРОГО на основе тех объемов и комментариев, которые физически нарисованы или написаны на чертежах.\n\n"
            "ПРАВИЛА АНАЛИЗА:\n"
            "1. НЕ придумывай работы от себя. Если в проекте потолок натяжной — НЕ закладывай сплошную штукатурку/шпаклевку потолка из ГКЛ.\n"
            "2. Внимательно читай текстовые сноски со стрелочками на планах стен и перегородок. Найди места, где дизайнер пишет: 'закладная из фанеры', 'скрытая дверь Invisible', 'усиление инсталляции'.\n"
            "3. Объемы (кв.м, п.м, шт) бери исключительно из экспликаций помещений и ведомостей отделки на листах.\n\n"
            f"Используй ТОЛЬКО этот прайс-лист на строительные работы:\n{price_list_text}\n\n"
            "Верни ответ СТРОГО в формате JSON-массива объектов, без разметки markdown (без ```json).\n"
            "Формат ответа: [{\"name\": \"название работы строго из прайса\", \"unit\": \"кв.м\", \"count\": 10, \"price\": 900, \"total\": 9000}]"
        )

        content_parts = [{"type": "text", "text": prompt_text}]

        with pdfplumber.open(file_path) as pdf:
            max_pages = min(len(pdf.pages), 15)
            for i in range(max_pages):
                page = pdf.pages[i]
                
                pix = page.to_image(resolution=100)
                pil_img = pix.original
                
                if pil_img.mode != "RGB":
                    pil_img = pil_img.convert("RGB")
                
                img_buffer = io.BytesIO()
                pil_img.save(img_buffer, format="JPEG", quality=60)
                img_bytes = img_buffer.getvalue()
                
                img_base64 = base64.b64encode(img_bytes).decode("utf-8")
                
                content_parts.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{img_base64}"
                    }
                })

        data = {
            "model": "openai/gpt-4o-mini",
            "messages": [
                {
                    "role": "user",
                    "content": content_parts
                }
            ],
            "temperature": 0.05  # Снижаем температуру до минимума для максимальной точности расчетов
        }

        response = requests.post(config.AI_COMPLETIONS_URL, headers=headers, json=data, timeout=160)

        if response.status_code == 200:
            response_json = response.json()
            
            choices = response_json.get("choices", [])
            if not choices or not isinstance(choices, list):
                return {"error": f"Неверная структура ответа API: {response.text}"}
                
            first_choice = choices[0]
            message = first_choice.get("message", {})
            raw_content = message.get("content", "").strip()
            
            if raw_content.startswith("```"):
                raw_content = raw_content.strip("```").strip("json").strip()
            return json.loads(raw_content)
        else:
            return {"error": f"API Error {response.status_code}: {response.text}"}

    except Exception as e:
        return {"error": f"Ошибка зрячего анализа чертежей: {str(e)}"}

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
        
        if os.path.exists(temp_download_path):
            os.remove(temp_download_path)
        return result
        
    except Exception as e:
        if os.path.exists(temp_download_path):
            os.remove(temp_download_path)
        return {"error": f"Ошибка при загрузке по ссылке: {str(e)}"}
        
