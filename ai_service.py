import requests
import json
import os
import config

def analyze_project_text_with_deepseek(user_text, price_list_text):
    """
    Отправляет текстовые параметры объекта и прайс-лист в модель DeepSeek.
    """
    headers = {
        "Authorization": f"Bearer {config.OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    
    prompt = (
        "Ты — профессиональный инженер-сметчик в сфере отделки и ремонта.\n"
        "Перед тобой текстовые параметры объекта (площади отделки, объемы, количество элементов):\n"
        f"=== ПАРАМЕТРЫ ОБЪЕКТА ===\n{user_text}\n=========================\n\n"
        f"Используй исключительно этот прайс-лист на строительные работы:\n{price_list_text}\n\n"
        "Твоя задача:\n"
        "1. Внимательно сопоставь переданные параметры объекта со строками из предоставленного прайс-листа.\n"
        "2. Посчитай объемы работ, подставь цены из прайса и рассчитай итоговую стоимость по каждой позиции.\n"
        "3. Верни ответ СТРОГО в формате JSON-массива объектов, без разметки markdown (без ```json).\n\n"
        "Формат объектов в массиве:\n"
        "[{\"name\": \"название работы\", \"unit\": \"кв.м\", \"count\": 50, \"price\": 900, \"total\": 45000}]\n"
        "В ответе должен быть ТОЛЬКО чистый JSON, без лишних фраз до или после."
    )
    
    data = {
        "model": "deepseek/deepseek-v4.1-flash",
        "messages": [
            {"role": "system", "content": "Ты сметный калькулятор. Отвечаешь строго валидным JSON-массивом."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.1
    }
    
    try:
        response = requests.post(config.AI_COMPLETIONS_URL, headers=headers, json=data, timeout=60)
        
        if response.status_code == 200:
            response_json = response.json()
            # Исправлено: Считываем через индекс choices[0] для OpenAI/ProxyAPI формата
            raw_content = response_json["choices"][0]["message"]["content"].strip()
            
            if raw_content.startswith("```"):
                raw_content = raw_content.strip("```").strip("json").strip()
            return json.loads(raw_content)
        else:
            return {"error": f"API Error {response.status_code}: {response.text}"}
    except Exception as e:
        return {"error": f"Ошибка сети DeepSeek: {str(e)}"}

def analyze_project_file_with_ai(file_path, price_list_text):
    """Заглушка для сохранения структуры проекта"""
    return {"error": "В тестовом режиме файлы не принимаются. Отправьте параметры текстом."}

def analyze_project_url_by_downloading(project_url, price_list_text):
    """Заглушка для сохранения структуры проекта"""
    return {"error": "В тестовом режиме ссылки не принимаются. Отправьте параметры текстом."}
    
