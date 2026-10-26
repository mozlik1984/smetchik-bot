import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Ваша стабильная система символов для сборки URL
URL_SCHEME = "https"
URL_COLON = ":"
URL_SLASH = "/"
URL_DOUBLE_SLASH = URL_SLASH + URL_SLASH
URL_DOT = "."

# Посимвольная сборка хоста ProxyAPI: api.proxyapi.ru/v1
HOST_PROXY = "api"
HOST_NAME = "proxyapi"
HOST_ZONE = "ru"
API_VERSION = "v1"
PATH_CHAT = "chat"
PATH_COMPLETIONS = "completions"

AI_COMPLETIONS_URL = (
    f"{URL_SCHEME}{URL_COLON}{URL_DOUBLE_SLASH}"
    f"{HOST_PROXY}{URL_DOT}{HOST_NAME}{URL_DOT}{HOST_ZONE}{URL_SLASH}"
    f"{API_VERSION}{URL_SLASH}"
    f"{PATH_CHAT}{URL_SLASH}{PATH_COMPLETIONS}"
)

# Маркер текстовых параметров (чтобы бот понимал, что это данные объекта)
TEXT_DATA_MARKER = "площадь"
