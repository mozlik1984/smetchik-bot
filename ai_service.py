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
    Передает прямую ссылку скачивания чертежей в зрячую модель gpt-4o-mini через ProxyAPI.
    Модель сама визуально сканирует документ, находит выноски, инсталляции и закладные.
    """
    file_id = extract_google_file_id(project_url)
    if not file_id:
        return {"error": "Не удалось распознать ID файла в ссылке."}
        
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
        "Ты — профессиональный инженер-сметчик в отделке и ремонте.\n"
        "Перед тобой полноценный дизайн-проект в прикрепленном файле.\n"
        "Внимательно изучи все чертежи, графические схемы, планы полов/стен/потолка и спецификации.\n"
        "Рассмотри все визуальные комментарии дизайнера, стрелочки и выноски (наличие фанерных закладных, усиление профилей под инсталляции, скрытые ниши для штор, двери invisible).\n"
        "Если на плане указан натяжной потолок, а из ГКЛ делаются только скрытые ниши — считай ГКЛ строго в погонных метрах ниш, не раздувай смету на всю площадь.\n\n"
        f"Используй исключительно этот прайс-лист на работы:\n{price_list_text}\n\n"
        "Выполни расчет:\n"
        "1. Рассчитай точные площади (кв.м), длины (п.м) и количество (шт) по каждой подходящей позиции из прайса.\n"
        "2. Сформируй смету строго в формате JSON-массива объектов, без разметки markdown (без ```json).\n"
        "Формат ответа: [{\"name\": \"название\", \"unit\": \"кв.м\", \"count\": 10, \"price\": 900, \"total\": 9000}]"
    )
    
    data = {
        "model": "openai/gpt-4o-mini", # Подключаем экономичную зрячую модель
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": download_url # Передаем прямую ссылку на графику PDF
                        }
                    }
                ]
            }
        ],
        "temperature": 0.1
    }
    
    try:
        response = requests.post(config.AI_COMPLETIONS_URL, headers=headers, json=data, timeout=150)
        
        if response.status_code == 200:
            response_json = response.json()
            raw_content = response_json["choices"][0]["message"]["content"].strip()
            
            if raw_content.startswith("```"):
                raw_content = raw_content.strip("```").strip("json").strip()
            return json.loads(raw_content)
        else:
            return {"error": f"API Error {response.status_code}: {response.text}"}
    except Exception as e:
        return {"error": f"Ошибка мультимодального анализа: {str(e)}"}
        
