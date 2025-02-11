from flask import Flask, render_template, request, jsonify
import requests
import os
import base64

app = Flask(__name__)

# WooCommerce API настройки
WC_API_URL = os.getenv("WC_API_URL", "https://karal.az/wp-json/wc/v3")
WC_CONSUMER_KEY = os.getenv("WC_CONSUMER_KEY")
WC_CONSUMER_SECRET = os.getenv("WC_CONSUMER_SECRET")

# WordPress User Auth (для загрузки изображений)
WP_USERNAME = "alikitto"  # Имя пользователя WordPress
WP_PASSWORD = "HsbD 0gjV hsj0 Fb1K XrMx 4nLQ"  # Application Password
AUTH_HEADER = {
    "Authorization": "Basic " + base64.b64encode(f"{WP_USERNAME}:{WP_PASSWORD}".encode()).decode()
}

# Функция загрузки изображения в WordPress Media Library
def upload_image(image):
    files = {'file': image}
    url = f"{WC_API_URL}/wp/v2/media"
    
    response = requests.post(url, headers=AUTH_HEADER, files=files)
    
    if response.status_code == 201:
        return response.json().get("source_url")  # Возвращаем URL загруженного изображения
    else:
        return None  # Ошибка загрузки

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/add-product", methods=["POST"])
def add_product():
    try:
        category_id = request.form.get("category")
        weight = request.form.get("weight")
        gold_purity = request.form.get("gold_purity")
        price = request.form.get("price")
        sale_price = request.form.get("sale_price", "0")
        image = request.files.get("image")  # Загруженное изображение

        # Загрузка изображения в WordPress
        image_url = upload_image(image) if image else None
        if not image_url:
            return jsonify({"status": "error", "message": "❌ Ошибка загрузки изображения"}), 400

        # Автоматическая генерация названия и slug
        category_names = {
            "126": "Qızıl üzük",
            "132": "Qızıl sırğa",
            "140": "Qızıl sep",
            "138": "Qızıl qolbaq",
            "144": "Qızıl dəst komplekt"
        }
        product_name = category_names.get(category_id, "Qızıl məhsul")
        product_slug = product_name.lower().replace(" ", "-")

        # Генерация случайного описания
        descriptions = [
            "🔹 Yeni qızıl üzük modeli. Zərif dizaynı ilə gündəlik və xüsusi günlər üçün ideal seçim! ✨",
            "💍 Zövqlü dizayn və yüksək keyfiyyət! Bu unikal qızıl üzük zərifliyi və incəliyi ilə seçilir. ✨",
            "✨ Qızılın əbədi gözəlliyi! Zəriflik, incəlik və yüksək keyfiyyət – bu qızıl üzük hər anınızı daha xüsusi edəcək."
        ]
        description = descriptions[int(weight) % len(descriptions)]  # Выбираем случайное описание

        # Данные для создания товара
        product_data = {
            "name": product_name,
            "slug": f"{product_slug}-{int(weight)}",
            "type": "simple",
            "regular_price": price,
            "sale_price": sale_price if sale_price != "0" else None,
            "categories": [{"id": int(category_id)}],
            "description": description,
            "images": [{"src": image_url}],
            "attributes": [
                {
                    "id": 2,  # ID атрибута Əyar
                    "options": [gold_purity],  # Значение атрибута (585, 750 и т. д.)
                    "visible": True
                }
            ],
            "weight": weight  # Вес товара
        }

        # Отправляем запрос в WooCommerce
        url = f"{WC_API_URL}/products"
        params = {
            "consumer_key": WC_CONSUMER_KEY,
            "consumer_secret": WC_CONSUMER_SECRET
        }
        response = requests.post(url, json=product_data, params=params)

        if response.status_code == 201:
            product_id = response.json().get("id")
            product_link = f"https://karal.az/product/{product_slug}-{product_id}/"
            return jsonify({"status": "success", "message": "✅ Товар успешно добавлен!", "link": product_link})
        else:
            return jsonify({"status": "error", "message": "❌ Ошибка при добавлении товара.", "details": response.text}), 400

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8080)
