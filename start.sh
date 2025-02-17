#!/bin/bash
set -e  # Завершаем выполнение при ошибках

echo "🔧 Устанавливаем зависимости..."
python3 -m ensurepip --default-pip  # Убеждаемся, что pip установлен
pip install -r requirements.txt  # Устанавливаем зависимости

echo "🚀 Запускаем приложение..."
exec gunicorn -b 0.0.0.0:8080 app:app
