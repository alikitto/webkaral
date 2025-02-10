from flask import Flask, render_template, request, jsonify
import requests
import os

app = Flask(__name__)

# WooCommerce API настройки
WC_API_URL = os.getenv("WC_API_URL", "https://karal.az/wp-json/wc/v3")
WC_CONSUMER_KEY = os.getenv("WC_CONSUMER_KEY")
WC_CONSUMER_SECRET = os.getenv("WC_CONSUMER_SECRET")

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/add-product", methods=["POST"])
def add_product():
    try:
        # Получение данных из формы
        name = request.form.get("name")
        category_id = request.form.get("category")
        weight = request.form.get("weight")
        gold_purity_slug = request.form.get("gold_purity")  # Значение slug (например, "585-14k")
        price = request.form.get("price")
        sale_price = request.form.get("sale_price", "0")
        image_url = request.form.get("image", "https://karal.az/wp-content/uploads/2020/01/20200109_113139.jpg")

# Подготовка данных для атрибутов
attributes_data = [
    {
        "id": 2,  # ID атрибута Əyar
        "options": [gold_purity]  # Здесь передаётся slug, например: "585" или "750"
    }
]

# Добавляем атрибуты к данным товара
product_data = {
    "name": f"Товар {gold_purity} {weight}г",
    "type": "simple",
    "regular_price": price,
    "sale_price": sale_price if sale_price != "0" else None,
    "categories": [{"id": int(category_id)}],
    "description": f"Вес: {weight} г, Проба золота: {gold_purity}",
    "images": [{"src": image_url}],
    "attributes": attributes_data
}


        # Отправка данных в WooCommerce
        url = f"{WC_API_URL}/products"
        params = {
            "consumer_key": WC_CONSUMER_KEY,
            "consumer_secret": WC_CONSUMER_SECRET
        }
        response = requests.post(url, json=product_data, params=params)

        # Проверка ответа
        if response.status_code == 201:
            return jsonify({"status": "success", "message": "✅ Товар успешно добавлен!"})
        else:
            return jsonify({
                "status": "error",
                "message": "❌ Ошибка при добавлении товара.",
                "details": response.text
            }), 400

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8080)
