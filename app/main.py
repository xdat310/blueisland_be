import json
from datetime import date, datetime, time, timedelta
from uuid import uuid4
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload
from app.config import settings
from app.database import Base, SessionLocal, engine, get_db
from app.models import CafeOrder, Category, OrderItem, Product, StaffShift, User
from app.schemas import LoginInput, OrderInput, ProductInput, StatusInput, TokenOut, UserOut
from app.security import current_user, make_token, require_admin, verify_password, hash_password
from app.seed import seed_database

app = FastAPI(title=settings.app_name, version="1.0.0", description="API quản lý quán café BlueIsland")
app.add_middleware(CORSMiddleware, allow_origins=settings.allowed_origins or ["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])


@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        seed_database(db)


def product_out(p: Product):
    return {"id": p.id, "name": p.name, "description": p.description, "price": p.price, "image_url": p.image_url, "tag": p.tag, "category_code": p.category.code, "category_name": p.category.name, "is_available": p.is_available}


def order_out(o: CafeOrder):
    return {"id": o.id, "order_code": o.order_code, "order_type": o.order_type, "table_code": o.table_code, "customer_name": o.customer_name, "student_id": o.student_id, "payment_method": o.payment_method, "cash_received": o.cash_received, "subtotal": o.subtotal, "discount": o.discount, "total": o.total, "status": o.status, "staff_id": o.staff_id, "staff_name": o.staff.full_name if o.staff else "", "created_at": o.created_at.isoformat() if o.created_at else None, "items": [{"product_id": i.product_id, "name": i.product_name, "quantity": i.quantity, "unit_price": i.unit_price, "options": json.loads(i.options_json), "line_total": i.line_total} for i in o.items]}


@app.get("/api/health")
def health(db: Session = Depends(get_db)):
    db.execute(func.now())
    return {"status": "ok", "service": settings.app_name, "database": "connected"}


@app.post("/api/auth/login", response_model=TokenOut)
def login(payload: LoginInput, db: Session = Depends(get_db)):
    user = db.query(User).filter((User.username == payload.username) | (User.email == payload.username) | (User.employee_code == payload.username)).first()
    if not user or not user.is_active or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Tên đăng nhập hoặc mật khẩu không đúng")
    token = make_token(user)
    # Keep the canonical OAuth-style fields and provide the aliases expected by
    # the current BlueIsland FE login snippet while it is being connected.
    profile = {
        "code": user.employee_code or user.username.upper(),
        "name": user.full_name,
        "email": user.email,
        "shift": "Toàn thời gian",
    }
    return {
        "access_token": token,
        "token": token,
        "role": user.role,
        "isStaff": user.role == "staff",
        "staffProfile": profile if user.role in ("admin", "staff") else None,
        "user": user,
    }


@app.get("/api/auth/me", response_model=UserOut)
def me(user: User = Depends(current_user)):
    return user


@app.get("/api/categories")
def categories(db: Session = Depends(get_db)):
    return [{"id": c.id, "code": c.code, "name": c.name} for c in db.query(Category).order_by(Category.id).all()]


@app.get("/api/menu")
def menu(q: str = "", category: str | None = None, available: bool = True, db: Session = Depends(get_db)):
    query = db.query(Product).join(Category).options(joinedload(Product.category))
    if available:
        query = query.filter(Product.is_available.is_(True))
    if category and category != "all":
        query = query.filter(Category.code == category)
    if q.strip():
        query = query.filter(Product.name.ilike(f"%{q.strip()}%"))
    return [product_out(p) for p in query.order_by(Product.id).all()]


@app.get("/api/menu/{product_id}")
def get_product(product_id: int, db: Session = Depends(get_db)):
    p = db.query(Product).options(joinedload(Product.category)).get(product_id)
    if not p: raise HTTPException(404, "Không tìm thấy món")
    return product_out(p)


@app.post("/api/admin/menu", status_code=201)
def create_product(payload: ProductInput, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    cat = db.query(Category).filter_by(code=payload.category_code).first()
    if not cat: raise HTTPException(400, "Danh mục không hợp lệ")
    p = Product(**payload.model_dump(exclude={"category_code"}), category=cat)
    db.add(p); db.commit(); db.refresh(p)
    return product_out(p)


@app.put("/api/admin/menu/{product_id}")
def update_product(product_id: int, payload: ProductInput, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    p = db.get(Product, product_id); cat = db.query(Category).filter_by(code=payload.category_code).first()
    if not p: raise HTTPException(404, "Không tìm thấy món")
    if not cat: raise HTTPException(400, "Danh mục không hợp lệ")
    for key, value in payload.model_dump(exclude={"category_code"}).items(): setattr(p, key, value)
    p.category = cat; db.commit(); db.refresh(p)
    return product_out(p)


@app.delete("/api/admin/menu/{product_id}")
def delete_product(product_id: int, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    p = db.get(Product, product_id)
    if not p: raise HTTPException(404, "Không tìm thấy món")
    p.is_available = False; db.commit()
    return {"message": "Đã ẩn món khỏi thực đơn"}


@app.post("/api/orders", status_code=201)
def create_order(payload: OrderInput, db: Session = Depends(get_db), user: User = Depends(current_user)):
    if payload.order_type not in ("dine-in", "takeaway") or payload.payment_method not in ("cash", "transfer"):
        raise HTTPException(422, "Loại đơn hoặc phương thức thanh toán không hợp lệ")
    ids = {line.product_id for line in payload.items}
    products = {p.id: p for p in db.query(Product).filter(Product.id.in_(ids), Product.is_available.is_(True)).all()}
    if len(products) != len(ids): raise HTTPException(400, "Có món không tồn tại hoặc đã ngừng bán")
    subtotal = sum(products[line.product_id].price * line.quantity for line in payload.items)
    discount = min(payload.discount, subtotal); total = subtotal - discount
    if payload.payment_method == "cash" and payload.cash_received < total:
        raise HTTPException(400, "Tiền khách đưa chưa đủ thanh toán")
    order = CafeOrder(order_code=f"BI-{datetime.now():%y%m%d}-{uuid4().hex[:6].upper()}", order_type=payload.order_type,
        table_code=payload.table_code if payload.order_type == "dine-in" else None,
        customer_name=payload.customer_name or "Khách lẻ", student_id=payload.student_id,
        payment_method=payload.payment_method, cash_received=payload.cash_received, subtotal=subtotal,
        discount=discount, total=total, status="waiting", staff_id=user.id)
    for line in payload.items:
        product = products[line.product_id]
        options_cost = sum(max(0, int(opt.get("price", 0))) for opt in line.options)
        unit = product.price + options_cost
        order.items.append(OrderItem(product_id=product.id, product_name=product.name, quantity=line.quantity,
            unit_price=unit, options_json=json.dumps(line.options, ensure_ascii=False), line_total=unit * line.quantity))
    # Tính thêm topping hợp lệ gửi từ POS vào tổng, nhưng tổng giá từng món vẫn lấy từ database.
    subtotal = sum(i.line_total for i in order.items); order.subtotal = subtotal
    order.discount = min(payload.discount, subtotal); order.total = subtotal - order.discount
    if order.payment_method == "cash" and order.cash_received < order.total: raise HTTPException(400, "Tiền khách đưa chưa đủ thanh toán")
    db.add(order); db.commit(); db.refresh(order)
    return order_out(order)


@app.get("/api/orders")
def list_orders(status: str | None = None, from_date: date | None = None, to_date: date | None = None,
                db: Session = Depends(get_db), _: User = Depends(current_user)):
    q = db.query(CafeOrder).options(joinedload(CafeOrder.staff), joinedload(CafeOrder.items)).order_by(CafeOrder.created_at.desc())
    if status: q = q.filter(CafeOrder.status == status)
    if from_date: q = q.filter(CafeOrder.created_at >= datetime.combine(from_date, time.min))
    if to_date: q = q.filter(CafeOrder.created_at < datetime.combine(to_date + timedelta(days=1), time.min))
    return [order_out(o) for o in q.limit(500).all()]


@app.patch("/api/orders/{order_id}/status")
def set_order_status(order_id: int, payload: StatusInput, db: Session = Depends(get_db), _: User = Depends(current_user)):
    allowed = {"waiting", "preparing", "ready", "completed", "cancelled"}
    if payload.status not in allowed: raise HTTPException(422, "Trạng thái không hợp lệ")
    o = db.query(CafeOrder).options(joinedload(CafeOrder.staff), joinedload(CafeOrder.items)).get(order_id)
    if not o: raise HTTPException(404, "Không tìm thấy đơn")
    o.status = payload.status; db.commit(); db.refresh(o)
    return order_out(o)


@app.delete("/api/admin/orders/{order_id}")
def cancel_order(order_id: int, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    o = db.get(CafeOrder, order_id)
    if not o: raise HTTPException(404, "Không tìm thấy đơn")
    if o.status == "completed": raise HTTPException(400, "Không thể hủy đơn đã hoàn thành")
    o.status = "cancelled"; db.commit()
    return {"message": "Đã hủy đơn"}


@app.get("/api/admin/stats/summary")
def stats_summary(from_date: date | None = None, to_date: date | None = None, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    start = datetime.combine(from_date or date.today(), time.min)
    end = datetime.combine((to_date or date.today()) + timedelta(days=1), time.min)
    rows = db.query(CafeOrder).filter(CafeOrder.created_at >= start, CafeOrder.created_at < end).all()
    valid = [o for o in rows if o.status != "cancelled"]
    return {"from_date": start.date(), "to_date": (end - timedelta(days=1)).date(), "order_count": len(valid),
        "cancelled_count": len(rows)-len(valid), "revenue": sum(o.total for o in valid),
        "cash_revenue": sum(o.total for o in valid if o.payment_method == "cash"),
        "transfer_revenue": sum(o.total for o in valid if o.payment_method == "transfer"),
        "active_orders": sum(o.status in ("waiting", "preparing", "ready") for o in valid)}


@app.get("/api/admin/stats/daily")
def stats_daily(days: int = Query(default=7, ge=1, le=90), db: Session = Depends(get_db), _: User = Depends(require_admin)):
    today = date.today(); start = datetime.combine(today - timedelta(days=days-1), time.min)
    rows = db.query(CafeOrder).filter(CafeOrder.created_at >= start, CafeOrder.status != "cancelled").all()
    buckets = {}
    for i in range(days): buckets[(today - timedelta(days=days-1-i)).isoformat()] = {"date": (today-timedelta(days=days-1-i)).isoformat(), "orders": 0, "revenue": 0}
    for o in rows:
        key = o.created_at.date().isoformat()
        if key in buckets: buckets[key]["orders"] += 1; buckets[key]["revenue"] += o.total
    return list(buckets.values())


@app.get("/api/admin/stats/top-products")
def top_products(limit: int = Query(default=10, ge=1, le=50), db: Session = Depends(get_db), _: User = Depends(require_admin)):
    rows = db.query(OrderItem.product_name, func.sum(OrderItem.quantity).label("quantity"), func.sum(OrderItem.line_total).label("revenue"))\
        .join(CafeOrder).filter(CafeOrder.status != "cancelled").group_by(OrderItem.product_name).order_by(func.sum(OrderItem.quantity).desc()).limit(limit).all()
    return [{"name": r.product_name, "quantity": int(r.quantity), "revenue": int(r.revenue)} for r in rows]


@app.get("/api/admin/staff")
def list_staff(db: Session = Depends(get_db), _: User = Depends(require_admin)):
    return [{"id": u.id, "username": u.username, "full_name": u.full_name, "email": u.email, "role": u.role, "employee_code": u.employee_code, "is_active": u.is_active} for u in db.query(User).order_by(User.id).all()]


@app.post("/api/admin/staff", status_code=201)
def create_staff(payload: dict, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    required = ("username", "full_name", "password")
    if any(not payload.get(k) for k in required): raise HTTPException(422, "username, full_name và password là bắt buộc")
    if payload.get("role", "staff") not in ("admin", "staff"): raise HTTPException(422, "role phải là admin hoặc staff")
    if db.query(User).filter_by(username=payload["username"]).first(): raise HTTPException(409, "Tên đăng nhập đã tồn tại")
    u = User(username=payload["username"], full_name=payload["full_name"], email=payload.get("email"), employee_code=payload.get("employee_code"), role=payload.get("role", "staff"), password_hash=hash_password(payload["password"]))
    db.add(u); db.commit(); db.refresh(u)
    return {"id": u.id, "username": u.username, "full_name": u.full_name, "role": u.role, "employee_code": u.employee_code}


@app.patch("/api/admin/staff/{user_id}/active")
def set_staff_active(user_id: int, active: bool, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    u = db.get(User, user_id)
    if not u: raise HTTPException(404, "Không tìm thấy tài khoản")
    u.is_active = active; db.commit()
    return {"id": u.id, "is_active": u.is_active}

@app.patch("/api/admin/staff/{user_id}")
def update_staff(user_id: int, payload: dict, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    u = db.get(User, user_id)
    if not u:
        raise HTTPException(404, "Không tìm thấy tài khoản")
    if payload.get("full_name"):
        u.full_name = str(payload["full_name"]).strip()
    if "email" in payload:
        u.email = str(payload["email"]).strip() or None
    if payload.get("password"):
        pw = str(payload["password"]).strip()
        if len(pw) < 4:
            raise HTTPException(422, "Mật khẩu phải có ít nhất 4 ký tự")
        u.password_hash = hash_password(pw)
    db.commit()
    db.refresh(u)
    return {
        "id": u.id,
        "username": u.username,
        "full_name": u.full_name,
        "email": u.email,
        "role": u.role,
        "employee_code": u.employee_code,
        "is_active": u.is_active,
    }


@app.post("/api/admin/staff/{user_id}/reset-password")
def reset_staff_password(user_id: int, payload: dict, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    u = db.get(User, user_id)
    if not u:
        raise HTTPException(404, "Không tìm thấy tài khoản")
    pw = str(payload.get("password") or "").strip()
    if len(pw) < 4:
        raise HTTPException(422, "Mật khẩu phải có ít nhất 4 ký tự")
    u.password_hash = hash_password(pw)
    db.commit()
    return {
        "ok": True,
        "staff": {
            "id": str(u.id),
            "code": u.employee_code or u.username.upper(),
            "name": u.full_name,
        },
    }

@app.post("/api/auth/register", status_code=201, response_model=TokenOut)
def register_customer(payload: dict, db: Session = Depends(get_db)):
    full_name = str(payload.get("full_name") or payload.get("name") or "").strip()
    email_raw = str(payload.get("email") or "").strip().lower()
    email = email_raw or None
    username = str(payload.get("username") or email_raw or "").strip().lower()
    password = str(payload.get("password") or "").strip()

    if not full_name or not username or not password:
        raise HTTPException(422, "Họ tên, tên đăng nhập và mật khẩu là bắt buộc")
    if len(password) < 6:
        raise HTTPException(422, "Mật khẩu phải có ít nhất 6 ký tự")
    if db.query(User).filter(User.username == username).first():
        raise HTTPException(409, "Tên đăng nhập đã tồn tại")
    if email and db.query(User).filter(User.email == email).first():
        raise HTTPException(409, "Email đã được đăng ký")

    u = User(
        username=username,
        full_name=full_name,
        email=email,
        role="customer",
        is_active=True,
        password_hash=hash_password(password),
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    token = make_token(u)
    return {
        "access_token": token,
        "token": token,
        "role": "customer",
        "isStaff": False,
        "staffProfile": None,
        "user": u,
    }


@app.get("/api/customer/orders")
def list_customer_orders(db: Session = Depends(get_db), user: User = Depends(current_user)):
    rows = (
        db.query(CafeOrder)
        .options(joinedload(CafeOrder.staff), joinedload(CafeOrder.items))
        .filter(CafeOrder.staff_id == user.id)
        .order_by(CafeOrder.created_at.desc())
        .limit(100)
        .all()
    )
    return [order_out(o) for o in rows]

@app.post("/api/staff/shifts/close", status_code=201)
def close_staff_shift(payload: dict, db: Session = Depends(get_db), user: User = Depends(current_user)):
    ended_at = datetime.now()
    ts = payload.get("started_at_ts")
    if ts:
        try:
            started_at = datetime.fromtimestamp(float(ts) / 1000.0)
        except Exception:
            started_at = datetime.combine(date.today(), time.min)
    else:
        started_at = datetime.combine(date.today(), time.min)

    rows = (
        db.query(CafeOrder)
        .filter(
            CafeOrder.staff_id == user.id,
            CafeOrder.status != "cancelled",
            CafeOrder.created_at >= started_at,
            CafeOrder.created_at <= ended_at,
        )
        .all()
    )
    order_count = len(rows)
    cash_total = sum(o.total for o in rows if o.payment_method == "cash")
    transfer_total = sum(o.total for o in rows if o.payment_method == "transfer")

    sh = StaffShift(
        staff_id=user.id,
        started_at=started_at,
        ended_at=ended_at,
        order_count=order_count,
        cash_total=cash_total,
        transfer_total=transfer_total,
    )
    db.add(sh)
    db.commit()
    db.refresh(sh)
    return {
        "id": sh.id,
        "staff_code": user.employee_code or user.username.upper(),
        "staff_name": user.full_name,
        "started_at": sh.started_at.isoformat(),
        "ended_at": sh.ended_at.isoformat(),
        "order_count": sh.order_count,
        "cash_total": sh.cash_total,
        "transfer_total": sh.transfer_total,
    }


@app.get("/api/admin/shifts")
def list_closed_shifts(db: Session = Depends(get_db), _: User = Depends(require_admin)):
    rows = (
        db.query(StaffShift)
        .options(joinedload(StaffShift.staff))
        .order_by(StaffShift.ended_at.desc())
        .limit(100)
        .all()
    )
    return [
        {
            "id": sh.id,
            "staff_code": (sh.staff.employee_code or sh.staff.username.upper()) if sh.staff else f"NV#{sh.staff_id}",
            "staff_name": sh.staff.full_name if sh.staff else "Nhân viên",
            "started_at": sh.started_at.isoformat() if sh.started_at else None,
            "ended_at": sh.ended_at.isoformat() if sh.ended_at else None,
            "order_count": sh.order_count,
            "cash_total": sh.cash_total,
            "transfer_total": sh.transfer_total,
        }
        for sh in rows
    ]


# Phục vụ trực tiếp Frontend trên cùng cổng 5500 (đặt cuối file để ưu tiên /api/*)
from pathlib import Path as _Path
from fastapi.staticfiles import StaticFiles

_fe_dir = _Path(r"C:\Users\PC\OneDrive\Desktop\BlueIsland fe")
if _fe_dir.is_dir():
    app.mount("/", StaticFiles(directory=str(_fe_dir), html=True), name="frontend")

