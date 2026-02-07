from app import app
from models import db, Product, User
from werkzeug.security import generate_password_hash

def seed_database():
    with app.app_context():
        # Clean existing data by dropping all tables and recreating them
        db.reflect()
        db.drop_all()
        db.create_all()

        # Admin user
        if not User.query.filter_by(username='admin').first():
            admin = User(
                username='admin',
                phone='07805088134', # Store phone
                email='admin@almaster.com',
                password_hash=generate_password_hash('admin123'),
                is_admin=True
            )
            db.session.add(admin)

        # Products
        products = [
            Product(
                title="بروش التخرج - اختار الديزاين",
                description="بروش مطلي بالذهب بجودة عالية. يرجى اختيار رقم الديزاين من الصور المرفقة وكتابة الاسم المطلوب.",
                price=15000.0,
                category="بروشات",
                grad_year="2026",
                can_customize_name=True,
                image_url="https://images.unsplash.com/photo-1523050853063-bd388f675f53?q=80&w=600",
                stock=1000
            ),
            Product(
                title="وشاح التخرج الملكي",
                description="وشاح تخرج مخملي فاخر قابل للتخصيص بالاسم.",
                price=30000.0,
                category="وشاحات",
                grad_year="2026",
                can_customize_name=True,
                image_url="https://images.unsplash.com/photo-1627556704290-2b1f5853ff78?q=80&w=600",
                stock=500
            ),
            Product(
                title="قبعة التخرج الفاخرة",
                description="قبعة تخرج بجودة ممتازة مع تطريز سنة التخرج.",
                price=25000.0,
                category="قبعات",
                grad_year="2026",
                can_customize_name=False,
                image_url="https://images.unsplash.com/photo-1541178735423-479693dbba0e?q=80&w=600",
                stock=500
            )
        ]
        
        for p in products:
            db.session.add(p)
        
        db.session.commit()
        print("تم تحديث قاعدة البيانات بنجاح!")

if __name__ == "__main__":
    seed_database()
