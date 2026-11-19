# Tài liệu xây dựng backend BlueIsland Coffee (step-by-step)

## 1. Phân tích yêu cầu từ FE

FE nằm tại `../blueisland-fe/blueisland-fe`: landing page, POS nhân viên và trang admin. Hiện trạng cần lưu ý: `assets/js/api.js` chỉ là stub; các đoạn login và POS fetch trong `main.js`/`staff.js` đang nằm trong comment; menu FE đang lấy từ dữ liệu tĩnh. Vì vậy backend cung cấp API cho login, danh mục/menu, CRUD món, tìm kiếm, POS/đơn hàng, báo cáo và quản lý tài khoản, nhưng để giao diện sử dụng dữ liệu MySQL thì vẫn phải bật và nối các lời gọi ở FE. Đánh giá/cài đặt chưa có nghiệp vụ cụ thể.

## 2. Chọn kiến trúc

Trình duyệt (HTML/JS) → HTTP/JSON + Bearer JWT → FastAPI → SQLAlchemy ORM → MySQL. FastAPI tự sinh OpenAPI/Swagger. `admin` quản lý menu, nhân viên, báo cáo; `staff` thao tác đơn. Backend kiểm tra quyền trên từng request.

## 3. Chuẩn bị môi trường

1. Cài Python 3.10+ và MySQL 8.
2. Tạo virtualenv để cô lập thư viện dự án.
3. Cài dependencies trong `requirements.txt` (FastAPI, Uvicorn, SQLAlchemy, PyMySQL, JWT, bcrypt).
4. Sao chép `.env.example` thành `.env`, cấu hình database, secret và CORS. Không commit `.env`.

Lệnh thực thi chi tiết nằm trong README.

## 4. Thiết kế cơ sở dữ liệu

- `users`: username/email/mã nhân viên, password hash, role, trạng thái.
- `categories`: mã và tên nhóm món.
- `products`: tên, mô tả, giá VND, ảnh, nhãn, danh mục, trạng thái bán.
- `orders`: mã đơn, loại đơn, bàn/khách, thanh toán, tổng, trạng thái, nhân viên, thời gian.
- `order_items`: snapshot tên/đơn giá/số lượng/topping/thành tiền từng dòng.

Quan hệ: category 1-n products; user 1-n orders; order 1-n order_items. Snapshot giá để lịch sử không đổi khi cập nhật menu. Tạo database bằng `database/create_database.sql`; model SQLAlchemy tạo các bảng khi API khởi động.

## 5. Model và dữ liệu khởi tạo

`app/models.py` khai báo bảng bằng SQLAlchemy. `app/seed.py` tạo 7 danh mục, 23 món khớp menu FE và 2 tài khoản demo. Seed chỉ chèn khi bảng liên quan chưa có dữ liệu. Giá lưu số nguyên VND.

## 6. API và kiểm tra dữ liệu

`app/schemas.py` dùng Pydantic giới hạn dữ liệu đầu vào. `app/main.py` định nghĩa đăng nhập, menu/tìm kiếm, đặt đơn, cập nhật trạng thái, CRUD món/tài khoản và báo cáo. Khi tạo đơn, server lấy giá từ DB, xác thực món đang bán, tính lại tổng và lưu chi tiết; frontend không được quyết định tổng tiền.

## 7. Đăng nhập và phân quyền

Mật khẩu băm bcrypt. Login trả JWT có thời hạn; route bảo vệ nhận `Authorization: Bearer <token>`. `current_user` xác minh chữ ký và trạng thái tài khoản; `require_admin` chặn staff khỏi route quản trị bằng HTTP 403. Vô hiệu hóa user sẽ chặn cả token đã cấp trước đó.

## 8. Báo cáo

Summary trả số đơn, số hủy, doanh thu, tiền mặt/chuyển khoản và số đơn đang xử lý theo khoảng ngày. Daily trả dữ liệu mỗi ngày để vẽ biểu đồ. Top products cộng số lượng và doanh thu, loại đơn hủy.

## 9. Chạy backend và kết nối FE riêng

1. Cài MySQL Server và khởi động dịch vụ MySQL. Tạo database bằng `mysql -u root -p < database/create_database.sql`.
2. Cài thư viện: `python3 -m venv .venv`, kích hoạt môi trường ảo, chạy `pip install -r requirements.txt`.
3. Sao chép `.env.example` thành `.env`, điền thông tin MySQL, `SECRET_KEY` và `CORS_ORIGINS=http://127.0.0.1:5500,http://localhost:5500`.
4. Chạy backend bằng `uvicorn app.main:app --reload`; Swagger ở `http://127.0.0.1:8000/docs`.
5. Chạy FE riêng trong `../blueisland-fe/blueisland-fe` bằng Live Server, ví dụ port 5500.
6. Trong FE, bật các đoạn fetch hiện đang comment và dùng API base `http://127.0.0.1:8000`, vì FE và BE có origin/port riêng. Login nhận JWT; gửi `Authorization: Bearer <token>` trên request riêng tư.
7. Khi tạo đơn, chuyển mỗi dòng từ giỏ FE thành `{product_id, quantity, options}`; backend đọc giá gốc từ DB, tính tổng và lưu đơn.
8. Login demo: `staff / Staff@123`, `admin / Admin@123`. Trang admin FE hiện là giao diện khung; có thể thử CRUD món, nhân viên và thống kê tại Swagger sau khi Authorize token admin.

## 10. Đóng gói và triển khai

API thường chạy trên máy chủ Python dùng chung; không cần cài desktop app trên từng máy nhân viên. Nếu yêu cầu bài nộp cần executable local, cài PyInstaller rồi thử đóng gói entrypoint Uvicorn; MySQL Server vẫn là dependency riêng. Có thể triển khai bằng Docker Compose hoặc máy chủ Python. Mỗi môi trường phải cấu hình `.env`; không dùng password demo và secret mẫu ở production.

## 11. Hướng phát triển tiếp

Bổ sung API đánh giá/cài đặt/ca làm; migration Alembic; phân trang, audit log, khôi phục mật khẩu và giới hạn login; tích hợp đầy đủ UI login/checkout/menu/admin và xử lý token hết hạn.
