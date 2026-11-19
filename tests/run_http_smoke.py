"""Black-box API smoke test against a running MySQL-backed API.

Start the server first, then run `.venv/bin/python tests/run_http_smoke.py`.
The script creates test rows and soft-deletes/cancels them at the end.
"""
import json
import os
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:8000").rstrip("/")
ADMIN_TOKEN = None
STAFF_TOKEN = None
PRODUCT_ID = None
ORDER_ID = None
STAFF_ID = None


def call(method, path, body=None, token=None, expected=200):
    headers = {"Accept": "application/json"}
    if body is not None:
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = Request(
        BASE_URL + path,
        data=None if body is None else json.dumps(body).encode("utf-8"),
        headers=headers,
        method=method,
    )
    try:
        with urlopen(request, timeout=10) as response:
            status, raw = response.status, response.read()
    except HTTPError as error:
        status, raw = error.code, error.read()
    except URLError as error:
        raise RuntimeError(f"Cannot reach {BASE_URL}: {error}") from error
    data = json.loads(raw) if raw else None
    assert status == expected, f"{method} {path}: expected {expected}, got {status}: {data}"
    print(f"PASS {method} {path} -> {status}")
    return data


def run():
    global ADMIN_TOKEN, STAFF_TOKEN, PRODUCT_ID, ORDER_ID, STAFF_ID
    stamp = str(int(time.time()))
    staff_username = f"api-smoke-{stamp}"

    health = call("GET", "/api/health")
    assert health["status"] == "ok" and health["database"] == "connected"
    categories = call("GET", "/api/categories")
    assert len(categories) == 7

    admin = call("POST", "/api/auth/login", {"username": "admin", "password": "Admin@123"})
    staff = call("POST", "/api/auth/login", {"username": "staff", "password": "Staff@123"})
    ADMIN_TOKEN, STAFF_TOKEN = admin["access_token"], staff["access_token"]
    me = call("GET", "/api/auth/me", token=STAFF_TOKEN)
    assert me["role"] == "staff"
    call("GET", "/api/orders", expected=401)
    call("GET", "/api/admin/stats/summary", token=STAFF_TOKEN, expected=403)

    found = call("GET", "/api/menu?q=Santorini")
    assert len(found) >= 1
    order_product = found[0]

    created = call(
        "POST", "/api/admin/menu",
        {"name": f"API Smoke {stamp}", "description": "temporary test item", "price": 10000,
         "image_url": "", "tag": "test", "category_code": "coffee", "is_available": True},
        ADMIN_TOKEN, 201,
    )
    PRODUCT_ID = created["id"]
    updated = call(
        "PUT", f"/api/admin/menu/{PRODUCT_ID}",
        {"name": f"API Smoke Updated {stamp}", "description": "updated", "price": 12000,
         "image_url": "", "tag": "test", "category_code": "coffee", "is_available": True},
        ADMIN_TOKEN,
    )
    assert updated["price"] == 12000

    order = call(
        "POST", "/api/orders",
        {"order_type": "takeaway", "customer_name": "API smoke", "payment_method": "cash",
         "cash_received": 100000, "discount": 1000,
         "items": [{"product_id": order_product["id"], "quantity": 2,
                    "options": [{"name": "size", "value": "L", "price": 5000}]}]},
        STAFF_TOKEN, 201,
    )
    ORDER_ID = order["id"]
    assert order["subtotal"] == (order_product["price"] + 5000) * 2
    assert order["total"] == order["subtotal"] - order["discount"]
    changed = call("PATCH", f"/api/orders/{ORDER_ID}/status", {"status": "preparing"}, STAFF_TOKEN)
    assert changed["status"] == "preparing"
    orders = call("GET", "/api/orders", token=STAFF_TOKEN)
    assert any(row["id"] == ORDER_ID for row in orders)

    summary = call("GET", "/api/admin/stats/summary", token=ADMIN_TOKEN)
    assert summary["order_count"] >= 1 and summary["revenue"] >= order["total"]
    assert len(call("GET", "/api/admin/stats/daily?days=7", token=ADMIN_TOKEN)) == 7
    call("GET", "/api/admin/stats/top-products", token=ADMIN_TOKEN)
    call("GET", "/api/admin/staff", token=ADMIN_TOKEN)

    new_staff = call(
        "POST", "/api/admin/staff",
        {"username": staff_username, "full_name": "API Smoke Staff",
         "password": "TestPass@123", "role": "staff"},
        ADMIN_TOKEN, 201,
    )
    STAFF_ID = new_staff["id"]
    disabled = call("PATCH", f"/api/admin/staff/{STAFF_ID}/active?active=false", token=ADMIN_TOKEN)
    assert disabled["is_active"] is False
    call("DELETE", f"/api/admin/menu/{PRODUCT_ID}", token=ADMIN_TOKEN)
    PRODUCT_ID = None
    call("DELETE", f"/api/admin/orders/{ORDER_ID}", token=ADMIN_TOKEN)
    ORDER_ID = None
    print("All MySQL-backed API smoke checks passed.")


try:
    run()
finally:
    # Best-effort cleanup keeps test accounts and test menu items from accumulating.
    if ADMIN_TOKEN and PRODUCT_ID:
        try:
            call("DELETE", f"/api/admin/menu/{PRODUCT_ID}", token=ADMIN_TOKEN)
        except Exception:
            pass
    if ADMIN_TOKEN and ORDER_ID:
        try:
            call("DELETE", f"/api/admin/orders/{ORDER_ID}", token=ADMIN_TOKEN)
        except Exception:
            pass
    if ADMIN_TOKEN and STAFF_ID:
        try:
            call("PATCH", f"/api/admin/staff/{STAFF_ID}/active?active=false", token=ADMIN_TOKEN)
        except Exception:
            pass
