from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(100)) # Graduation Products, Academic Recognition, etc.
    university = db.Column(db.String(200)) # جامعة كربلاء, etc.
    college = db.Column(db.String(200)) # كلية الطب, etc.
    grad_year = db.Column(db.String(10)) # 2026, 2025, etc.
    image_url = db.Column(db.String(500))
    stock = db.Column(db.Integer, default=0)
    
    # Customization flags
    can_customize_name = db.Column(db.Boolean, default=False)
    can_customize_photo = db.Column(db.Boolean, default=False)
    can_select_year = db.Column(db.Boolean, default=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    total_price = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(50), default='قيد الانتظار') # Pending, Paid, Shipped, Delivered
    
    # Customer Details
    full_name = db.Column(db.String(200))
    phone = db.Column(db.String(20))
    province = db.Column(db.String(100))
    address = db.Column(db.String(500))
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    items = db.relationship('OrderItem', backref='order', lazy=True)

class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)
    
    # Customization Data
    custom_name = db.Column(db.String(200))
    custom_year = db.Column(db.String(10))
    custom_photo_url = db.Column(db.String(500))
