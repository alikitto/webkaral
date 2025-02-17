from flask import Flask, render_template, request, jsonify
import requests
import os
import base64
import random
import moviepy.editor as mp

app = Flask(__name__)

# WooCommerce API данные
WC_API_URL = os.getenv("WC_API_URL", "https://karal.az/wp-json/wc/v3")
WC_CONSUMER_KEY = os.getenv("WC_CONSUMER_KEY")
WC_CONSUMER_SECRET = os.getenv("WC_CONSUMER_SECRET")

# WordPress API данные (для загрузки изображений и видео)
WP_USERNAME = os.getenv("WP_USERNAME", "alikitto")
WP_PASSWORD = os.getenv("WP_PASSWORD", "HsbD0gjVhsj0Fb1KXrMx4nLQ")
WP_MEDIA_URL = "https://karal.az/wp-json/wp/v2/media"

# Авторизация для WordPress API
auth = base64.b64encode(f"{WP_USERNAME}:{WP_PASSWORD}".encode()).decode()
HEADERS = {
    "Authorization": f"Basic {auth}"
}

# Категории товаров
CATEGORY_DATA = {
    "126": {"name": "Qızıl üzük", "slug": "qizil-uzuk"},
    "132": {"name": "Qızıl sırğa", "slug": "qizil-sirqa"},
    "140": {"name": "Qızıl sep", "slug": "qizil-sep"},
    "138": {"name": "Qızıl qolbaq", "slug": "qizil-qolbaq"},
    "144": {"name": ["Qızıl dəst", "Qızıl komplekt"], "slug": "qizil-komplekt-dest"}
}

# Пробы золота (Əyar)
GOLD_PURITY_MAP = {
    "105": "585 (14K)",
    "106": "750 (18K)"
}

# Возможные описания для Qızıl üzüklər
RING_DESCRIPTIONS = [
    "🔹 Yeni qızıl üzük modeli. Zərif dizaynı ilə gündəlik və xüsusi günlər üçün ideal seçim! ✨",
    "💍 Zövqlü dizayn və yüksək keyfiyyət! Bu unikal qızıl üzük zərifliyi və incəliyi ilə seçilir. ✨",
    "✨ Qızılın əbədi gözəlliyi! Zəriflik, incəlik və yüksək keyfiyyət – bu qızıl üzük hər anınızı daha xüsusi edəcək."
]

# Функция загрузки медиа (изображения или видео)
def upload_media(file):
    """ Загружает файл в WordPress и возвращает ID """
    if not file:
        print("Ошибка: Файл отсутствует!")
        return None

    if not hasattr(file, "filename"):
        print("Ошибка: У файла нет атрибута 'filename'")
        return None

    print(f"Отправка файла {file.filename} на сервер WordPress...")

    files = {"file": (file.filename, file.stream, file.content_type)}
    response = requests.post(WP_MEDIA_URL, headers=HEADERS, files=files)

    print(f"Ответ сервера WordPress: {response.status_code}, {response.text}")

    if response.status_code == 201:
        media_id = response.json().get("id")
        print(f"Файл успешно загружен! ID: {media_id}")
        return media_id
    else:
        print(f"Ошибка загрузки файла: {response.text}")
        return None

# Функция конвертации MOV → MP4
def convert_mov_to_mp4(video):
    """ Конвертация MOV в MP4 """
    try:
        temp_input = f"/tmp/{random.randint(1000, 9999)}.mov"
        temp_output = temp_input.replace(".mov", ".mp4")

        print(f"Сохранение видео {video.filename} во временный файл {temp_input}")
        video.save(temp_input)

        print("Начало конвертации MOV → MP4...")

        # Конвертация
        clip = mp.VideoFileClip(temp_input)
        clip.write_videofile(temp_output, codec="libx264", audio_codec="aac")

        print(f"Конвертация завершена! Файл сохранён: {temp_output}")

        return temp_output
    except Exception as e:
        print(f"Ошибка конвертации видео: {e}")
        return None

# Главная страница
@app.route("/")
def home():
    return render_template("index.html", categories=CATEGORY_DATA)

# Добавление товара
@app.route("/add-product", methods=["POST"])
def add_product():
    try:
        category_id = request.form.get("category")
        weight = request.form.get("weight")
        gold_purity_id = request.form.get("gold_purity")
        price = request.form.get("price")
        sale_price = request.form.get("sale_price", "0")
        image = request.files.get("image")
        video = request.files.get("video")

        print(f"Получены данные: Категория: {category_id}, Вес: {weight}, Цена: {price}")

        # Загружаем изображение
        image_id = upload_media(image) if image else None
        if not image_id:
            return jsonify({"status": "error", "message": "❌ Ошибка загрузки изображения"}), 400

        # Проверка типа видео и конвертация, если это MOV
        video_id = None
        if video:
            print(f"Загружено видео: {video.filename}")

            if video.filename.lower().endswith(".mov"):
                converted_video_path = convert_mov_to_mp4(video)
                if converted_video_path:
                    with open(converted_video_path, "rb") as converted_video:
                        video_id = upload_media(converted_video)
            else:
                video_id = upload_media(video)

        # Данные для WooCommerce
        product_data = {
            "name": "Тестовый продукт",
            "slug": "test-product",
            "type": "simple",
            "regular_price": price,
            "sale_price": sale_price if sale_price != "0" else None,
            "categories": [{"id": int(category_id)}],
            "description": "Тестовое описание",
            "images": [{"id": image_id}],
            "meta_data": [
                {"key": "_weight", "value": weight},
                {"key": "_product_video_autoplay", "value": "on"}
            ]
        }

        if video_id:
            product_data["meta_data"].append({"key": "_product_video_gallery", "value": video_id})

        print(f"Отправка данных в WooCommerce: {product_data}")

        # Отправляем товар в WooCommerce
        url = f"{WC_API_URL}/products"
        params = {"consumer_key": WC_CONSUMER_KEY, "consumer_secret": WC_CONSUMER_SECRET}
        response = requests.post(url, json=product_data, params=params)

        print(f"Ответ сервера WooCommerce: {response.status_code}, {response.text}")

        if response.status_code == 201:
            product_url = response.json().get("permalink", "#")
            return jsonify({"status": "success", "message": "✅ Товар успешно добавлен!", "url": product_url})
        else:
            return jsonify({"status": "error", "message": "❌ Ошибка при добавлении товара.", "details": response.text}), 400

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8080)
