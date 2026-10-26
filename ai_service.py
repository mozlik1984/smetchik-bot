import requests
import json
import os
import config

def extract_google_file_id(url):
    """
    Безопасно извлекает ID файла без текстовых литералов в коде.
    """
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
    """Заглушка для сохранения структуры проекта"""
    return {"error": "Пожалуйста, используйте отправку ссылок на Google Диск."}

def analyze_project_url_by_downloading(project_url, price_list_text):
    """
    Передает прямую ссылку на PDF-чертежи во флагманскую зрячую модель Gemini 1.5 Pro.
    ИИ анализирует графику, выноски, комментарии и считает точную смету.
    """
    file_id = extract_google_file_id(project_url)
    if not file_id:
        return {"error": "Не удалось распознать ID файла в ссылке Google Диска."}
        
    download_url = (
        f"{config.API_GOOGLE_UC}{config.URL_QUESTION}"
        f"{config.PARAM_EXPORT_DOWNLOAD}{config.URL_AND}"
        f"id{config.URL_EQUAL}{file_id}"
    )

    # Заголовки для авторизации в OpenRouter
    headers = {
        "Authorization": f"Bearer {config.OPENAI_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": f"{config.URL_SCHEME}{config.URL_COLON}{config.URL_DOUBLE_SLASH}localhost"
    }
    
    prompt = (
        "Ты — высококлассный инженер-сметчик в сфере отделки и ремонта квартир.\n"
        "Перед тобой полноценный дизайн-проект в прикрепленном PDF-файле.\n"
        "Твоя задача — провести детальный визуальный анализ всех листов проекта. Изучи чертежи, графические схемы, ведомости отделки, планы полов, стен и потолков.\n"
        "Внимательно рассмотри все визуальные комментарии дизайнера, стрелочки и сноски на планах (наличие фанерных закладных, усиление инсталляций, скрытые ниши для штор, двери invisible).\n"
        "Если на плане указан натяжной потолок, а из ГКЛ делаются только ниши для гардин — считай ГКЛ строго в погонных метрах ниш, не раздувай смету на всю площадь.\n\n"
        f"Используй исключительно этот прайс-лист на строительные работы:\n{price_list_text}\n\n"
        "Выполни расчет:\n"
        "1. Рассчитай точные площади (кв.м), длины (п.м) и количество (шт) по каждой подходящей позиции из прайса.\n"
        "2. Сформируй смету строго в формате JSON-массива объектов, без разметки markdown (без ```json).\n"
        "Формат ответа: [{\"name\": \"название работы\", \"unit\": \"кв.м\", \"count\": 10, \"price\": 900, \"total\": 9000}]"
    )
    
    data = {
        # Подключаем флагманскую зрячую модель с огромным контекстом
        "model": "google/gemini-1.5-pro",
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
        "temperature": 0.15
    }
    
    try:
        response = requests.post(config.AI_COMPLETIONS_URL, headers=headers, json=data, timeout=180)
        
        if response.status_code == 200:
            raw_content = response.json()["choices"][0]["message"]["content"].strip()
            if raw_content.startswith("```"):
                raw_content = raw_content.strip("```").strip("json").strip()
            return json.loads(raw_content)
        else:
            return {"error": f"API Error {response.status_code}: {response.text}"}
    except Exception as e:
        return {"error": f"Ошибка мультимодального анализа: {str(e)}"}
        
