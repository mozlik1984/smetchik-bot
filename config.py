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
URL_QUESTION = "?"
URL_AND = "&"
URL_EQUAL = "="

# Компоненты хоста нейросети
HOST_PROXY = "api"
HOST_NAME = "proxyapi"
HOST_ZONE = "ru"

API_BASE_HOST = f"{HOST_PROXY}{URL_DOT}{HOST_NAME}{URL_DOT}{HOST_ZONE}"
API_VERSION = "v1"
PATH_CHAT = "chat"
PATH_COMPLETIONS = "completions"

AI_COMPLETIONS_URL = (
    f"{URL_SCHEME}{URL_COLON}{URL_DOUBLE_SLASH}"
    f"{API_BASE_HOST}{URL_SLASH}"
    f"{API_VERSION}{URL_SLASH}"
    f"{PATH_CHAT}{URL_SLASH}{PATH_COMPLETIONS}"
)

# Компоненты для работы с Google Диском
HOST_GOOGLE_DOCS = "docs"
HOST_GOOGLE_MAIN = "google"
HOST_GOOGLE_DRIVE = "drive"
HOST_GOOGLE_ZONE = "com"

GOOGLE_DRIVE_MARKER = f"{HOST_GOOGLE_DRIVE}{URL_DOT}{HOST_GOOGLE_MAIN}{URL_DOT}{HOST_GOOGLE_ZONE}"

# Переменные для безопасного парсинга и сборки ссылок (БЕЗ ЖЕСТКОГО ТЕКСТА)
PATH_MARKER_FILE_D = f"{URL_SLASH}file{URL_SLASH}d{URL_SLASH}"
PARAM_ID_EQUAL = f"id{URL_EQUAL}"
PARAM_EXPORT_DOWNLOAD = f"export{URL_EQUAL}download"

# Собираем базовый URL скачивания: https://google.com
API_GOOGLE_UC = f"{URL_SCHEME}{URL_COLON}{URL_DOUBLE_SLASH}{GOOGLE_DRIVE_MARKER}{URL_SLASH}uc"
