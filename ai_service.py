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
    Интеллектуально отбирает только целевые листы с развертками, плинтусами и штукатуркой,
    отправляя в gpt-4o компактный и точный визуальный пакет.
    """
    headers = {
        "Authorization": f"Bearer {config.OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }

    try:
        prompt_text = (
            "Ты — высококлассный инженер-сметчик с глубоким пониманием сложных строительных чертежей.\n"
            "Перед тобой графические листы дизайн-проекта. Проведи точный визуальный анализ каждого листа.\n\n"
            "ЖЕСТКИЕ ПРАВИЛА РАСЧЕТА:\n"
            "1. Ищи сложные, оригинальные отделочные работы строго из прайса. Особое внимание обрати на: 'полный пирог под покраску', 'штукатурка стен', 'плинтус скрытого монтажа', 'откосы', 'демонтаж/монтаж перегородок', 'крупноформатный керамогранит', 'авторские обои' и 'скрытые двери Invisible'. Подставляй именно их с точными объемами. НЕ упрощай до стандартных отделочных работ!\n"
            "2. Внимательно читай текстовые сноски, спецификации Архикада на развертках стен и мелкие комментарии со стрелочками. Найди скрытые ниши для штор, инсталляции с усилением профиля и фанерные закладные под мебель/ТВ.\n"
            "3. Скрупулезно проанализируй ведомости отделки и экспликации помещений. Суммируй площади стен, полов и погонаж плинтусов со всех чертежей.\n\n"
            f"Используй исключительно этот прайс-лист на строительные работы:\n{price_list_text}\n\n"
            "Верни ответ СТРОГО в формате JSON-объекта, содержащего ключ \"estimate\", в котором лежит массив сметных позиций.\n"
            "Пример структуры ответа:\n"
            "{\n"
            "  \"estimate\": [\n"
            "    {\"name\": \"точное название работы из прайса\", \"unit\": \"кв.м\", \"count\": 10, \"price\": 900, \"total\": 9000}\n"
            "  ]\n"
            "}"
        )

        content_parts = [{"type": "text", "text": prompt_text}]
        
        # Ключевые слова для интеллектуального поиска скрытых отделочных работ на листах
        keywords = ["развертк", "ведомост", "экспликац", "план стен", "план полов", "плинтус", "покраск", "штукатур", "демонтаж"]

        with pdfplumber.open(file_path) as pdf:
            pages_to_send = []
            
            # Умный постраничный отбор листов
            for page in pdf.pages:
                text = page.extract_text() or ""
                text_lower = text.lower()
                
                # Если лист содержит чертежную сметную информацию
                if any(kw in text_lower for kw in keywords):
                    pages_to_send.append(page)
            
            # Защита: если чертежи сохранены в кривых и текст не извлекся, берем ключевой диапазон разверток (с 15 по 25 листы)
            if not pages_to_send:
                total = len(pdf.pages)
                pages_to_send = pdf.pages[min(14, total-1):min(25, total)]
            
            # Жестко ограничиваем до 8 самых информативных страниц для стабильности шлюза
            final_pages = pages_to_send[:8]

            for page in final_pages:
                pix = page.to_image(resolution=130)
                pil_img = pix.original
                
                if pil_img.mode != "RGB":
                    pil_img = pil_img.convert("RGB")
                
                img_buffer = io.BytesIO()
                pil_img.save(img_buffer, format="JPEG", quality=75)
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
            
            if raw_content.startswith("```"):
                raw_content = raw_content.strip("```").strip("json").strip()
                
            parsed_json = json.loads(raw_content)
            
            if isinstance(parsed_json, dict) and "estimate" in parsed_json:
                return parsed_json["estimate"]
                
            if isinstance(parsed_json, dict):
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
        
