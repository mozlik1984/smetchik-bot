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
    return {"error": "Пожалуйста, отправьте ссылку на Google Диск."}

def analyze_project_url_by_downloading(project_url, price_list_text):
    file_id = extract_google_file_id(project_url)
    if not file_id:
        return {"error": "Не удалось распознать ID файла."}
        
    download_url = (
        f"{config.API_GOOGLE_UC}{config.URL_QUESTION}"
        f"{config.PARAM_EXPORT_DOWNLOAD}{config.URL_AND}"
        f"id{config.URL_EQUAL}{file_id}"
    )

    # Исправленные заголовки авторизации для OpenRouter
    headers = {
        "Authorization": f"Bearer {config.OPENAI_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": f"{config.URL_SCHEME}{config.URL_COLON}{config.URL_DOUBLE_SLASH}localhost"
    }
    
    prompt = (
        "Ты — профессиональный инженер-сметчик. Перед тобой дизайн-проект в прикрепленном файле.\n"
        "Внимательно изучи все чертежи, графические схемы, выноски и спецификации. Рассмотри все визуальные комментарии дизайнера (про закладные, усиления профилей, инсталляции).\n\n"
        f"Используй исключительно этот прайс-лист на работы:\n{price_list_text}\n\n"
        "Выполни расчет:\n"
        "1. Рассчитай точные площади (кв.м) и длины (п.м) по каждому виду отделочных работ из прайса.\n"
        "2. Сформируй смету строго в формате JSON-массива объектов.\n"
        "Формат: [{\"name\": \"название\", \"unit\": \"кв.м\", \"count\": 10, \"price\": 900, \"total\": 9000}]"
    )
    
    data = {
        "model": "google/gemini-2.5-flash",
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": download_url
                        }
                    }
                ]
            }
        ],
        "temperature": 0.1
    }
    
    try:
        response = requests.post(config.AI_COMPLETIONS_URL, headers=headers, json=data, timeout=120)
        
        if response.status_code == 200:
            raw_content = response.json()["choices"]["message"]["content"].strip()
            if raw_content.startswith("```"):
                raw_content = raw_content.strip("```").strip("json").strip()
            return json.loads(raw_content)
        else:
            return {"error": f"API Error {response.status_code}: {response.text}"}
    except Exception as e:
        return {"error": str(e)}
        
