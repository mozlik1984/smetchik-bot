import requests
import json
import config

def convert_google_drive_link(url):
    """
    Превращает обычную ссылку Google Диска в ссылку для прямого скачивания файла,
    чтобы нейросеть скачивала сам PDF, а не веб-интерфейс Google.
    """
    if "://google.com" in url:
        # Извлекаем ID файла из ссылки
        parts = url.split('/')
        for i, part in enumerate(parts):
            if part == 'd' and i + 1 < len(parts):
                file_id = parts[i+1].split('?')[0]
                # Формируем прямую ссылку для скачивания документа
                return f"https://://google.com/uc?export=download&id={file_id}"
    return url

def analyze_project_with_ai(project_url, price_list_text):
    headers = {
        "Authorization": f"Bearer {config.OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    
    # Конвертируем ссылку в прямую для скачивания
    direct_download_url = convert_google_drive_link(project_url)
    
    prompt = (
        f"Ты — опытный инженер-сметчик в сфере отделки и ремонта.\n"
        f"Внимательно изучи PDF-файл дизайн-проекта по этой прямой ссылке: {direct_download_url}\n\n"
        f"Используй ТОЛЬКО этот прайс-лист на строительные работы:\n{price_list_text}\n\n"
        "Твоя задача:\n"
        "1. Найди в проекте ведомости отделки, планы полов, стен и потолков.\n"
        "2. Рассчитай точные площади (кв.м) или погонные метры (п.м) по каждой подходящей позиции из прайса.\n"
        "3. Подставь цены и посчитай итоговую стоимость.\n"
        "4. Верни ответ СТРОГО в формате JSON-массива объектов.\n\n"
        "Формат объектов в массиве:\n"
        "[{\"name\": \"название\", \"unit\": \"кв.м\", \"count\": 50, \"price\": 900, \"total\": 45000}]\n"
        "В ответе должен быть ТОЛЬКО чистый JSON, без текста до или после, без разметки ```json."
    )
    
    data = {
        "model": "gpt-4o",
        "messages": [
            {"role": "system", "content": "Ты сметный калькулятор. Отвечаешь строго валидным JSON-массивом без Markdown."},
            {"role": "user", "content": prompt}
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
        
