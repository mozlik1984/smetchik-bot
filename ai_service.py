import base64
import json
import aiohttp
from config import AI_COMPLETION_URL, OPENAI_API_KEY
from database import load_price_list

def encode_image_to_base64(image_path: str) -> str:
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")

async def analyze_project_page(image_path: str) -> dict:
    # 1. Загружаем твой полный прайс со всеми 29 позициями динамически
    current_prices = load_price_list()
    
    # Формируем красивый список для ИИ, чтобы он видел русские названия и коды
    price_items_v2 = []
    for key, item in current_prices.items():
        price_items_v2.append(f"- Code: '{key}' | Name in Russian: '{item['name']}'")
        
    price_list_context = "\n".join(price_items_v2)

    # 2. Создаем гибкий промпт, который заставит ИИ сопоставлять данные с любым прайсом
    system_prompt = (
        "You are an expert construction estimation engineer. Analyze the provided Russian blueprint or table image.\n"
        "Your goal is to extract construction and finishing works, their quantities (volumes, areas, counts) and match them strictly to the items from the allowed price list below.\n\n"
        "ALLOWED PRICE LIST (Code and Russian Name):\n"
        f"{price_list_context}\n\n"
        "CRITICAL MAPPING & EXTRACTION RULES:\n"
        "1. Carefully read all tables, floor plans, keys, notes, and specifications in the image.\n"
        "2. Match the found Russian terms or synonyms with the 'Name in Russian' from the allowed list, then extract the corresponding 'Code'.\n"
        "3. For example, if you see wall painting or 'покраска стен' or 'стены под покраску', map it to code 'pie_sten_pod_pokrasku'.\n"
        "4. If you see tiles, 'керамогранит' or 'плитка 60х120', map it to code 'keramogranit_60x120'.\n"
        "5. If you see partitions or 'возведение перегородок', map it to code 'peregorodki_gkl'.\n"
        "6. Extract values as floating point numbers or integers. Do not include units (like m2, pcs) in values.\n\n"
        "OUTPUT FORMAT Rules:\n"
        "1. Return output STRICTLY as a valid JSON object.\n"
        "2. Key must be ONLY the technical 'Code' from the allowed list, value must be a number (volume, quantity).\n"
        "3. If no matching construction or finishing data found on this page, return an empty JSON object: {}\n"
        "Example response:\n"
        '{"shkaturka_sten": 120.5, "peregorodki_gkl": 45.0, "keramogranit_60x120": 15.3}'
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
                        "text": "Extract finishing volumes from this blueprint image and map them to the allowed price list codes."
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

    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(AI_COMPLETION_URL, headers=headers, json=payload) as response:
                if response.status == 200:
                    result = await response.json()
                    content = result["choices"]["message"]["content"]
                    return json.loads(content)
                else:
                    return {}
        except Exception as e:
            return {}
            
