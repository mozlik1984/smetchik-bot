import json
import aiohttp
from config import AI_COMPLETION_URL, OPENAI_API_KEY

async def analyze_project_via_link(project_url: str, price_list_text: str) -> str:
    # Заставляем ИИ зайти по ссылке, прочитать проект и рассчитать смету по прайсу
    system_prompt = (
        "You are an expert construction estimator. You will receive a direct Google Drive link to a design project PDF file, and a price list text.\n"
        "Your task:\n"
        "1. Open and thoroughly analyze the PDF file via the provided URL.\n"
        "2. Look for finish schedules, area specifications, and drawing tables in the document.\n"
        "3. Match the discovered quantities and items with the positions in the provided price list.\n"
        "4. Calculate the cost for each matching item (Volume multiplied by Price).\n"
        "5. Output a beautifully formatted comprehensive summary in Russian language.\n\n"
        "The output must include:\n"
        "- Name of the work\n"
        "- Extracted volume and unit\n"
        "- Base price and final calculated cost\n"
        "- Grand Total sum in Rubles (ИТОГО)\n"
        "Do not use non-ascii characters in the code string, keep the output response strictly as clean text."
    )

    user_content = (
        f"Here is the design project PDF link: {project_url}\n\n"
        f"Here is the allowed Price List:\n{price_list_text}\n\n"
        "Please analyze the file, calculate the estimate, and output a detailed report in Russian."
    )

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {OPENAI_API_KEY}"
    }

    payload = {
        "model": "gpt-4o",  # gpt-4o превосходно умеет читать файлы по внешним ссылкам
        "messages": [
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": user_content
            }
        ],
        "temperature": 0.2
    }

    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(AI_COMPLETION_URL, headers=headers, json=payload) as response:
                if response.status == 200:
                    result = await response.json()
                    return result["choices"]["message"]["content"]
                else:
                    err = await response.text()
                    return f"API Error ({response.status}): {err}"
        except Exception as e:
            return f"Network communication error: {e}"
            
