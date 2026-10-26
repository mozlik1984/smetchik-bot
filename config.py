import os
from dotenv import load_dotenv

# Загрузка локальных переменных (если тестируется на ПК, на Render подхватит автоматом)
load_dotenv()

# Ключи и токены из переменных окружения
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

# Сборка базового хоста и путей
API_BASE_HOST = f"{HOST_PROXY}{URL_DOT}{HOST_NAME}{URL_DOT}{HOST_ZONE}"
API_VERSION = "v1"
PATH_CHAT = "chat"
PATH_COMPLETIONS = "completions"

# Итоговая стабильная ссылка для запросов к ИИ
AI_COMPLETIONS_URL = (
    f"{URL_SCHEME}{URL_COLON}{URL_DOUBLE_SLASH}"
    f"{API_BASE_HOST}{URL_SLASH}"
    f"{API_VERSION}{URL_SLASH}"
    f"{PATH_CHAT}{URL_SLASH}{PATH_COMPLETIONS}"
)

# Компоненты для валидации и работы с Google Диском / Документами
HOST_GOOGLE_DOCS = "docs"
HOST_GOOGLE_MAIN = "google"
HOST_GOOGLE_DRIVE = "drive"
HOST_GOOGLE_ZONE = "com"

GOOGLE_DRIVE_MARKER = f"{HOST_GOOGLE_DRIVE}{URL_DOT}{HOST_GOOGLE_MAIN}{URL_DOT}{HOST_GOOGLE_ZONE}"
PATH_MARKER_FILE = f"{URL_SLASH}file{URL_SLASH}d{URL_SLASH}"

