import os
from config import PRICE_LIST_PATH

def load_price_list() -> dict:
    prices = {}
    if not os.path.exists(PRICE_LIST_PATH):
        return prices

    with open(PRICE_LIST_PATH, "r", encoding="utf-8") as f:
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
  
