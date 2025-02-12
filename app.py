from flask import Flask, render_template, request, jsonify
import requests
import os
import base64
import random

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

# Функция загрузки файла (изображение или видео) в WordPress
def upload_media(file):
    """ Загружает файл (изображение или видео) в медиатеку WordPress и возвращает ID """
    files = {"file": (file.filename, file.stream, file.content_type)}
    response = requests.post(WP_MEDIA_URL, headers=HEADERS, files=files)

    if response.status_code == 201:
        media_id = response.json().get("id")  # Получаем ID файла
        return media_id
    else:
        return None

# Главная страница
@app.route("/")
def home():
    return render_template("index.html", categories=CATEGORY_DATA)

# Добавление товара
@app.route("/add-product", methods=["POST"])
def add_product():
    try:
        # Получаем данные из формы
        category_id = request.form.get("category")
        weight = request.form.get("weight")
        gold_purity_id = request.form.get("gold_purity")  # Получаем ID пробы
        price = request.form.get("price")
        sale_price = request.form.get("sale_price", "0")
        image = request.files.get("image")
        video = request.files.get("video")  # Файл видео

        # Преобразуем ID пробы в текстовое значение
        gold_purity = GOLD_PURITY_MAP.get(gold_purity_id, "585 (14K)")

        # Генерируем название и slug
        category_info = CATEGORY_DATA.get(category_id, {})
        product_name = random.choice(category_info["name"]) if isinstance(category_info["name"], list) else category_info["name"]
        product_slug = f"{category_info['slug']}-{random.randint(1000, 9999)}"

        # Генерация описания
        if category_id == "126":  # Üzüklər
            description = random.choice(RING_DESCRIPTIONS)
        else:
            description = f"Yeni {product_name} modeli. Çəkisi: {weight}g, Əyarı: {gold_purity}"

        # Загружаем изображение
        image_id = upload_media(image) if image else None
        if not image_id:
            return jsonify({"status": "error", "message": "❌ Ошибка загрузки изображения"}), 400

        # Загружаем видео
        video_id = upload_media(video) if video else None

        # Данные для WooCommerce API
        product_data = {
            "name": product_name,
            "slug": product_slug,
            "type": "simple",
            "regular_price": price,
            "sale_price": sale_price if sale_price != "0" else None,
            "categories": [{"id": int(category_id)}],
            "description": description,
            "images": [{"id": image_id}],  # Теперь передаем ID изображения
            "attributes": [
                {
                    "id": 2,  # ID атрибута Əyar
                    "options": [gold_purity],  # Передаем текст
                    "visible": True,
                    "variation": False
                }
            ],
            "meta_data": [
                {"key": "_weight", "value": weight}  # Вес
            ]
        }

        # Если есть видео, добавляем его в meta_data с ключом "_product_video_gallery"
        if video_id:
            product_data["meta_data"].append({"key": "_product_video_gallery", "value": video_id})

        # Отправляем товар в WooCommerce
        url = f"{WC_API_URL}/products"
        params = {"consumer_key": WC_CONSUMER_KEY, "consumer_secret": WC_CONSUMER_SECRET}
        response = requests.post(url, json=product_data, params=params)

        # Проверка ответа
        if response.status_code == 201:
            product_url = response.json().get("permalink", "#")
            return jsonify({"status": "success", "message": "✅ Товар успешно добавлен!", "url": product_url})
        else:
            return jsonify({"status": "error", "message": "❌ Ошибка при добавлении товара.", "details": response.text}), 400

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8080)
