from app import app
from models import db, Product

with app.app_context():
    products = Product.query.all()
    print(f"Total products: {len(products)}")
    for p in products:
        print(f"ID: {p.id} | Title: {p.title}")
