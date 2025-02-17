# Базовый образ Python + ffmpeg
FROM python:3.10-slim

# Устанавливаем ffmpeg и зависимости
RUN apt-get update && apt-get install -y ffmpeg libsm6 libxext6 && apt-get clean

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем файлы
COPY . .

# Устанавливаем зависимости Python
RUN pip install --no-cache-dir -r requirements.txt

# Запускаем сервер
CMD ["gunicorn", "-b", "0.0.0.0:8080", "app:app"]
