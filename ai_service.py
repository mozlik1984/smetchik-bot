import base64
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
            if end == -1:
                end = url.find(config.URL_QUESTION, start)
            if end == -1:
                return url[start:]
            return url[start:end]
            
        elif config.PARAM_ID_EQUAL in url:
            start = url.find(config.PARAM_ID_EQUAL) + len(config.PARAM_ID_EQUAL)
            end = url.find(config.URL_AND, start)
            if end == -1:
                return url[start:]
            return url[start:end]
    except Exception:
        return None
    return None

def analyze_project_file_with_ai(file_path, price_list_text):
    """
    Кодирует PDF-файл в base64 и бесплатно отправляет его в OpenRouter.
    """
    headers = {
        "Authorization": f"Bearer {config.OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    
    try:
        with open(file_path, "rb") as f:
            pdf_base64 = base64.b64encode(f.read()).decode("utf-8")
            
        prompt = (
            "Ты — опытный инженер-сметчик в сфере отделки и ремонта.\n"
            "Внимательно изучи прикрепленный PDF-файл дизайн-проекта.\n\n"
            f"Используй ТОЛЬКО этот прайс-лист на строительные работы:\n{price_list_text}\n\n"
            "Твоя задача:\n"
            "1. Найди в проекте ведомости отделки, планы полов, стен и потолков.\n"
            "2. Рассчитай точные площади (кв.м) или погонные метры (п.м) по каждой подходящей позиции из прайса.\n"
            "3. Подставь цены из прайса и посчитай итоговую стоимость.\n"
            "4. Верни ответ СТРОГО в формате JSON-массива объектов.\n\n"
            "Формат объектов в массиве:\n"
            "[{\"name\": \"название\", \"unit\": \"кв.м\", \"count\": 50, \"price\": 900, \"total\": 45000}]\n"
            "В ответе должен быть ТОЛЬКО чистый JSON, без текста до или после, без разметки ```json."
        )
        
        data = {
            # Указываем точный бесплатный слаг модели, предложенный самим сервером
            "model": "meta-llama/llama-3.3-70b-instruct",
            "messages": [
                {
                    "role": "system", 
                    "content": "Ты сметный калькулятор. Отвечаешь строго валидным JSON-массивом без Markdown."
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "file",
                            "file": {
                                "filename": "project.pdf",
                                "file_data": pdf_base64
                            }
                        }
                    ]
                }
            ],
            "temperature": 0.1
        }
        
        response = requests.post(config.AI_COMPLETIONS_URL, headers=headers, json=data, timeout=150)
        
        if response.status_code == 200:
            raw_content = response.json()["choices"]["message"]["content"].strip()
            if raw_content.startswith("```"):
                raw_content = raw_content.strip("```").strip("json").strip()
            return json.loads(raw_content)
        else:
            return {"error": f"API Error {response.status_code}: {response.text}"}
            
    except Exception as e:
        return {"error": f"Ошибка в ai_service: {str(e)}"}

def analyze_project_url_by_downloading(project_url, price_list_text):
    """
    Скачивает большой файл по ссылке на сервер Render и отправляет в OpenRouter.
    """
    file_id = extract_google_file_id(project_url)
    if not file_id:
        return {"error": "Не удалось распознать ID файла в ссылке Google Диска. Убедитесь, что ссылка верная."}
        
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
                return {"error": f"Не удалось скачать файл. Статус: {r.status_code}. Проверьте доступ по ссылке."}
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
        
