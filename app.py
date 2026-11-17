# ==========================================
# LocalKart - Multi-Vendor Marketplace
# Updated with Home Delivery and Store Pickup
# ==========================================

from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import os

app = Flask(__name__)

app.secret_key = os.environ.get(
    "SECRET_KEY",
    "change-this-secret-key"
)

# Store database beside app.py
DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "marketplace.db")


# ==========================================
# DATABASE CONNECTION
# ==========================================

def db():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    return con


# ==========================================
# DATABASE INITIALIZATION
# ==========================================

def init_db():

    con = db()

    con.executescript("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT NOT NULL CHECK(role IN ('customer','vendor','admin'))
    );

    CREATE TABLE IF NOT EXISTS products(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        vendor_id INTEGER,
        name TEXT NOT NULL,
        category TEXT,
        description TEXT,
        price REAL NOT NULL,
        image TEXT,
        stock INTEGER DEFAULT 10,
        FOREIGN KEY(vendor_id) REFERENCES users(id)
    );

    CREATE TABLE IF NOT EXISTS orders(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_id INTEGER,
        product_id INTEGER,
        quantity INTEGER,
        total REAL,
        address TEXT,
        status TEXT DEFAULT 'Placed'
    );
    """)

    # --------------------------------------
    # Safely update existing orders table
    # --------------------------------------

    columns = [
        row["name"]
        for row in con.execute("PRAGMA table_info(orders)").fetchall()
    ]

    if "delivery_method" not in columns:
        con.execute("""
            ALTER TABLE orders
            ADD COLUMN delivery_method TEXT DEFAULT 'Home Delivery'
        """)

    if "customer_phone" not in columns:
        con.execute("""
            ALTER TABLE orders
            ADD COLUMN customer_phone TEXT DEFAULT ''
        """)

    # --------------------------------------
    # Create demo admin account
    # --------------------------------------

    admin = con.execute(
        "SELECT id FROM users WHERE email=?",
        ("admin@localkart.in",)
    ).fetchone()

    if not admin:

        con.execute("""
            INSERT INTO users(name,email,password,role)
            VALUES(?,?,?,?)
        """, (
            "Marketplace Admin",
            "admin@localkart.in",
            generate_password_hash("Admin@123"),
            "admin"
        ))

    # --------------------------------------
    # Add demo products
    # --------------------------------------

    if con.execute("SELECT COUNT(*) FROM products").fetchone()[0] == 0:

        demo = [
            (
                "Fresh Apples", "Groceries",
                "Crisp apples from a local farm.",
                149,
                "https://images.unsplash.com/photo-1560806887-1e4cd0b6cbd6?w=700",
                30
            ),
            (
                "Handmade Ceramic Mug", "Home",
                "Handcrafted mug by a local artisan.",
                299,
                "https://images.unsplash.com/photo-1515714342885-4e2c5b1a7f7b?w=700",
                12
            ),
            (
                "Cotton Tote Bag", "Fashion",
                "Reusable everyday cotton tote.",
                199,
                "https://images.unsplash.com/photo-1590874103328-eac38a683ce7?w=700",
                20
            ),
            (
                "Indoor Green Plant", "Home",
                "Easy-care indoor plant.",
                249,
                "https://images.unsplash.com/photo-1501004318641-b39e6451bec6?w=700",
                15
            )
        ]

        for p in demo:

            con.execute("""
                INSERT INTO products(
                    vendor_id,name,category,description,price,image,stock
                )
                VALUES(NULL,?,?,?,?,?,?)
            """, p)

    con.commit()
    con.close()


# ==========================================
# CURRENT USER
# ==========================================

def current_user():

    if "user_id" not in session:
        return None

    con = db()

    user = con.execute(
        "SELECT id,name,email,role FROM users WHERE id=?",
        (session["user_id"],)
    ).fetchone()

    con.close()

    return user


@app.context_processor
def inject_user():

    return {"user": current_user()}


# ==========================================
# HOME PAGE
# ==========================================

@app.route("/")
def home():

    q = request.args.get("q", "").strip()
    category = request.args.get("category", "")

    con = db()

    sql = """
        SELECT products.*, users.name AS shop
        FROM products
        LEFT JOIN users ON products.vendor_id=users.id
        WHERE 1=1
    """

    args = []

    if q:

        sql += """
            AND (
                products.name LIKE ?
                OR products.description LIKE ?
                OR products.category LIKE ?
            )
        """

        args += [f"%{q}%"] * 3

    if category:

        sql += " AND products.category=?"
        args.append(category)

    products = con.execute(
        sql + " ORDER BY products.id DESC",
        args
    ).fetchall()

    categories = con.execute("""
        SELECT DISTINCT category
        FROM products
        WHERE category IS NOT NULL AND category!=''
    """).fetchall()

    con.close()

    return render_template(
        "home.html",
        products=products,
        categories=categories,
        q=q,
        selected=category
    )


# ==========================================
# CUSTOMER / VENDOR REGISTRATION
# ==========================================

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        name = request.form["name"].strip()
        email = request.form["email"].strip().lower()
        password = request.form["password"]
        role = request.form["role"]

        if role not in ("customer", "vendor"):

            flash("Choose a valid account type.")
            return redirect(url_for("register"))

        try:

            con = db()

            con.execute("""
                INSERT INTO users(name,email,password,role)
                VALUES(?,?,?,?)
            """, (
                name,
                email,
                generate_password_hash(password),
                role
            ))

            con.commit()
            con.close()

            flash("Account created. Please sign in.")

            return redirect(url_for("login"))

        except sqlite3.IntegrityError:

            flash("That email is already registered.")

    return render_template("auth.html", mode="register")


# ==========================================
# LOGIN
# ==========================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        con = db()

        u = con.execute(
            "SELECT * FROM users WHERE email=?",
            (request.form["email"].strip().lower(),)
        ).fetchone()

        con.close()

        if u and check_password_hash(
            u["password"],
            request.form["password"]
        ):

            session.clear()
            session["user_id"] = u["id"]

            return redirect(url_for("dashboard"))

        flash("Incorrect email or password.")

    return render_template("auth.html", mode="login")


# ==========================================
# LOGOUT
# ==========================================

@app.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("home"))


# ==========================================
# DASHBOARD
# ==========================================

@app.route("/dashboard")
def dashboard():

    u = current_user()

    if not u:
        return redirect(url_for("login"))

    if u["role"] == "vendor":
        return redirect(url_for("vendor_dashboard"))

    if u["role"] == "admin":
        return redirect(url_for("admin_dashboard"))

    con = db()

    orders = con.execute("""
        SELECT orders.*,
               products.name AS product
        FROM orders
        JOIN products ON products.id=orders.product_id
        WHERE orders.customer_id=?
        ORDER BY orders.id DESC
    """, (u["id"],)).fetchall()

    con.close()

    return render_template("customer.html", orders=orders)


# ==========================================
# VENDOR DASHBOARD
# ==========================================

@app.route("/vendor")
def vendor_dashboard():

    u = current_user()

    if not u:
        return redirect(url_for("login"))

    if u["role"] != "vendor":
        return "Access denied: vendor account required.", 403

    con = db()

    # Vendor's own products
    products = con.execute("""
        SELECT *
        FROM products
        WHERE vendor_id=?
        ORDER BY id DESC
    """, (u["id"],)).fetchall()

    # Vendor's orders with customer details
    orders = con.execute("""
        SELECT
            orders.*,
            products.name AS product,
            users.name AS customer_name,
            users.email AS customer_email
        FROM orders
        JOIN products ON products.id=orders.product_id
        JOIN users ON users.id=orders.customer_id
        WHERE products.vendor_id=?
        ORDER BY orders.id DESC
    """, (u["id"],)).fetchall()

    con.close()

    return render_template(
        "vendor.html",
        products=products,
        orders=orders
    )


# ==========================================
# UPDATE ORDER STATUS
# ==========================================

@app.route("/vendor/order/<int:order_id>/status", methods=["POST"])
def update_order_status(order_id):

    u = current_user()

    if not u or u["role"] != "vendor":
        return "Access denied.", 403

    new_status = request.form.get("status", "")

    allowed_statuses = [
        "Accepted",
        "Packed",
        "Out for Delivery",
        "Delivered",
        "Ready for Pickup",
        "Picked Up"
    ]

    if new_status not in allowed_statuses:
        flash("Invalid order status.")
        return redirect(url_for("vendor_dashboard"))

    con = db()

    # Ensure the order belongs to this vendor
    order = con.execute("""
        SELECT orders.id
        FROM orders
        JOIN products ON products.id=orders.product_id
        WHERE orders.id=? AND products.vendor_id=?
    """, (order_id, u["id"])).fetchone()

    if not order:

        con.close()
        return "Order not found.", 404

    con.execute("""
        UPDATE orders
        SET status=?
        WHERE id=?
    """, (new_status, order_id))

    con.commit()
    con.close()

    flash("Order status updated.")

    return redirect(url_for("vendor_dashboard"))


# ==========================================
# ADD PRODUCT
# ==========================================

@app.route("/vendor/add", methods=["POST"])
def add_product():

    u = current_user()

    if not u or u["role"] != "vendor":
        return "Access denied.", 403

    f = request.form

    try:

        con = db()

        con.execute("""
            INSERT INTO products(
                vendor_id,name,category,description,price,image,stock
            )
            VALUES(?,?,?,?,?,?,?)
        """, (
            u["id"],
            f["name"],
            f["category"],
            f["description"],
            float(f["price"]),
            f["image"],
            int(f["stock"])
        ))

        con.commit()
        con.close()

        flash("Product published.")

    except (ValueError, KeyError):

        flash("Please enter valid product details.")

    return redirect(url_for("vendor_dashboard"))


# ==========================================
# ADMIN DASHBOARD
# ==========================================

@app.route("/admin")
def admin_dashboard():

    u = current_user()

    if not u:
        return redirect(url_for("login"))

    if u["role"] != "admin":
        return "Access denied: admin account required.", 403

    con = db()

    users = con.execute("""
        SELECT id,name,email,role
        FROM users
        ORDER BY id DESC
    """).fetchall()

    products = con.execute("""
        SELECT products.*, users.name AS shop
        FROM products
        LEFT JOIN users ON users.id=products.vendor_id
        ORDER BY products.id DESC
    """).fetchall()

    orders = con.execute("""
        SELECT * FROM orders
        ORDER BY id DESC
    """).fetchall()

    con.close()

    return render_template(
        "admin.html",
        users=users,
        products=products,
        orders=orders
    )


# ==========================================
# CART
# ==========================================

@app.route("/cart")
def cart():

    ids = session.get("cart", {})

    con = db()

    items = []
    total = 0

    for pid, qty in ids.items():

        p = con.execute(
            "SELECT * FROM products WHERE id=?",
            (int(pid),)
        ).fetchone()

        if p:

            line = p["price"] * qty

            total += line

            items.append({
                "product": p,
                "qty": qty,
                "line": line
            })

    con.close()

    return render_template(
        "cart.html",
        items=items,
        total=total
    )


# ==========================================
# ADD TO CART
# ==========================================

@app.route("/cart/add/<int:pid>", methods=["POST"])
def add_cart(pid):

    con = db()

    p = con.execute(
        "SELECT id FROM products WHERE id=?",
        (pid,)
    ).fetchone()

    con.close()

    if not p:
        return "Product not found.", 404

    cart = session.get("cart", {})

    key = str(pid)

    cart[key] = cart.get(key, 0) + 1

    session["cart"] = cart

    flash("Added to cart.")

    return redirect(request.referrer or url_for("home"))


# ==========================================
# REMOVE FROM CART
# ==========================================

@app.route("/cart/remove/<int:pid>", methods=["POST"])
def remove_cart(pid):

    cart = session.get("cart", {})

    cart.pop(str(pid), None)

    session["cart"] = cart

    return redirect(url_for("cart"))


# ==========================================
# CHECKOUT
# ==========================================

@app.route("/checkout", methods=["GET", "POST"])
def checkout():

    u = current_user()

    if not u:
        flash("Please sign in before checkout.")
        return redirect(url_for("login"))

    if u["role"] != "customer":
        return "Only customers can place orders.", 403

    cart = session.get("cart", {})

    if not cart:
        return redirect(url_for("cart"))

    con = db()

    if request.method == "POST":

        # Get customer details
        phone = request.form.get("phone", "").strip()

        # Get delivery method
        delivery_method = request.form.get(
            "delivery_method",
            "Home Delivery"
        )

        address = request.form.get("address", "").strip()

        # Validate phone
        if not phone:
            con.close()
            flash("Please enter your phone number.")
            return redirect(url_for("checkout"))

        # Validate delivery method
        if delivery_method not in ["Home Delivery", "Store Pickup"]:
            con.close()
            flash("Please select a valid delivery method.")
            return redirect(url_for("checkout"))

        # Address required only for home delivery
        if delivery_method == "Home Delivery" and not address:
            con.close()
            flash("Please enter your delivery address.")
            return redirect(url_for("checkout"))

        try:

            # Start a transaction
            con.execute("BEGIN")

            placed_count = 0

            for pid, qty in cart.items():

                p = con.execute("""
                    SELECT * FROM products
                    WHERE id=?
                """, (int(pid),)).fetchone()

                if not p:
                    continue

                if qty <= 0 or p["stock"] < qty:
                    continue

                # Store an empty address for store pickup
                order_address = (
                    address if delivery_method == "Home Delivery" else ""
                )

                # Save order details
                con.execute("""
                    INSERT INTO orders(
                        customer_id,
                        product_id,
                        quantity,
                        total,
                        address,
                        status,
                        delivery_method,
                        customer_phone
                    )
                    VALUES(?,?,?,?,?,?,?,?)
                """, (
                    u["id"],
                    p["id"],
                    qty,
                    p["price"] * qty,
                    order_address,
                    "Placed",
                    delivery_method,
                    phone
                ))

                # Reduce product stock
                con.execute("""
                    UPDATE products
                    SET stock=stock-?
                    WHERE id=?
                """, (qty, p["id"]))

                placed_count += 1

            if placed_count == 0:

                con.rollback()
                con.close()

                flash("No orders placed. Please check product stock.")
                return redirect(url_for("cart"))

            con.commit()
            con.close()

            session["cart"] = {}

            flash(
                "Order placed successfully! Payment method: Cash on Delivery."
            )

            return redirect(url_for("dashboard"))

        except Exception:

            con.rollback()
            con.close()

            flash("Something went wrong while placing your order.")
            return redirect(url_for("checkout"))

    con.close()

    return render_template("checkout.html")


# ==========================================
# PRODUCT DETAILS
# ==========================================

@app.route("/product/<int:pid>")
def product(pid):

    con = db()

    p = con.execute("""
        SELECT products.*, users.name AS shop
        FROM products
        LEFT JOIN users ON users.id=products.vendor_id
        WHERE products.id=?
    """, (pid,)).fetchone()

    con.close()

    if not p:
        return "Product not found.", 404

    return render_template("product.html", p=p)


# ==========================================
# RUN APPLICATION
# ==========================================

if __name__ == "__main__":

    init_db()

    print("LocalKart is running!")
    print("Open http://127.0.0.1:5000")

    app.run(debug=True)