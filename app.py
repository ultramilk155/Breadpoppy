from flask import Flask, render_template, request, redirect, url_for
import sqlite3
import os
import requests
from datetime import datetime

app = Flask(__name__)

# Variabel global untuk menyimpan item di keranjang
cart = []

# Telegram Bot Token and Chat ID
TELEGRAM_BOT_TOKEN = 'YOUR_BOT_TOKEN_HERE'
TELEGRAM_CHAT_ID = 'YOUR_CHAT_ID_HERE'

# Fungsi untuk membuat koneksi ke database
def get_db_connection():
    conn = sqlite3.connect('customer.db')
    conn.row_factory = sqlite3.Row
    return conn

# Fungsi untuk membuat tabel pelanggan jika belum ada
def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    # Buat tabel customers jika belum ada
    c.execute('''CREATE TABLE IF NOT EXISTS customers
                 (id INTEGER PRIMARY KEY, name TEXT, phone TEXT, address TEXT)''')
    # Buat tabel orders jika belum ada
    c.execute('''CREATE TABLE IF NOT EXISTS orders
                 (order_id INTEGER PRIMARY KEY, customer_id INTEGER, product_name TEXT, product_price INTEGER, quantity INTEGER, order_date TEXT,
                  FOREIGN KEY(customer_id) REFERENCES customers(id))''')
    # Buat tabel products jika belum ada
    c.execute('''CREATE TABLE IF NOT EXISTS products
                        (id INTEGER PRIMARY KEY, name TEXT, price INTEGER, image_url TEXT)''')
    conn.commit()
    conn.close()

# Fungsi untuk memperbarui tabel produk dan memastikan kolom image_url ada
def update_products_table():
    conn = get_db_connection()
    c = conn.cursor()
    # Tambahkan kolom image_url jika belum ada
    c.execute("PRAGMA table_info(products)")
    columns = [col[1] for col in c.fetchall()]
    if 'image_url' not in columns:
        c.execute("ALTER TABLE products ADD COLUMN image_url TEXT")
    conn.commit()
    conn.close()

# Fungsi untuk memastikan data produk awal ada di database
def init_products():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM products")
    count = c.fetchone()[0]
    if count == 0:
        products = [
            {"name": "Sepatu Nike", "price": 500000, "image_url": "product1.jpeg"},
            {"name": "Tas Ransel", "price": 300000, "image_url": "product2.jpeg"},
            {"name": "Kemeja Pria", "price": 150000, "image_url": "product3.jpeg"},
            {"name": "Kaos Kaki", "price": 180000, "image_url": "product4.jpeg"},
        ]
        for product in products:
            c.execute("INSERT INTO products (name, price, image_url) VALUES (?, ?, ?)",
                      (product['name'], product['price'], product['image_url']))
        conn.commit()
    conn.close()

# Fungsi untuk mengirim pesan ke Telegram
def send_telegram_message(message):
    url = f'https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage'
    payload = {
        'chat_id': TELEGRAM_CHAT_ID,
        'text': message,
        'parse_mode': 'HTML'
    }
    response = requests.post(url, data=payload)
    return response

# Fungsi untuk mendapatkan daftar gambar dari direktori
def get_images():
    images = []
    for filename in os.listdir('static/images'):
        if filename.endswith('.jpg') or filename.endswith('.jpeg') or filename.endswith('.png'):
            images.append(filename)
    return images

# Membuat tabel jika belum ada dan memastikan data awal ada di database
init_db()
update_products_table()
init_products()

@app.route('/')
def index():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM products")
    products = c.fetchall()
    conn.close()
    return render_template('index.html', products=products, image_dir='/static/images/')

@app.route('/products')
def product():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM products")
    products = c.fetchall()
    conn.close()
    return render_template('product_list.html', products=products, image_dir='/static/images/')

@app.route('/add_product', methods=['GET', 'POST'])
def add_product():
    if request.method == 'POST':
        name = request.form['name']
        price = int(request.form['price'])
        image = request.files['image']

        if image:
            image_filename = image.filename
            image_path = os.path.join('static/images', image_filename)
            image.save(image_path)
        else:
            image_filename = 'default.jpg'

        conn = get_db_connection()
        c = conn.cursor()
        c.execute("INSERT INTO products (name, price, image_url) VALUES (?, ?, ?)",
                  (name, price, image_filename))
        conn.commit()
        conn.close()

        return redirect(url_for('product'))

    return render_template('add_product.html')

@app.route('/delete_product/<int:product_id>', methods=['POST'])
def delete_product(product_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("DELETE FROM products WHERE id = ?", (product_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('product'))

@app.route('/edit_product/<int:product_id>', methods=['GET', 'POST'])
def edit_product(product_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM products WHERE id = ?", (product_id,))
    product = c.fetchone()

    if request.method == 'POST':
        name = request.form['name']
        price = int(request.form['price'])
        image = request.files['image']

        if image:
            image_filename = image.filename
            image_path = os.path.join('static/images', image_filename)
            image.save(image_path)
        else:
            image_filename = product['image_url']

        c.execute("UPDATE products SET name = ?, price = ?, image_url = ? WHERE id = ?",
                  (name, price, image_filename, product_id))
        conn.commit()
        conn.close()

        return redirect(url_for('product'))

    conn.close()
    return render_template('edit_product.html', product=product, image_dir='/static/images/')

@app.route('/add_to_cart/<int:product_id>', methods=['POST'])
def add_to_cart(product_id):
    quantity = int(request.form.get('quantity', 1))
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM products WHERE id = ?", (product_id,))
    product = c.fetchone()
    conn.close()

    if product:
        for item in cart:
            if item["id"] == product_id:
                item["quantity"] += quantity
                break
        else:
            cart.append({"id": product["id"], "name": product["name"], "price": product["price"], "quantity": quantity})

    return redirect(url_for('index'))

@app.route('/cart', methods=['GET', 'POST'])
def view_cart():
    if request.method == 'POST':
        if 'update_quantities' in request.form:
            for item in cart:
                item_id = str(item['id'])
                if item_id in request.form:
                    item['quantity'] = int(request.form[item_id])
        else:
            name = request.form['name']
            phone = request.form['phone']
            address = request.form['address']

            conn = get_db_connection()
            c = conn.cursor()
            c.execute("INSERT INTO customers (name, phone, address) VALUES (?, ?, ?)", (name, phone, address))
            customer_id = c.lastrowid
            order_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            for item in cart:
                c.execute(
                    "INSERT INTO orders (customer_id, product_name, product_price, quantity, order_date) VALUES (?, ?, ?, ?, ?)",
                    (customer_id, item["name"], item["price"] * item["quantity"], item["quantity"], order_date))

            conn.commit()
            conn.close()

            message = f"New Order from {name}\nPhone: {phone}\nAddress: {address}\nOrder Date: {order_date}\nProducts:\n"
            for item in cart:
                message += f"- {item['name']} (x{item['quantity']}): Rp {item['price'] * item['quantity']:,.0f}\n".replace(",", ".")
            send_telegram_message(message)

            cart.clear()
            success_message = "Data pelanggan telah disimpan."
            return render_template('cart.html', products=cart, total_price=0, success_message=success_message)

    total_price = sum(product["price"] * product["quantity"] for product in cart)
    return render_template('cart.html', products=cart, total_price=total_price)

@app.route('/remove_from_cart/<int:product_index>', methods=['POST'])
def remove_from_cart(product_index):
    if 0 <= product_index < len(cart):
        cart.pop(product_index)
    return redirect(url_for('view_cart'))

@app.route('/orders', methods=['GET', 'POST'])
def view_orders():
    conn = get_db_connection()
    c = conn.cursor()
    query = '''SELECT customers.name, customers.phone, customers.address, orders.product_name, orders.product_price, orders.quantity, orders.order_date 
               FROM customers JOIN orders ON customers.id = orders.customer_id'''
    params = []

    if request.method == 'POST':
        filters = []
        start_date = request.form['start_date']
        end_date = request.form['end_date']
        customer_name = request.form['customer_name']
        product_name = request.form['product_name']

        if start_date and end_date:
            filters.append("orders.order_date BETWEEN ? AND ?")
            params.extend([start_date, end_date])

        if customer_name:
            filters.append("customers.name LIKE ?")
            params.append(f"%{customer_name}%")

        if product_name:
            filters.append("orders.product_name LIKE ?")
            params.append(f"%{product_name}%")

        if filters:
            query += " WHERE " + " AND ".join(filters)

        c.execute(query + " ORDER BY orders.order_date DESC", params)
        orders = c.fetchall()
        total_filtered_price = sum(order['product_price'] for order in orders)
        total_filtered_quantity = sum(order['quantity'] for order in orders)
    else:
        c.execute(query + " ORDER BY orders.order_date DESC LIMIT 10")
        orders = c.fetchall()
        total_filtered_price = None
        total_filtered_quantity = None

    conn.close()
    return render_template('orders.html', orders=orders, total_filtered_price=total_filtered_price, total_filtered_quantity=total_filtered_quantity)

@app.template_filter('format_currency')
def format_currency(value):
    return f"Rp {value:,.0f}".replace(",", ".")

if __name__ == '__main__':
    app.run(port=5010, debug=True)
