# Используем официальный образ Python
FROM python:3.10

# Устанавливаем FFmpeg
RUN apt-get update && apt-get install -y ffmpeg

# Создаём рабочую директорию
WORKDIR /app

# Копируем файлы проекта
COPY . /app

# Устанавливаем зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Запуск приложения через Gunicorn
CMD ["gunicorn", "--workers", "2", "--threads", "2", "--timeout", "120", "--bind", "0.0.0.0:8080", "app:app"]
