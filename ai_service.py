import requests
import json
import config

def analyze_project_file_with_ai(file_path, price_list_text):
    """
    Отправляет физический файл проекта и текст прайса в нейросеть.
    """
    headers = {
        "Authorization": f"Bearer {config.OPENAI_API_KEY}"
    }
    
    prompt = (
        "Ты — опытный инженер-сметчик в сфере отделки и ремонта.\n"
        "Внимательно изучи прикрепленный PDF-файл дизайн-проекта.\n\n"
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
    
    # Формируем multipart/form-data запрос для передачи файла вместе с промптом
    # Для ProxyAPI/OpenAI мы передаем параметры модели в секцию data, а файл в files
    data = {
        "model": "gpt-4o",
        "messages": json.dumps([
            {"role": "system", "content": "Ты сметный калькулятор. Отвечаешь строго валидным JSON-массивом без Markdown."},
            {"role": "user", "content": prompt}
        ]),
        "temperature": "0.1"
    }
    
    try:
        with open(file_path, "rb") as f:
            files = {
                "file": (os.path.basename(file_path), f, "application/pdf")
            }
            
            response = requests.post(
                config.AI_COMPLETIONS_URL, 
                headers=headers, 
                data=data, 
                files=files,
                timeout=150
            )
        
        if response.status_code == 200:
            raw_content = response.json()["choices"]["message"]["content"].strip()
            if raw_content.startswith("```"):
                raw_content = raw_content.strip("```").strip("json").strip()
            
            return json.loads(raw_content)
        else:
            return {"error": f"API Error {response.status_code}: {response.text}"}
            
    except Exception as e:
        return {"error": str(e)}
        
