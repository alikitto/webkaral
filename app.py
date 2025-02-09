from flask import Flask, render_template, request, redirect, url_for
import requests
import os

app = Flask(__name__)

# Настройки WooCommerce
WC_API_URL = os.getenv("WC_API_URL", "https://karal.az/wp-json/wc/v3")
WC_CONSUMER_KEY = os.getenv("WC_CONSUMER_KEY")
WC_CONSUMER_SECRET = os.getenv("WC_CONSUMER_SECRET")


# Функция для получения категорий из WooCommerce
def fetch_categories():
    url = f"{WC_API_URL}/products/categories"
    params = {
        "consumer_key": WC_CONSUMER_KEY,
        "consumer_secret": WC_CONSUMER_SECRET,
    }
    response = requests.get(url, params=params)
    if response.status_code == 200:
        return response.json()
    return []


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        # Получение данных из формы
        name = request.form.get("name")
        category_id = request.form.get("category")  # ID категории
        weight = request.form.get("weight")
        gold_purity = request.form.get("gold_purity")
        price = request.form.get("price")
        sale_price = request.form.get("sale_price") or None

        # Подготовка данных для WooCommerce
        product_data = {
            "name": name,
            "type": "simple",
            "regular_price": price,
            "sale_price": sale_price,
            "categories": [{"id": int(category_id)}],
            "description": f"Вес: {weight} г, Проба золота: {gold_purity}",
            "images": [
                {"src": "https://karal.az/wp-content/uploads/2020/01/20200109_113139.jpg"}
            ],
        }

        # Запрос к WooCommerce API
        url = f"{WC_API_URL}/products"
        params = {
            "consumer_key": WC_CONSUMER_KEY,
            "consumer_secret": WC_CONSUMER_SECRET,
        }
        response = requests.post(url, json=product_data, params=params)

        if response.status_code == 201:
            return redirect(url_for("index"))
        else:
            return "Ошибка при добавлении товара", 500

    # Получение категорий для отображения
    categories = fetch_categories()
    return render_template("index.html", categories=categories)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
