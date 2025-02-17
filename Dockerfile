FROM python:3.10

# Устанавливаем ffmpeg
RUN apt-get update && apt-get install -y ffmpeg

# Устанавливаем зависимости
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем код
COPY . .

CMD ["gunicorn", "-b", "0.0.0.0:8080", "app:app"]
