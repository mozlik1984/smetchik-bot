import base64
import json
import aiohttp
from config import AI_COMPLETION_URL, OPENAI_API_KEY

def encode_image_to_base64(image_path: str) -> str:
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")

async def analyze_project_page(image_path: str) -> dict:
    system_prompt = (
        "You are an assistant. Look at the blueprint image. "
        "Find any tables, materials, text or quantities. "
        "List what you see in English language. "
        "Return STRICTLY a JSON object with one key 'debug_text' containing your text. "
        "Do not use any non-ascii characters."
    )

    try:
        base64_image = encode_image_to_base64(image_path)
    except Exception as e:
        return {"debug_text": f"Error encoding: {e}"}

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
                        "text": "What text or tables do you see on this page?"
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
        "temperature": 0.5
    }

    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(AI_COMPLETION_URL, headers=headers, json=payload) as response:
                if response.status == 200:
                    result = await response.json()
                    content = result["choices"]["message"]["content"]
                    return json.loads(content)
                else:
                    err = await response.text()
                    return {"debug_text": f"API Error {response.status}: {err}"}
        except Exception as e:
            return {"debug_text": f"Network error: {e}"}
          
