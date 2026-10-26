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
    Анализирует чертежи в высоком качестве с жестким требованием 
    структуры ответа через JSON Mode.
    """
    headers = {
        "Authorization": f"Bearer {config.OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }

    try:
        prompt_text = (
            "Ты — высококлассный инженер-сметчик с глубоким пониманием строительных чертежей.\n"
            "Перед тобой графические листы дизайн-проекта. Проведи точный визуальный анализ каждого листа.\n\n"
            "ЖЕСТКИЕ ПРАВИЛА РАСЧЕТА:\n"
            "1. Ищи сложные, оригинальные отделочные работы строго из прайса. Если на планах и развертках стен указан 'полный пирог под покраску', 'крупноформатный керамогранит', 'авторские обои' или 'скрытые двери Invisible' — подставляй именно их с точными площадями. НЕ упрощай до стандартных работ!\n"
            "2. Внимательно читай текстовые сноски, спецификации Архикада и мелкие комментарии со стрелочками. Найди скрытые ниши для штор, инсталляции с усилением профиля и фанерные закладные под мебель/ТВ.\n"
            "3. НЕ придумывай объемы из головы. Если на плане потолок указан как натяжной, а ГКЛ используется локально только для скрытых шторных ниш — считай ГКЛ строго в погонных метрах ниш, НЕ раздувай ГКЛ на всю площадь потолка.\n\n"
            f"Используй исключительно этот прайс-лист на строительные работы:\n{price_list_text}\n\n"
            "Верни ответ строго в формате JSON-массива объектов. Никакого текста до или после массива быть не должно.\n"
            "Формат ответа: [{\"name\": \"точное название работы из прайса\", \"unit\": \"кв.м\", \"count\": 10, \"price\": 900, \"total\": 9000}]"
        )

        content_parts = [{"type": "text", "text": prompt_text}]

        with pdfplumber.open(file_path) as pdf:
            total_pages = len(pdf.pages)
            
            # Диапазон сметных листов чертежей (с 6 по 16 страницу)
            start_page = min(5, total_pages - 1)
            end_page = min(15, total_pages)
            
            if start_page >= end_page or total_pages <= 5:
                start_page = 0
                end_page = min(total_pages, 8)
                
            for i in range(start_page, end_page):
                page = pdf.pages[i]
                
                pix = page.to_image(resolution=120)
                pil_img = pix.original
                
                if pil_img.mode != "RGB":
                    pil_img = pil_img.convert("RGB")
                
                img_buffer = io.BytesIO()
                pil_img.save(img_buffer, format="JPEG", quality=70)
                img_bytes = img_buffer.getvalue()
                
                img_base64 = base64.b64encode(img_bytes).decode("utf-8")
                
                content_parts.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{img_base64}"
                    }
                })

        data = {
            "model": "openai/gpt-4o",
            "messages": [
                {
                    "role": "user",
                    "content": content_parts
                }
            ],
            # ИСПРАВЛЕНО: Принудительный режим JSON Mode на уровне ядра OpenAI
            "response_format": {"type": "json_object"},
            "temperature": 0.05
        }

        response = requests.post(config.AI_COMPLETIONS_URL, headers=headers, json=data, timeout=160)

        if response.status_code == 200:
            response_json = response.json()
            choices = response_json.get("choices", [])
            if not choices or not isinstance(choices, list) or len(choices) == 0:
                return {"error": f"Неверная структура ответа API: {response.text}"}
                
            first_choice = choices[0]
            message = first_choice.get("message", {})
            raw_content = message.get("content", "").strip()
            
            # Исправлено: если JSON пришел обернутым в объект ответа, извлекаем сам массив
            parsed_json = json.loads(raw_content)
            if isinstance(parsed_json, dict) and "estimate" in parsed_json:
                return parsed_json["estimate"]
            if isinstance(parsed_json, dict) and not isinstance(parsed_json, list):
                # Если модель вернула объект со списком внутри, берем первый попавшийся массив
                for key, val in parsed_json.items():
                    if isinstance(val, list):
                        return val
            return parsed_json
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
        
