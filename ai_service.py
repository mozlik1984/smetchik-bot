import base64
import json
import asyncio
import aiohttp
from config import AI_COMPLETION_URL, OPENAI_API_KEY
from database import load_price_list

def encode_image_to_base64(image_path: str) -> str:
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")

async def analyze_project_page(image_path: str) -> dict:
    current_prices = load_price_list()
    
    # Собираем список СТРОГО русских названий работ для ИИ
    russian_names = []
    for item in current_prices.values():
        russian_names.append(f"- '{item['name']}'")
        
    if not russian_names:
        russian_names = ["Vysokokachestvennoe vyravnivanie sten shtukaturnym sostavom po mayakam"]

    price_list_context = "\n".join(russian_names)

    system_prompt = (
        "You are an expert construction estimation engineer. Analyze the provided Russian blueprint or table image.\n"
        "Your task is to find finishing works, descriptions, or materials and their exact quantities (volumes, areas, counts).\n\n"
        "CRITICAL MATCHING RULE:\n"
        "You must strictly match the extracted works with the allowed Russian names from this list:\n"
        f"{price_list_context}\n\n"
        "Use your professional engineering logic to find synonyms. For example, if you see 'shtukaturnye raboty' or 'shkaturka', map it to 'Высококачественное выравнивание стен штукатурным составом по маякам'.\n"
        "If you see quartzvinyl or laminat floor layouts, map it to 'Укладка напольного покрытия (ламинат / кварцвинил) замковым способом' or kleyevym.\n\n"
        "OUTPUT FORMAT:\n"
        "1. Return output STRICTLY as a valid JSON object.\n"
        "2. The KEY must be the EXACT 'Russian Name' from the allowed list above. Do not modify the name string!\n"
        "3. The VALUE must be a number (float or integer) representing the total quantity found.\n"
        "4. If no matching data is found on this page, return an empty JSON object: {}\n"
        "Example response:\n"
        '{"Высококачественное выравнивание стен штукатурным составом по маякам": 120.5}'
    )

    try:
        base64_image = encode_image_to_base64(image_path)
    except Exception as e:
        print(f"Error base64: {e}")
        return {}

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {OPENAI_API_KEY}"
    }

    payload = {
        "model": "gpt-4o",
        "response_format": {"type": "json_object"},
        "messages": [
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Extract finishing volumes from this blueprint image and map them to the allowed Russian names."
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_image}"
                        }
                    }
                ]
            }
        ],
        "temperature": 0.0
    }

    timeout = aiohttp.ClientTimeout(total=60)

    async with aiohttp.ClientSession(timeout=timeout) as session:
        try:
            await asyncio.sleep(1.0)
            async with session.post(AI_COMPLETION_URL, headers=headers, json=payload) as response:
                if response.status == 200:
                    result = await response.json()
                    content = result["choices"]["message"]["content"]
                    return json.loads(content)
                else:
                    return {}
        except Exception as e:
            return {}
            
