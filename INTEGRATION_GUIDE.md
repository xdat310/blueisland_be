# BlueIsland Coffee – Integration Guide

## 📦 Project Status

✅ **Backend (BE)** – FastAPI, fully operational
✅ **Frontend (FE)** – HTML/JS, API integrated  
✅ **GitHub** – Both repos pushed and synced

---

## 🚀 Quick Start

### 1. Backend Setup
```bash
cd blueisland_be
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8001
```

**Health Check:**
```bash
curl http://127.0.0.1:8001/api/health
```

### 2. Frontend Setup
```bash
cd blueisland-fe/blueisland-fe
# Open index.html in browser or use HTTP server
```

---

## 🔐 Default Credentials

**Admin:**
- Username: `admin`
- Password: `Admin@123`

**Staff:**
- Username: `staff`  
- Password: `Staff@123`

---

## 📋 Implemented Endpoints

### Auth
- `POST /api/auth/login` – Login (JWT)
- `GET /api/auth/me` – Current user

### Menu
- `GET /api/menu` – Search/filter menu
- `GET /api/categories` – List categories
- `POST /api/admin/menu` – Create (admin)
- `PUT /api/admin/menu/{id}` – Update (admin)
- `DELETE /api/admin/menu/{id}` – Delete (admin)

### Orders
- `GET /api/orders` – List orders
- `POST /api/orders` – Create order
- `PATCH /api/orders/{id}/status` – Update status

### Admin
- `GET /api/admin/staff` – List staff
- `POST /api/admin/staff` – Create staff
- `GET /api/admin/stats/summary` – Statistics
- `GET /api/admin/stats/daily` – Daily revenue
- `GET /api/admin/stats/top-products` – Top items

---

## 🧪 Testing with Postman

**Collection:** `postman/BlueIsland-API.postman_collection.json`

1. Import into Postman
2. Set `baseUrl` = `http://127.0.0.1:8001`
3. Run in Collection Runner (sequential)
4. All tests pass ✅

---

## 🔧 Frontend API

File: `assets/js/api.js`

```javascript
// Login
const data = await BI_API.auth.login('admin', 'Admin@123');

// Get stats  
const stats = await BI_API.stats.summary();

// Search menu
const items = await BI_API.menu.search('cà phê', 'coffee');

// Create order
const order = await BI_API.orders.create({
  order_type: 'takeaway',
  items: [{ product_id: 1, quantity: 2 }],
  payment_method: 'cash'
});
```

---

## 📂 Project Structure

```
blueisland_be/
├── app/main.py          # API routes
├── app/models.py        # DB models
├── tests/test_main.py   # Unit tests
├── postman/             # API tests
└── requirements.txt

blueisland-fe/
├── index.html           # Homepage
├── admin.html           # Admin dashboard
├── staff.html           # POS
├── assets/js/
│   ├── api.js           # API client
│   ├── main.js          # Login logic
│   ├── admin.js         # Admin UI
│   └── staff.js         # POS logic
```

---

## ✅ What's Working

- User authentication (JWT tokens)
- Menu CRUD operations
- Order creation & tracking
- Admin statistics
- Staff management
- Role-based access (admin/staff)
- MySQL database persistence

---

## 📝 Git Repos

- BE: https://github.com/xdat310/blueisland_be
- FE: https://github.com/xdat310/blueisland-fe

---

**Version:** 1.0.0
