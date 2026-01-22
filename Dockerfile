FROM python:3.9-slim

WORKDIR /app

# Копировать requirements и установить зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копировать код приложения
COPY src/ ./src/
COPY mock_replicate.py .

# Установить переменные окружения
ENV PYTHONUNBUFFERED=1

# Команда запуска FastAPI приложения
CMD ["uvicorn", "src.app:app", "--host", "0.0.0.0", "--port", "8000"]
