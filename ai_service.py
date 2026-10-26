import requests
import json
import config

def analyze_project_with_ai(project_url, price_list_text):
    """
    Отправляет ссылку на дизайн-проект и текст прайса в нейросеть.
    Возвращает структурированный массив со сметой.
    """
    headers = {
        "Authorization": f"Bearer {config.OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    
    # Формируем жесткий и развернутый промпт для сметчика
    prompt = (
        f"Ты — опытный инженер-сметчик в сфере отделки и ремонта. "
        f"Проанализируй дизайн-проект, доступный по ссылке: {project_url}\n\n"
        f"Используй исключительно этот прайс-лист на работы:\n{price_list_text}\n\n"
        "Твоя задача:\n"
        "1. Внимательно изучить ведомости отделки, планы полов, стен и потолков в проекте.\n"
        "2. Найти и посчитать точные объемы работ: площади (кв.м) и длины (п.м) по каждой подходящей позиции из прайса.\n"
        "3. Подставить цены из предоставленного прайса и рассчитать общую стоимость по каждой строке.\n"
        "4. Сформировать смету и вернуть ответ СТРОГО в формате JSON-массива объектов.\n\n"
        "Каждый объект в массиве должен иметь следующие ключи:\n"
        "- 'name' (наименование работы)\n"
        "- 'unit' (ед. изм.: кв.м, п.м, шт.)\n"
        "- 'count' (рассчитанное количество, только число)\n"
        "- 'price' (цена из прайса, только число)\n"
        "- 'total' (итоговая стоимость по позиции, только число)\n\n"
        "В ответе не должно быть никакого текста, кроме чистого JSON-массива. Без разметки ```json."
    )
    
    data = {
        "model": "gpt-4o",  # gpt-4o отлично справляется с контекстом документов и ссылок
        "messages": [
            {"role": "system", "content": "Ты — сметный калькулятор. Выдаешь ответ только в формате JSON-массива без лишних слов."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.15  # Низкая температура для максимальной точности расчетов
    }
    
    try:
        # Отправляем запрос на наш посимвольно собранный URL
        response = requests.post(
            config.AI_COMPLETIONS_URL, 
            headers=headers, 
            json=data, 
            timeout=90  # Большой таймаут, так как анализ проекта занимает время
        )
        
        if response.status_code == 200:
            raw_content = response.json()["choices"][0]["message"]["content"].strip()
            # Очищаем от возможных случайных маркеров markdown, если ИИ их добавил
            if raw_content.startswith("```"):
                raw_content = raw_content.strip("```").strip("json").strip()
            
            # Проверяем, что это валидный JSON
            parsed_json = json.loads(raw_content)
            return parsed_json
        else:
            return {"error": f"API Error: {response.status_code} - {response.text}"}
            
    except Exception as e:
        return {"error": f"Ошибка при запросе к ИИ: {str(e)}"}
        
