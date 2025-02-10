from flask import Flask, render_template, request, jsonify
import requests
import os

app = Flask(__name__)

# WooCommerce API настройки
WC_API_URL = os.getenv("WC_API_URL", "https://karal.az/wp-json/wc/v3")
WC_CONSUMER_KEY = os.getenv("WC_CONSUMER_KEY")
WC_CONSUMER_SECRET = os.getenv("WC_CONSUMER_SECRET")

# Функция для получения списка категорий из WooCommerce
def fetch_categories():
    url = f"{WC_API_URL}/products/categories"
    params = {
        "consumer_key": WC_CONSUMER_KEY,
        "consumer_secret": WC_CONSUMER_SECRET
    }
    response = requests.get(url, params=params)

    if response.status_code == 200:
        return response.json()
    return []

@app.route("/")
def home():
    categories = fetch_categories()
    return render_template("index.html", categories=categories)

@app.route("/add-product", methods=["POST"])
def add_product():
    try:
        # Получение данных из формы
        category_id = request.form.get("category")
        weight = request.form.get("weight")
        gold_purity_tag_id = request.form.get("gold_purity")  # ID значения атрибута Əyar (например, 105 или 106)
        price = request.form.get("price")
        sale_price = request.form.get("sale_price", "0")

        # Дефолтное изображение (если не указано)
        image_url = "https://karal.az/wp-content/uploads/2020/01/20200109_113139.jpg"

        # Подготовка данных для отправки в WooCommerce
        product_data = {
            "name": f"Товар {weight}г (проба {gold_purity_tag_id})",
            "type": "simple",
            "regular_price": price,
            "sale_price": sale_price if sale_price != "0" else None,
            "categories": [{"id": int(category_id)}],
            "shipping_class": None,  # Укажите, если у вас есть классы доставки
            "weight": weight,  # Вес в разделе доставки
            "attributes": [
                {
                    "id": 2,  # ID атрибута Əyar
                    "options": [gold_purity_tag_id],  # Передаем tag_id
                    "visible": True,  # Делаем атрибут видимым
                    "variation": False
                }
            ],
            "description": f"Вес: {weight} г, Проба золота: {gold_purity_tag_id}",
            "images": [{"src": image_url}]
        }

        # Отправка данных в WooCommerce API
        url = f"{WC_API_URL}/products"
        params = {
            "consumer_key": WC_CONSUMER_KEY,
            "consumer_secret": WC_CONSUMER_SECRET
        }
        response = requests.post(url, json=product_data, params=params)

        # Проверка ответа от WooCommerce
        if response.status_code == 201:
            return jsonify({"status": "success", "message": "Товар успешно добавлен!"})
        else:
            return jsonify({
                "status": "error",
                "message": "Ошибка при добавлении товара.",
                "details": response.text,
                "status_code": response.status_code
            }), 400

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8080)
