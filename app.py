from flask import Flask, request, jsonify
from woocommerce import API
import os

app = Flask(__name__)

# Настройки WooCommerce API (читаем из переменных окружения)
wcapi = API(
    url=os.getenv("WC_API_URL"),
    consumer_key=os.getenv("WC_CONSUMER_KEY"),
    consumer_secret=os.getenv("WC_CONSUMER_SECRET"),
    version="wc/v3"
)

@app.route('/')
def home():
    return "WooCommerce API Web App is running!"

@app.route('/add-product', methods=['POST'])
def add_product():
    try:
        data = request.json  # Получаем данные из формы

        # Формируем данные для WooCommerce
        product_data = {
            "name": data.get("name"),
            "type": "simple",
            "regular_price": str(data.get("price")),
            "sale_price": str(data.get("sale_price")) if data.get("sale_price") else None,
            "description": f"Вес: {data.get('weight')} г, Проба золота: {data.get('gold_purity')}",
            "categories": [{"id": int(data.get("category_id"))}],
            "images": [{"src": data.get("image_url")}],
            "attributes": [
                {
                    "name": "Əyar",
                    "visible": True,
                    "options": [data.get('gold_purity')]
                }
            ]
        }

        # Отправляем в WooCommerce API
        response = wcapi.post("products", data=product_data)

        if response.status_code == 201:
            return jsonify({"status": "success", "message": "Товар успешно добавлен!"})
        else:
            return jsonify({"status": "error", "message": response.json()}), 400

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
