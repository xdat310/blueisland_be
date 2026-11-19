from sqlalchemy.orm import Session
from app.models import Category, Product, User
from app.security import hash_password

CATEGORIES = {
    "special": "Đặc biệt", "espresso": "Café máy", "coffee": "Café",
    "tea": "Trà", "ice": "Đá xay", "juice": "Sinh tố, Nước ép", "other": "Đồ uống khác",
}
MENU = {
    "special": [("Santorini blue soda", "Soda việt quất xanh mát mang phong vị biển đảo Santorini đặc trưng.", 25000, "Signature", "https://images.unsplash.com/photo-1513558161293-cdaf765ed2fd?auto=format&fit=crop&w=600&q=75"), ("Santorini dream", "Hương vị biển nhiệt đới mộng mơ mát lạnh, công thức độc quyền của quán.", 25000, "Đặc biệt", "https://images.unsplash.com/photo-1536935338788-846bb9981813?auto=format&fit=crop&w=600&q=75")],
    "espresso": [("Capuchino", "Espresso thơm đậm hòa quyện cùng lớp bọt sữa dày mịn.", 40000, "Café máy", "https://images.unsplash.com/photo-1572442388796-11668a67e53d?auto=format&fit=crop&w=600&q=75"), ("Latte", "Espresso cùng sữa tươi đánh mịn mượt.", 40000, "In hình nghệ thuật", "https://images.unsplash.com/photo-1553962311-62f2471b159d?auto=format&fit=crop&w=600&q=75"), ("Americano", "Espresso Arabica pha loãng thanh nhẹ.", 35000, None, "https://images.unsplash.com/photo-1514432324607-a09d9b4aefdd?auto=format&fit=crop&w=600&q=75"), ("Mocha", "Cà phê hòa quyện cùng chocolate.", 40000, None, "https://images.unsplash.com/photo-1578314675249-a6910f80cc4e?auto=format&fit=crop&w=600&q=75")],
    "coffee": [("Café đen nóng/đá", "Cà phê phin truyền thống thơm nồng.", 20000, None, "https://images.unsplash.com/photo-1558557019-051d86ef616f?auto=format&fit=crop&w=600&q=75"), ("Café nâu nóng/đá", "Cà phê phin hòa cùng sữa đặc.", 20000, None, "https://images.unsplash.com/photo-1517701604599-bb29b565090c?auto=format&fit=crop&w=600&q=75"), ("Bạc xỉu", "Nhiều sữa ít cà phê, béo ngậy ngọt dịu.", 25000, "Yêu thích", "https://images.unsplash.com/photo-1541167760496-1628856ab772?auto=format&fit=crop&w=600&q=75"), ("Café muối", "Cà phê đậm vị phủ lớp kem muối.", 30000, "Best seller", "https://images.unsplash.com/photo-1517256064527-09c73fc73e38?auto=format&fit=crop&w=600&q=75"), ("Café kem trứng", "Kem trứng đánh bông trên nền cà phê đậm đà.", 30000, "Món hot", "https://images.unsplash.com/photo-1509042239860-f550ce710b93?auto=format&fit=crop&w=600&q=75")],
    "tea": [("Trà chanh mật ong", "Chanh tươi quyện mật ong ngọt dịu.", 20000, None, "https://images.unsplash.com/photo-1556679343-c7306c1976bc?auto=format&fit=crop&w=600&q=75"), ("Trà vải hoa nhài", "Hương hoa nhài cùng vị ngọt của trái vải.", 20000, "Thanh mát", "https://images.unsplash.com/photo-1544145945-f90425340c7e?auto=format&fit=crop&w=600&q=75")],
    "ice": [("Matcha đá xay", "Matcha Nhật Bản xay cùng đá và sữa tươi.", 35000, "Yêu thích", "https://images.unsplash.com/photo-1572490122747-3968b75cc699?auto=format&fit=crop&w=600&q=75"), ("Chocolate đá xay", "Chocolate xay mát lạnh, béo ngậy.", 35000, None, "https://images.unsplash.com/photo-1586985289688-ca3cf47d3e6e?auto=format&fit=crop&w=600&q=75"), ("Sữa chua đá xay", "Sữa chua lên men xay tuyết.", 30000, None, "https://images.unsplash.com/photo-1488477181946-6428a0291777?auto=format&fit=crop&w=600&q=75")],
    "juice": [("Nước cam ép", "Cam tươi vắt nguyên chất.", 40000, None, "https://images.unsplash.com/photo-1613478223719-2ab802602423?auto=format&fit=crop&w=600&q=75"), ("Nước ép dứa", "Dứa tươi chín vàng ngọt thanh.", 40000, None, "https://images.unsplash.com/photo-1525385133512-2f3bdd039054?auto=format&fit=crop&w=600&q=75"), ("Nước ép cam cà rốt, cam dứa", "Mix hoa quả tươi tự nhiên.", 40000, "Mix tươi", "https://images.unsplash.com/photo-1621506289937-a8e4df240d0b?auto=format&fit=crop&w=600&q=75"), ("Sinh tố bơ", "Bơ sáp béo ngậy xay cùng sữa.", 35000, "Bổ dưỡng", "https://images.unsplash.com/photo-1541591425126-4e6dcf84b386?auto=format&fit=crop&w=600&q=75"), ("Bơ già dừa non", "Bơ béo bùi và dừa non giòn ngọt.", 35000, "Món mới", "https://images.unsplash.com/photo-1546069901-ba9599a7e63c?auto=format&fit=crop&w=600&q=75")],
    "other": [("Matcha Latte", "Trà xanh Nhật Bản cùng sữa tươi.", 40000, None, "https://images.unsplash.com/photo-1536256263959-770b48d82b0a?auto=format&fit=crop&w=600&q=75"), ("Coco Matcha", "Matcha nguyên chất hòa cùng nước cốt dừa.", 50000, "Đặc sắc", "https://images.unsplash.com/photo-1515823662972-da6a2e4d3002?auto=format&fit=crop&w=600&q=75")],
}


def seed_database(db: Session):
    if not db.query(Category).first():
        categories = {code: Category(code=code, name=name) for code, name in CATEGORIES.items()}
        db.add_all(categories.values())
        db.flush()
        for code, products in MENU.items():
            for name, desc, price, tag, image in products:
                db.add(Product(name=name, description=desc, price=price, tag=tag, image_url=image, category=categories[code]))
    if not db.query(User).filter_by(username="admin").first():
        db.add(User(username="admin", full_name="Quản trị viên BlueIsland", email="admin@blueisland.local", password_hash=hash_password("Admin@123"), role="admin", employee_code="BI-ADMIN"))
    if not db.query(User).filter_by(username="staff").first():
        db.add(User(username="staff", full_name="Nhân viên BlueIsland", email="staff@blueisland.local", password_hash=hash_password("Staff@123"), role="staff", employee_code="BI-001"))
    db.commit()
