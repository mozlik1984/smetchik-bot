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
    """
    Загружает файл в хранилище ProxyAPI, проводит визуальный анализ чертежей
    через gpt-4o-mini и зачищает за собой облако.
    """
    if not config.OPENAI_API_KEY:
        return {"error": "В настройках Render не найден токен OPENAI_API_KEY"}

    # Сборка базовых URL посимвольно для ProxyAPI
    base_url_files = f"{config.URL_SCHEME}{config.URL_COLON}{config.URL_DOUBLE_SLASH}api{config.URL_DOT}proxyapi{config.URL_DOT}ru{config.URL_SLASH}v1{config.URL_SLASH}files"
    
    headers_auth = {
        "Authorization": f"Bearer {config.OPENAI_API_KEY}"
    }

    try:
        # 1. Загружаем файл в облако OpenAI/ProxyAPI через Files API
        with open(file_path, "rb") as f:
            files_data = {
                "file": (os.path.basename(file_path), f, "application/pdf")
            }
            data_purpose = {
                "purpose": "assistants"  # Назначение для обработки документов
            }
            
            upload_response = requests.post(base_url_files, headers=headers_auth, files=files_data, data=data_purpose, timeout=60)
            
        if upload_response.status_code != 200:
            return {"error": f"Ошибка загрузки файла в ИИ: {upload_response.text}"}
            
        file_id = upload_response.json().get("id")

        # 2. Формируем запрос на анализ содержимого
        prompt = (
            "Ты — опытный инженер-сметчик в отделке и ремонте.\n"
            "Перед тобой дизайн-проект в прикрепленном PDF-файле.\n"
            "Внимательно изучи чертежи, графические схемы, планы полов/стен/потолка и спецификации.\n"
            "Рассмотри все визуальные комментарии дизайнера, стрелочки и выноски (наличие фанерных закладных, усиление профилей под инсталляции, скрытые ниши для штор, двери invisible).\n"
            "Если на плане указан натяжной потолок, а из ГКЛ делаются только скрытые ниши — считай ГКЛ строго в погонных метрах ниш, не раздувай смету на всю площадь.\n\n"
            f"Используй исключительно этот прайс-лист на работы:\n{price_list_text}\n\n"
            "Выполни расчет:\n"
            "1. Рассчитай точные площади (кв.м), длины (п.м) и количество (шт) по каждой подходящей позиции из прайса.\n"
            "2. Сформируй смету строго в формате JSON-массива объектов, без разметки markdown (без ```json).\n"
            "Формат ответа: [{\"name\": \"название\", \"unit\": \"кв.м\", \"count\": 10, \"price\": 900, \"total\": 9000}]"
        )

        headers_chat = {
            "Authorization": f"Bearer {config.OPENAI_API_KEY}",
            "Content-Type": "application/json"
        }

        # Передаем файл через секцию контента
        chat_data = {
            "model": "openai/gpt-4o-mini",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "file",
                            "file": {
                                "file_id": file_id
                            }
                        }
                    ]
                }
            ],
            "temperature": 0.1
        }

        response = requests.post(config.AI_COMPLETIONS_URL, headers=headers_chat, json=chat_data, timeout=150)

        # 3. Зачищаем файл из облака ИИ сразу после ответа, чтобы не платить за хранение
        delete_url = f"{base_url_files}{config.URL_SLASH}{file_id}"
        requests.delete(delete_url, headers=headers_auth, timeout=20)

        if response.status_code == 200:
            raw_content = response.json()["choices"][0]["message"]["content"].strip()
            if raw_content.startswith("```"):
                raw_content = raw_content.strip("```").strip("json").strip()
            return json.loads(raw_content)
        else:
            return {"error": f"API Error {response.status_code}: {response.text}"}

    except Exception as e:
        return {"error": f"Ошибка мультимодального анализа: {str(e)}"}

def analyze_project_url_by_downloading(project_url, price_list_text):
    file_id = extract_google_file_id(project_url)
    if not file_id:
        return {"error": "Не удалось распознать ID файла в ссылке."}
        
    download_url = (
        f"{config.API_GOOGLE_UC}{config.URL_QUESTION}"
        f"{config.PARAM_EXPORT_DOWNLOAD}{config.URL_AND}"
        f"id{config.URL_EQUAL}{file_id}"
    )

    os.makedirs("temp", exist_ok=True)
    temp_download_path = f"temp/downloaded_{file_id}.pdf"
    
    try:
        # Скачиваем файл силами сервера Render напрямую
        with requests.get(download_url, stream=True, timeout=60) as r:
            if r.status_code != 200:
                return {"error": f"Не удалось скачать файл с Google Диска. Статус: {r.status_code}."}
            with open(temp_download_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
                    
        # Запускаем локальный анализ загруженного файла
        result = analyze_project_file_with_ai(temp_download_path, price_list_text)
        
        if os.path.exists(temp_download_path):
            os.remove(temp_download_path)
        return result
        
    except Exception as e:
        if os.path.exists(temp_download_path):
            os.remove(temp_download_path)
        return {"error": str(e)}
        
