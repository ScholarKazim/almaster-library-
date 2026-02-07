from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import db, User, Product, Order, OrderItem, Category, ProductImage
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
import json
import requests
import random
from datetime import datetime

# Telegram Configuration
TELEGRAM_BOT_TOKEN = "8441247700:AAEta7Yd2lDbTccy3PRWJBtb2Si6T5D5Flw"
TELEGRAM_CHAT_ID = "369981296"

def send_telegram_notification(order):
    try:
        items_str = ""
        for i, item in enumerate(order.items):
            items_str += f"\n{i+1}. {item.product.title}"
            if item.custom_name:
                items_str += f" (ملاحظات: {item.custom_name})"
        
        message = (
            f"🔔 *طلب جديد وارد!* 🔔\n\n"
            f"📍 *رقم الطلب:* #{order.id}\n"
            f"👤 *الزبون:* {order.full_name}\n"
            f"📞 *الهاتف:* {order.phone}\n"
            f"🏠 *العنوان:* {order.province} - {order.address}\n\n"
            f"📦 *المنتجات:* {items_str}\n\n"
            f"💰 *الإجمالي:* {order.total_price:,.0f} د.ع\n"
            f"⏰ *الوقت:* {order.created_at.strftime('%Y/%m/%d %H:%M')}\n\n"
            f"🔗 [عرض الطلبات في الماستر](http://127.0.0.1:5000/admin/orders)"
        )
        
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "Markdown"
        }
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Error sending Telegram notification: {e}")

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here' # In a real app, use an environment variable
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///library.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024 # 16MB

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db.init_app(app)
login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Create database and initial admin if doesn't exist
with app.app_context():
    db.create_all()
    if not User.query.filter_by(username='admin').first():
        admin = User(
            username='admin',
            phone='07805088134',
            email='admin@library.com',
            password_hash=generate_password_hash('admin123'),
            is_admin=True
        )
        db.session.commit()
    
    # Initialize basic categories if they don't exist
    for cat_name in ['بروشات', 'وشاحات', 'قبعات']:
        if not Category.query.filter_by(name=cat_name).first():
            db.session.add(Category(name=cat_name))
    db.session.commit()

# Routes
@app.route('/')
def index():
    category_filter = request.args.get('category')
    search_query = request.args.get('q')
    
    query = Product.query
    if category_filter:
        query = query.filter_by(category=category_filter)
    if search_query:
        query = query.filter(Product.title.contains(search_query))
        
    products = query.order_by(Product.created_at.desc()).all()
    categories = Category.query.all()
    return render_template('index.html', products=products, categories=categories, 
                           current_category=category_filter, search_query=search_query)

@app.route('/product/<int:product_id>')
def product_detail(product_id):
    product = Product.query.get_or_404(product_id)
    return render_template('product_detail.html', product=product)

# Direct login using Name and Phone as ID
@app.route('/api/direct_login', methods=['POST'])
def direct_login():
    data = request.get_json()
    phone = data.get('phone')
    username = data.get('username')

    if not phone or not username:
        return jsonify({'error': 'جميع الحقول مطلوبة'}), 400

    # Find or create user
    user = User.query.filter_by(phone=phone).first()
    if not user:
        user = User(username=username, phone=phone)
        db.session.add(user)
        db.session.commit()
    
    login_user(user, remember=True)
    return jsonify({'success': True})

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/api/get_cart_details', methods=['POST'])
def get_cart_details():
    try:
        # Get JSON data safely
        data = request.get_json(silent=True)
        print(f"DEBUG: Received cart data: {data}")
        
        if not data or not isinstance(data.get('cart'), list):
            return jsonify([])
            
        cart_items = data.get('cart', [])
        product_details = []
        
        for item in cart_items:
            if not isinstance(item, dict):
                continue
                
            raw_id = item.get('id')
            if raw_id is None:
                continue
                
            try:
                product_id = int(raw_id)
                # Use db.session.get for maximum compatibility
                product = db.session.get(Product, product_id)
                
                if product:
                    product_details.append({
                        'id': product.id,
                        'title': product.title,
                        'price': product.price,
                        'image_url': product.image_url,
                        'note': item.get('note', '')
                    })
                else:
                    print(f"DEBUG: Product not found for ID: {product_id}")
            except (ValueError, TypeError) as e:
                print(f"DEBUG: Invalid product ID format: {raw_id}")
                continue
                    
        print(f"DEBUG: Returning {len(product_details)} products")
        return jsonify(product_details)
    except Exception as e:
        import traceback
        print(f"ERROR in get_cart_details: {str(e)}")
        traceback.print_exc()
        return jsonify({"error": "Internal server error"}), 500

@app.route('/cart')
def view_cart():
    return render_template('cart.html')

@app.route('/checkout', methods=['GET', 'POST'])
@login_required
def checkout():
    if request.method == 'POST':
        full_name = request.form.get('full_name')
        phone = request.form.get('phone')
        province = request.form.get('province')
        address = request.form.get('address')
        cart_data = request.form.get('cart_data') # Expected JSON string
        
        if not cart_data:
            flash('Empty cart')
            return redirect(url_for('view_cart'))
            
        cart_items = json.loads(cart_data)
        total_price = 0
        
        # Create order
        order = Order(
            user_id=current_user.id,
            full_name=full_name,
            phone=phone,
            province=province,
            address=address,
            total_price=0 # Will update after summing items
        )
        db.session.add(order)
        db.session.flush() # Get order.id
        
        for item in cart_items:
            product = Product.query.get(item['id'])
            if product:
                order_item = OrderItem(
                    order_id=order.id,
                    product_id=product.id,
                    quantity=1,
                    price=product.price,
                    custom_name=item.get('note')
                )
                total_price += product.price
                db.session.add(order_item)
        
        order.total_price = total_price + 5000 # Adding delivery fee
        db.session.commit()
        
        # Send notification to owner
        send_telegram_notification(order)
        
        # We render a success template
        return render_template('order_success.html', order=order)
        
    return render_template('checkout.html')

@app.route('/profile')
@login_required
def profile():
    orders = Order.query.filter_by(user_id=current_user.id).order_by(Order.created_at.desc()).all()
    return render_template('profile.html', orders=orders)

@app.route('/admin/products')
@login_required
def admin_products():
    if not current_user.is_admin:
        return redirect(url_for('index'))
    products = Product.query.order_by(Product.created_at.desc()).all()
    return render_template('admin/products.html', products=products)

@app.route('/admin/products/add', methods=['GET', 'POST'])
@login_required
def add_product():
    if not current_user.is_admin:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        title = request.form.get('title')
        price = float(request.form.get('price').replace(',', ''))
        category_name = request.form.get('category')
        new_category = request.form.get('new_category')
        description = request.form.get('description')
        
        # Use new category if provided
        final_category = new_category if new_category else category_name
        if final_category and not Category.query.filter_by(name=final_category).first():
            db.session.add(Category(name=final_category))
            db.session.commit()

        files = request.files.getlist('images')
        main_image_url = 'https://via.placeholder.com/600'
        
        new_product = Product(
            title=title,
            price=price,
            category=final_category,
            description=description,
            image_url=main_image_url
        )
        db.session.add(new_product)
        db.session.flush()

        for i, file in enumerate(files):
            if file and file.filename != '':
                filename = secure_filename(f"{new_product.id}_{i}_{file.filename}")
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                img_url = url_for('static', filename='uploads/' + filename)
                if i == 0:
                    new_product.image_url = img_url
                
                db.session.add(ProductImage(product_id=new_product.id, image_url=img_url))
        
        db.session.commit()
        flash('تمت إضافة المنتج بنجاح!')
        return redirect(url_for('admin_products'))
        
    categories = Category.query.all()
    return render_template('admin/add_product.html', categories=categories)

@app.route('/admin/products/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_product(id):
    if not current_user.is_admin:
        return redirect(url_for('index'))
    
    product = Product.query.get_or_404(id)
    
    if request.method == 'POST':
        product.title = request.form.get('title')
        product.price = float(request.form.get('price').replace(',', ''))
        
        category_name = request.form.get('category')
        new_category = request.form.get('new_category')
        final_category = new_category if new_category else category_name
        
        if final_category and not Category.query.filter_by(name=final_category).first():
            db.session.add(Category(name=final_category))
            db.session.commit()
            
        product.category = final_category
        product.description = request.form.get('description')
        
        # Handle new image uploads
        files = request.files.getlist('images')
        if files and files[0].filename != '':
            # If new images are uploaded, we can either append or replace. 
            # For simplicity, let's append these new ones.
            for i, file in enumerate(files):
                filename = secure_filename(f"{product.id}_edit_{random.randint(1000,9999)}_{file.filename}")
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                img_url = url_for('static', filename='uploads/' + filename)
                
                # Update main image if none exists or if it was placeholder
                if i == 0 and ('placeholder' in product.image_url):
                    product.image_url = img_url
                    
                db.session.add(ProductImage(product_id=product.id, image_url=img_url))
        
        db.session.commit()
        flash('تم تحديث المنتج بنجاح!')
        return redirect(url_for('admin_products'))
        
    categories = Category.query.all()
    return render_template('admin/edit_product.html', product=product, categories=categories)

@app.route('/admin/products/delete/<int:id>')
@login_required
def delete_product(id):
    if not current_user.is_admin:
        return redirect(url_for('index'))
    product = Product.query.get_or_404(id)
    db.session.delete(product)
    db.session.commit()
    flash('تم حذف المنتج!')
    return redirect(url_for('admin_products'))

@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if not current_user.is_admin:
        return redirect(url_for('index'))
    
    total_orders = Order.query.count()
    pending_orders = Order.query.filter_by(status='قيد الانتظار').count()
    total_sales = db.session.query(db.func.sum(Order.total_price)).scalar() or 0
    today_orders = Order.query.filter(db.func.date(Order.created_at) == db.func.date(datetime.utcnow())).count()
    
    recent_orders = Order.query.order_by(Order.created_at.desc()).limit(5).all()
    return render_template('admin/dashboard.html', 
                           total_orders=total_orders, 
                           pending_orders=pending_orders,
                           total_sales=total_sales,
                           today_orders=today_orders,
                           recent_orders=recent_orders)

@app.route('/admin/orders')
@login_required
def admin_orders():
    if not current_user.is_admin:
        return redirect(url_for('index'))
    orders = Order.query.order_by(Order.created_at.desc()).all()
    return render_template('admin/orders.html', orders=orders)

@app.route('/admin/orders/status/<int:id>', methods=['POST'])
@login_required
def update_order_status(id):
    if not current_user.is_admin:
        return redirect(url_for('index'))
    order = Order.query.get_or_404(id)
    new_status = request.form.get('status')
    if new_status:
        order.status = new_status
        db.session.commit()
    return redirect(url_for('admin_orders'))

@app.route('/search')
def search():
    query = request.args.get('q', '')
    if query:
        return redirect(url_for('index', q=query))
    return redirect(url_for('index'))

app.secret_key = os.environ.get('SECRET_KEY', 'default_secure_key_1234')

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        
        # قائمة المديرين (5 حسابات ببيانات قوية)
        admins_data = [
            {"username": "AlMaster_Admin1", "phone": "07809424493", "pass": "Master@2026!#Secure1"},
            {"username": "AlMaster_Admin2", "phone": "07713006952", "pass": "Master@2026!#Secure2"},
            {"username": "AlMaster_Admin3", "phone": "07806126915", "pass": "Master@2026!#Secure3"},
            {"username": "AlMaster_Admin4", "phone": "07830739188", "pass": "Master@2026!#Secure4"},
            {"username": "AlMaster_Admin5", "phone": "07805088134", "pass": "Master@2026!#Secure5"}
        ]

        for admin_info in admins_data:
            admin_check = User.query.filter_by(phone=admin_info["phone"]).first()
            if not admin_check:
                new_admin = User(
                    username=admin_info["username"],
                    phone=admin_info["phone"],
                    password=generate_password_hash(admin_info["pass"]),
                    is_admin=True
                )
                db.session.add(new_admin)
        
        db.session.commit()
        print("Success: 5 Secure Admin accounts verified/created.")

    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
