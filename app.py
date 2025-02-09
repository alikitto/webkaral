from flask import Flask, render_template, request, jsonify
import requests
import os

app = Flask(__name__)

# WooCommerce API ключи
WC_API_URL = os.getenv("WC_API_URL")
WC_CONSUMER_KEY = os.getenv("WC_CONSUMER_KEY")
WC_CONSUMER_SECRET = os.getenv("WC_CONSUMER_SECRET")

@app.route('/')
def home():
    # Отдаем HTML-форму пользователю
    return render_template('index.html')

@app.route('/add-product', methods=['POST'])
def add_product():
    # Получаем данные из формы
    category_id = request.form.get('category')
    weight = request.form.get('weight')
    gold_purity = request.form.get('gold_purity')
    price = request.form.get('price')
    sale_price = request.form.get('sale_price', '0')

    # Дефолтное изображение
    image_url = "https://karal.az/wp-content/uploads/2020/01/20200109_113139.jpg"

    # Формируем данные для WooCommerce
    product_data = {
        "name": f"Товар {gold_purity} {weight}г",
        "type": "simple",
        "regular_price": price,
        "sale_price": sale_price if sale_price != "0" else None,
        "categories": [{"id": category_id}],
        "description": f"Вес: {weight} г, Проба золота: {gold_purity}",
        "images": [{"src": image_url}],
    }

    # Отправляем запрос в WooCommerce
    url = f"{WC_API_URL}/products"
    params = {"consumer_key": WC_CONSUMER_KEY, "consumer_secret": WC_CONSUMER_SECRET}
    response = requests.post(url, json=product_data, params=params)

    if response.status_code == 201:
        return jsonify({"status": "success", "message": "Товар успешно добавлен!"})
    else:
        return jsonify({"status": "error", "message": "Ошибка при добавлении товара."}), 400

if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=8080)
