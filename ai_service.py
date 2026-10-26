import base64
import json
import aiohttp
from config import AI_COMPLETION_URL, OPENAI_API_KEY
from database import load_price_list

def encode_image_to_base64(image_path: str) -> str:
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")

async def analyze_project_page(image_path: str) -> dict:
    current_prices = load_price_list()
    available_keys = list(current_prices.keys())

    if not available_keys:
        available_keys = ["shkaturka_sten", "laminat_zamok", "keramogranit_60x120", "pie_sten_pod_pokrasku", "invisible_doors_complex"]

    system_prompt = (
        "You are an expert estimation engineer. Analyze the provided Russian blueprint or table image. "
        "Find construction and finishing works, their quantities (volumes, areas) and map them to the allowed keys.\n\n"
        f"ALLOWED KEYS LIST: {', '.join(available_keys)}\n\n"
        "CRITICAL MAPPING RULES FOR RUSSIAN TEXT IN IMAGE:\n"
        "- If you see Russian words like 'Shtukatourka', 'Shtukaturnye', 'Vravnivanie sten' -> map to 'shkaturka_sten'\n"
        "- If you see Russian words like 'Laminat', 'Kvarcvinil', 'Pol' or floor finish quantities -> map to 'laminat_zamok'\n"
        "- If you see Russian words like 'Keramogranit', 'Plitka', '60x120' -> map to 'keramogranit_60x120'\n"
        "- If you see Russian words like 'Pokraska sten', 'Steny pod pokrasku', 'Okraska' -> map to 'pie_sten_pod_pokrasku'\n"
        "- If you see Russian words like 'Skrytaya dver', 'Invisible' -> map to 'invisible_doors_complex'\n\n"
        "OUTPUT FORMAT Rules:\n"
        "1. Return output STRICTLY as a valid JSON object.\n"
        "2. Key must be ONLY from the allowed keys list, value must be a number (volume, quantity).\n"
        "3. If no matching construction data found on this page, return an empty JSON object: {}\n"
        "Example response:\n"
        '{"shkaturka_sten": 120.5, "laminat_zamok": 45.0}'
    )

    try:
        base64_image = encode_image_to_base64(image_path)
    except Exception as e:
        print(f"Error: {e}")
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
                        "text": "Find finishing volumes from this Russian project image and map to JSON."
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
            
