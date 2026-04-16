# Берем готовый образ Python
FROM python:3.11-slim

# Устанавливаем сканер Tesseract и русский язык (тут нам разрешено!)
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-rus \
    libgl1-mesa-glx \
    && rm -rf /var/lib/apt/lists/*

# Копируем наш код в сервер
WORKDIR /app
COPY . /app

# Устанавливаем библиотеки
RUN pip install --no-cache-dir -r requirements.txt

# Запускаем бота
CMD ["python", "main.py"]
