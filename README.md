# BE_AIDE - Hệ Thống Backend Bóc Tách & Dự Toán Tủ Bảng Điện

Backend FastAPI mạnh mẽ cho hệ thống AIDE (Tự động bóc tách bản vẽ kỹ thuật CAD/DWG/DXF/PDF, tính toán dự toán thiết bị tủ bảng điện, quản lý dự án, báo giá và tích hợp AI).

## 🚀 Công Nghệ Sử Dụng

- **Ngôn ngữ:** Python 3.11+
- **Framework:** [FastAPI](https://fastapi.tiangolo.com/) + [Uvicorn](https://www.uvicorn.org/)
- **Database ORM:** [SQLAlchemy 2.0](https://www.sqlalchemy.org/) (Async) + [Alembic](https://alembic.sqlalchemy.org/)
- **Database:** SQLite (Mặc định: `webbaogia.db`) / PostgreSQL (Sẵn sàng)
- **Xử lý CAD:** ezdxf, PyMuPDF, OpenCV
- **Bảo mật:** JWT (JSON Web Tokens), Google OAuth 2.0, Passlib (Bcrypt)
- **Tích hợp AI:** OpenAI / Gemini / Custom LLM API

---

## 🛠️ Hướng Dẫn Cài Đặt & Khởi Chạy

### 1. Yêu cầu hệ thống
- Python 3.11 trở lên
- Git

### 2. Cài đặt môi trường ảo
```bash
# Tạo môi trường ảo
python -m venv venv

# Kích hoạt trên Windows PowerShell:
.\venv\Scripts\Activate.ps1

# Kích hoạt trên Linux/macOS:
source venv/bin/activate
```

### 3. Cài đặt các gói thư viện
```bash
pip install -r requirements.txt
```

### 4. Thiết lập biến môi trường
Tạo file `.env` từ file `.env.example`:
```bash
cp .env.example .env
```
Cập nhật các thông số cần thiết trong `.env`.

### 5. Khởi động Backend
```bash
# Sử dụng script PowerShell có sẵn (Windows):
.\start.ps1

# Hoặc khởi chạy trực tiếp với Uvicorn:
uvicorn app.main:app --reload --port 8000 --host 0.0.0.0
```

---

## 📖 Tài Liệu API & Quản Trị

- **Swagger UI:** `http://localhost:8000/docs`
- **ReDoc:** `http://localhost:8000/redoc`
- **Admin Panel:** `http://localhost:8000/admin`
- Chi tiết tài liệu API xem tại file [API_DOCUMENTATION.md](API_DOCUMENTATION.md).

---

## 📁 Cấu Trúc Dự Án

```
BE_BOM/
├── alembic/              # Database migrations
├── app/                  # Mã nguồn chính của ứng dụng
│   ├── api/              # Endpoints & Routers (v1)
│   ├── core/             # Cấu hình, bảo mật, exceptions
│   ├── db/               # Khởi tạo database session
│   ├── models/           # SQLAlchemy ORM models
│   ├── schemas/          # Pydantic schemas (Request / Response)
│   └── services/         # Business logic (CAD parser, BOM matcher, AI...)
├── data/                 # Dữ liệu catalog mẫu thiết bị & phụ kiện
├── scripts/              # Các script quản trị, seed dữ liệu, kiểm tra hệ thống
├── storage/              # File lưu trữ (uploads, projects, exports)
├── webbaogia.db          # Database SQLite tích hợp
├── requirements.txt      # Danh sách dependencies
└── start.ps1             # Script khởi động nhanh
```
