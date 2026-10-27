import requests
import json
import os
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
    return {"error": "Пожалуйста, используйте отправку ссылок на Google Диск."}

def analyze_project_url_by_downloading(project_url, price_list_text):
    """
    Прямой перенос ИИ-зрения в облако. Код шлет прямую ссылку на PDF проекта
    в gpt-4o. Модель сама открывает её внутри своего ядра без нагрузки на Render.
    """
    file_id = extract_google_file_id(project_url)
    if not file_id:
        return {"error": "Не удалось распознать ID файла в ссылке Google Диска."}
        
    download_url = (
        f"{config.API_GOOGLE_UC}{config.URL_QUESTION}"
        f"{config.PARAM_EXPORT_DOWNLOAD}{config.URL_AND}"
        f"id{config.URL_EQUAL}{file_id}"
    )

    headers = {
        "Authorization": f"Bearer {config.OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    
    prompt = (
        "Ты — высококлассный инженер-сметчик с глубоким пониманием сложных строительных чертежей.\n"
        "Перед тобой полноценный дизайн-проект в прикрепленном PDF-файле по ссылке.\n"
        "Проведи доскональный визуальный анализ всего альбома чертежей.\n\n"
        "ЖЕСТКИЕ ПРАВИЛА РАСЧЕТА:\n"
        "1. В НАЧАЛЕ АЛЬБОМА найди планы демонтажа и монтажа. Обязательно рассчитай объемы по позициям: 'демонтаж межкомнатных перегородок (ГКЛ/кирпич)', 'возведение новых перегородок', 'штукатурка стен по маякам'.\n"
        "2. Ищи сложные, оригинальные отделочные работы строго из прайса: 'полный пирог стен под покраску', 'плинтус скрытого монтажа', 'откосы', 'крупноформатный керамогранит', 'авторские обои' и 'скрытые двери Invisible'. Подставляй именно их с точными площадями и длинами.\n"
        "3. Внимательно читай текстовые сноски, спецификации Архикада на развертках стен и мелкие комментарии со стрелочками. Найди скрытые ниши для штор, инсталляции с усилением профиля и фанерные закладные под мебель/ТВ.\n"
        "4. НЕ придумывай объемы из головы. Если на плане потолок указан как натяжной, а ГКЛ используется локально только для скрытых шторных ниш — считай ГКЛ строго в погонных метрах ниш, НЕ раздувай ГКЛ на всю площадь потолка.\n\n"
        f"Используй исключительно этот прайс-лист на строительные работы:\n{price_list_text}\n\n"
        "Верни ответ СТРОГО в формате JSON-объекта, содержащего ключ \"estimate\", в котором лежит массив сметных позиций.\n"
        "Пример структуры ответа:\n"
        "{\n"
        "  \"estimate\": [\n"
        "    {\"name\": \"точное название работы из прайса\", \"unit\": \"кв.м\", \"count\": 10, \"price\": 900, \"total\": 9000}\n"
        "  ]\n"
        "}"
    )
    
    data = {
        "model": "openai/gpt-4o", # Старшая полноценная зрячая модель
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": download_url # Скармливаем прямую ссылку на чтение PDF
                        }
                    }
                ]
            }
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.05
    }
    
    try:
        response = requests.post(config.AI_COMPLETIONS_URL, headers=headers, json=data, timeout=170)
        
        if response.status_code == 200:
            response_json = response.json()
            choices = response_json.get("choices")
            if choices and isinstance(choices, list) and len(choices) > 0:
                first_choice = choices[0]
                message = first_choice.get("message", {})
                raw_content = message.get("content", "").strip()
                
                parsed_json = json.loads(raw_content)
                if isinstance(parsed_json, dict) and "estimate" in parsed_json:
                    return parsed_json["estimate"]
                if isinstance(parsed_json, dict):
                    for key, val in parsed_json.items():
                        if isinstance(val, list):
                            return val
                return parsed_json
            else:
                return {"error": "API вернул пустой список choices"}
        else:
            return {"error": f"API Error {response.status_code}: {response.text}"}
    except Exception as e:
        return {"error": f"Ошибка мультимодального анализа: {str(e)}"}
        
