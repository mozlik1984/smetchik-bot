import base64
import requests
import json
import config

def analyze_project_file_with_ai(file_path, price_list_text):
    """
    Кодирует локальный PDF-файл в base64 и отправляет его вместе с прайсом в ИИ.
    """
    headers = {
        "Authorization": f"Bearer {config.OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    
    try:
        # Читаем PDF файл и переводим его в строку base64
        with open(file_path, "rb") as f:
            pdf_base64 = base64.b64encode(f.read()).decode("utf-8")
            
        # Строгий промпт для сметных расчетов
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
        
        # Передаем PDF через официальный формат file_data для gpt-4o
        data = {
            "model": "gpt-4o",
            "messages": [
                {
                    "role": "system", 
                    "content": "Ты сметный калькулятор. Отвечаешь строго валидным JSON-массивом без Markdown."
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt
                        },
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
        
        # Отправка запроса на ваш стабильный посимвольный URL
        response = requests.post(
            config.AI_COMPLETIONS_URL, 
            headers=headers, 
            json=data, 
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
        return {"error": f"Ошибка в ai_service: {str(e)}"}
        
