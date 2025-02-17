# Используем Python 3.10 или новее
FROM python:3.10-slim

# Устанавливаем ffmpeg (это нужно для moviepy)
RUN apt-get update && apt-get install -y ffmpeg

# Устанавливаем зависимости Python
WORKDIR /app
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Копируем код приложения
COPY . .

# Запуск приложения
CMD ["gunicorn", "-b", "0.0.0.0:8080", "app:app"]
