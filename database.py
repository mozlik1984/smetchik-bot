import os

def load_price_list() -> dict:
    prices = {}
    
    # Явно определяем папку, где лежит сам скрипт database.py (корень проекта)
    current_dir = os.path.dirname(os.path.abspath(__file__))
    price_file_path = os.path.join(current_dir, "price_list.txt")
    
    if not os.path.exists(price_file_path):
        return prices

    with open(price_file_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
                
            key, data = line.split("=", 1)
            key = key.strip()
            
            parts = data.split("|")
            if len(parts) == 3:
                name = parts[0].strip()
                price = int(parts[1].strip())
                unit = parts[2].strip()
                
                prices[key] = {
                    "name": name,
                    "price": price,
                    "unit": unit
                }
                
    return prices
    
