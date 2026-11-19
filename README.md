# BlueIsland Coffee Backend

Backend REST API bằng Python/FastAPI và MySQL cho website BlueIsland Coffee. Hỗ trợ đăng nhập JWT, vai trò `admin`/`staff`, quản lý món, tìm kiếm, POS, đơn hàng và thống kê. Dữ liệu seed khớp 23 món trong `assets/js/menu-data.js` của FE.

## Chạy backend local

- Cài Python 3.10+ (máy hiện tại trong môi trường này có Python 3.9.6) và MySQL Server 8. Có thể cài trên macOS bằng `brew install python@3.12 mysql`, sau đó khởi động MySQL bằng `brew services start mysql`.
- Tạo database: `mysql -u root -p < database/create_database.sql`.
- Trong thư mục này: `python3.12 -m venv .venv`, kích hoạt venv, `pip install -r requirements.txt`.
- Sao chép `.env.example` thành `.env`; điền đúng `MYSQL_USER`, `MYSQL_PASSWORD`, host/port và đặt `SECRET_KEY` ngẫu nhiên.
- Chạy `uvicorn app.main:app --reload`.
- Mở Swagger tại http://127.0.0.1:8000/docs.

API: http://127.0.0.1:8000/api · Swagger: http://127.0.0.1:8000/docs

| Role | Username | Password |
|---|---|---|
| Admin | `admin` | `Admin@123` |
| Staff | `staff` | `Staff@123` |

Tài khoản demo được seed lần đầu; thay password và secret trước khi dùng thật. `.env` không được commit.

## Kết nối FE riêng

- FE riêng ở `../blueisland-fe/blueisland-fe`; chạy bằng Live Server, ví dụ `http://127.0.0.1:5500`.
- Thêm origin này vào `CORS_ORIGINS` trong `.env`. Vì FE chạy port khác, các lệnh `fetch('/api/...')` cần bật và đổi thành `fetch('http://127.0.0.1:8000/api/...')` (hoặc dùng biến `API_BASE_URL`).
- Login, menu và POS trong FE hiện vẫn chưa được bật đầy đủ; bật các đoạn fetch và chuyển payload đơn hàng sang `product_id`, `quantity`, `options` như mô tả trong `docs/BUILD_GUIDE_VI.md`.
- Đăng nhập thử qua API bằng `staff / Staff@123` hoặc `admin / Admin@123`. Dùng Bearer token cho các route cần quyền.
- CRUD và báo cáo admin có thể thử tại `/docs`; trang admin FE hiện mới là giao diện khung.
- Có sẵn Postman collection tại [postman/BlueIsland-API.postman_collection.json](postman/BlueIsland-API.postman_collection.json). Import vào Postman, chọn Run collection; collection đang đặt `baseUrl` là `http://127.0.0.1:8001` theo lệnh chạy hiện tại, và tự lưu token/id giữa requests.
- Collection kiểm tra health/DB, login admin/staff, menu search, menu create/update/soft-delete, tạo và cập nhật đơn, báo cáo, quản lý staff và RBAC. Chạy trên database test vì collection tạo đơn và tài khoản/món test.
- Chạy smoke test không cần MySQL bằng `.venv/bin/python tests/run_api_smoke.py`. Script dùng SQLite in-memory để test route/API logic; kiểm tra kết nối MySQL thật bằng collection trong Postman.
- Khi API đang chạy, kiểm tra HTTP/MySQL thật bằng `BASE_URL=http://127.0.0.1:8000 .venv/bin/python tests/run_http_smoke.py` (nếu chạy port 8001 thì đổi URL tương ứng). Script tự tạo rồi dọn món/đơn/tài khoản test.

Đặt đơn gửi `order_type`, `table_code`, `customer_name`, `student_id`, `payment_method`, `cash_received`, `discount`, `items: [{product_id, quantity, options:[{name, price}]}]`. Backend đọc giá món từ DB và tự tính lại tổng.

## Routes

- Public: `GET /api/health`, `POST /api/auth/login`, `GET /api/categories`, `GET /api/menu?q=...&category=...`.
- Staff đăng nhập: `GET /api/auth/me`, `POST /api/orders`, `GET /api/orders`, `PATCH /api/orders/{id}/status`.
- Chỉ admin: CRUD `/api/admin/menu`, thống kê `/api/admin/stats/summary`, `/daily`, `/top-products`, quản lý `/api/admin/staff`, hủy đơn `/api/admin/orders/{id}`.

Chi tiết request/response xem tại `/docs`; hướng dẫn xây dựng từng bước ở [docs/BUILD_GUIDE_VI.md](docs/BUILD_GUIDE_VI.md).

## Cấu trúc

`app/config.py` cấu hình; `database.py` session DB; `models.py` schema ORM; `schemas.py` kiểm tra dữ liệu; `security.py` bcrypt/JWT/phân quyền; `seed.py` tạo danh mục, món, demo users; `main.py` định nghĩa REST API.
