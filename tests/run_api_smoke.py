"""Exercise FastAPI routes against an isolated in-memory SQLite test database.

This smoke test checks API behavior without opening a network port. MySQL
connectivity is still checked separately with GET /api/health and Postman.
Run with: .venv/bin/python tests/run_api_smoke.py
"""
import asyncio
import json
from pathlib import Path
import sys
from urllib.parse import urlsplit

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database import Base, get_db
from app.main import app
from app.seed import seed_database


test_engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSession = sessionmaker(bind=test_engine, autoflush=False, autocommit=False)
Base.metadata.create_all(bind=test_engine)
with TestSession() as session:
    seed_database(session)


def override_get_db():
    with TestSession() as session:
        yield session


app.dependency_overrides[get_db] = override_get_db


async def asgi_request(method, url, body=None, token=None):
    parsed = urlsplit(url)
    payload = b"" if body is None else json.dumps(body).encode("utf-8")
    headers = []
    if body is not None:
        headers.append((b"content-type", b"application/json"))
    if token:
        headers.append((b"authorization", f"Bearer {token}".encode("ascii")))
    scope = {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.3"},
        "http_version": "1.1",
        "method": method,
        "scheme": "http",
        "path": parsed.path,
        "raw_path": parsed.path.encode("utf-8"),
        "query_string": parsed.query.encode("ascii"),
        "root_path": "",
        "headers": headers,
        "client": ("testclient", 50000),
        "server": ("testserver", 80),
    }
    messages = []
    sent_request = False

    async def receive():
        nonlocal sent_request
        if not sent_request:
            sent_request = True
            return {"type": "http.request", "body": payload, "more_body": False}
        return {"type": "http.disconnect"}

    async def send(message):
        messages.append(message)

    await app(scope, receive, send)
    start = next(message for message in messages if message["type"] == "http.response.start")
    content = b"".join(
        message.get("body", b"")
        for message in messages
        if message["type"] == "http.response.body"
    )
    decoded = json.loads(content) if content else None
    return start["status"], decoded


def request(method, path, body=None, token=None):
    return asyncio.run(asgi_request(method, path, body, token))


def check(label, expected, result):
    status, body = result
    assert status == expected, f"{label}: expected {expected}, got {status}: {body}"
    print(f"PASS {label} ({status})")
    return body


BASE = "http://testserver"

try:
    check("health route with SQLite test override", 200, request("GET", BASE + "/api/health"))
    categories = check("category listing", 200, request("GET", BASE + "/api/categories"))
    assert len(categories) == 7, f"expected 7 categories, got {len(categories)}"
    print("PASS seven seeded categories")

    admin = check(
        "admin login", 200,
        request("POST", BASE + "/api/auth/login", {"username": "admin", "password": "Admin@123"}),
    )
    staff = check(
        "staff login", 200,
        request("POST", BASE + "/api/auth/login", {"username": "staff", "password": "Staff@123"}),
    )
    admin_token, staff_token = admin["access_token"], staff["access_token"]
    me = check("JWT current user", 200, request("GET", BASE + "/api/auth/me", token=staff_token))
    assert me["role"] == "staff"
    check("orders requires authentication", 401, request("GET", BASE + "/api/orders"))
    check("staff is denied admin route", 403, request("GET", BASE + "/api/admin/stats/summary", token=staff_token))

    products = check("search menu", 200, request("GET", BASE + "/api/menu?q=Santorini"))
    assert len(products) == 2
    product = products[0]
    created = check(
        "admin creates menu item", 201,
        request("POST", BASE + "/api/admin/menu", {
            "name": "API Smoke Test Item", "description": "test", "price": 10000,
            "image_url": "", "tag": "test", "category_code": "coffee", "is_available": True,
        }, admin_token),
    )
    product_id = created["id"]
    updated = check(
        "admin updates menu item", 200,
        request("PUT", f"{BASE}/api/admin/menu/{product_id}", {
            "name": "API Smoke Test Item Updated", "description": "updated", "price": 12000,
            "image_url": "", "tag": "test", "category_code": "coffee", "is_available": True,
        }, admin_token),
    )
    assert updated["price"] == 12000

    order = check(
        "staff creates order", 201,
        request("POST", BASE + "/api/orders", {
            "order_type": "takeaway", "customer_name": "API Smoke Test",
            "payment_method": "cash", "cash_received": 100000, "discount": 1000,
            "items": [{"product_id": product["id"], "quantity": 2,
                       "options": [{"name": "size", "value": "L", "price": 5000}]}],
        }, staff_token),
    )
    assert order["subtotal"] == (product["price"] + 5000) * 2
    assert order["total"] == order["subtotal"] - 1000
    order_id = order["id"]
    status_body = check(
        "staff changes order status", 200,
        request("PATCH", f"{BASE}/api/orders/{order_id}/status", {"status": "preparing"}, staff_token),
    )
    assert status_body["status"] == "preparing"
    listed = check("staff lists orders", 200, request("GET", BASE + "/api/orders", token=staff_token))
    assert any(row["id"] == order_id for row in listed)

    summary = check("admin summary report", 200, request("GET", BASE + "/api/admin/stats/summary", token=admin_token))
    assert summary["order_count"] >= 1 and summary["revenue"] >= order["total"]
    daily = check("admin daily report", 200, request("GET", BASE + "/api/admin/stats/daily?days=7", token=admin_token))
    assert len(daily) == 7
    check("admin top products report", 200, request("GET", BASE + "/api/admin/stats/top-products", token=admin_token))

    new_staff = check(
        "admin creates staff account", 201,
        request("POST", BASE + "/api/admin/staff", {
            "username": "api-smoke-user", "full_name": "API Smoke User",
            "password": "TestPass@123", "role": "staff",
        }, admin_token),
    )
    inactive = check(
        "admin disables staff account", 200,
        request("PATCH", f"{BASE}/api/admin/staff/{new_staff['id']}/active?active=false", token=admin_token),
    )
    assert inactive["is_active"] is False
    check(
        "admin soft deletes test menu item", 200,
        request("DELETE", f"{BASE}/api/admin/menu/{product_id}", token=admin_token),
    )
    hidden = check("hidden menu item remains retrievable", 200, request("GET", f"{BASE}/api/menu/{product_id}"))
    assert hidden["is_available"] is False

    print("API smoke checks passed against isolated SQLite test database.")
finally:
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=test_engine)
    test_engine.dispose()
