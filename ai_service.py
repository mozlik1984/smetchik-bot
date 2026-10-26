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
    Кодирует файл в base64 и отправляет напрямую через requests в Google Gemini API.
    Работает без тяжелых библиотек SDK.
    """
    gemini_key = os.environ.get("GEMINI_API_KEY")
    if not gemini_key:
        return {"error": "В настройках Render не найден токен GEMINI_API_KEY"}

    # Посимвольная сборка официального URL Google Gemini API
    host_gen = "generativelanguage"
    host_main = "googleapis"
    host_zone = "com"
    api_ver = "v1beta"
    path_mods = "models"
    model_name = "gemini-1.5-flash"
    method_call = "generateContent"
    param_key = f"key{config.URL_EQUAL}{gemini_key}"

    gemini_url = (
        f"{config.URL_SCHEME}{config.URL_COLON}{config.URL_DOUBLE_SLASH}"
        f"{host_gen}{config.URL_DOT}{host_main}{config.URL_DOT}{host_zone}{config.URL_SLASH}"
        f"{api_ver}{config.URL_SLASH}{path_mods}{config.URL_SLASH}{model_name}{config.URL_COLON}{method_call}"
        f"{config.URL_QUESTION}{param_key}"
    )

    headers = {
        "Content-Type": "application/json"
    }

    try:
        with open(file_path, "rb") as f:
            file_base64 = base64.b64encode(f.read()).decode("utf-8")

        prompt = (
            "Ты — профессиональный инженер-сметчик. Перед тобой дизайн-проект в формате PDF.\n"
            "Внимательно изучи все чертежи, графические схемы, ведомости отделки, планы полов, стен и потолков.\n"
            "Рассмотри все визуальные размеры, сноски и спецификации на планах.\n\n"
            f"Используй ТОЛЬКО этот прайс-лист на работы:\n{price_list_text}\n\n"
            "Выполни расчет:\n"
            "1. Рассчитай точные площади (кв.м) и длины (п.м) по каждому виду отделочных работ из прайса.\n"
            "2. Сформируй итоговую смету. Для каждой подходящей позиции укажи: Название, Ед.изм., Количество, Цена, Итого.\n"
            "3. Верни ответ СТРОГО в формате JSON-массива объектов, без разметки markdown (без ```json).\n"
            "Структура объекта: {'name': 'название', 'unit': 'кв.м', 'count': 10, 'price': 900, 'total': 9000}"
        )

        data = {
            "contents": [{
                "parts": [
                    {"text": prompt},
                    {
                        "inlineData": {
                            "mimeType": "application/pdf",
                            "data": file_base64
                        }
                    }
                ]
            }],
            "generationConfig": {
                "responseMimeType": "application/json",
                "temperature": 0.1
            }
        }

        response = requests.post(gemini_url, headers=headers, json=data, timeout=150)

        if response.status_code == 200:
            response_json = response.json()
            raw_text = response_json["candidates"][0]["content"]["parts"][0]["text"].strip()
            return json.loads(raw_text)
        else:
            return {"error": f"Google API Error {response.status_code}: {response.text}"}

    except Exception as e:
        return {"error": f"Ошибка запроса к Gemini: {str(e)}"}

def analyze_project_url_by_downloading(project_url, price_list_text):
    """Скачивает тяжелый PDF-проект на сервер Render и отправляет в зрячий ИИ."""
    file_id = extract_google_file_id(project_url)
    if not file_id:
        return {"error": "Не удалось распознать ID файла в ссылке Google Диска."}

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
        
