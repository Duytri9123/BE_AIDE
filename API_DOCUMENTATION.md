# BE_BOM API Documentation

## Base URL
```
http://127.0.0.1:8001/api/v1
```

## Authentication
API sử dụng Bearer Token authentication. Token được trả về khi login thành công.

### Headers
```
Authorization: Bearer <token>
Content-Type: application/json
```

---

## 📋 Authentication Endpoints

### POST /auth/register
Đăng ký user mới

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "password123",
  "name": "User Name"
}
```

**Response:**
```json
{
  "message": "User registered successfully"
}
```

### POST /auth/login
Đăng nhập

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "password123"
}
```

**Response:**
```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

### POST /auth/refresh
Refresh access token

**Response:**
```json
{
  "access_token": "new_token_here",
  "token_type": "bearer"
}
```

### POST /auth/logout
Đăng xuất

**Response:**
```json
{
  "message": "Logged out successfully"
}
```

---

## 👤 Users Endpoints

### GET /users/me
Lấy thông tin user hiện tại

**Response:**
```json
{
  "id": 1,
  "email": "user@example.com",
  "name": "User Name",
  "phone": "0123456789",
  "status": "active",
  "role": "user",
  "tokens": 100000
}
```

### PUT /users/me
Cập nhật thông tin user hiện tại

**Request Body:**
```json
{
  "name": "Updated Name",
  "phone": "0987654321"
}
```

### GET /users (Admin only)
Danh sách users

**Query Parameters:**
- `skip` (int): Số record bỏ qua (default: 0)
- `limit` (int): Số record tối đa (default: 100)

**Response:**
```json
[
  {
    "id": 1,
    "email": "user@example.com",
    "name": "User Name",
    "status": "active",
    "role": "user",
    "tokens": 100000
  }
]
```

### GET /users/{user_id} (Admin only)
Chi tiết user

### PUT /users/{user_id} (Admin only)
Cập nhật user

### DELETE /users/{user_id} (Admin only)
Xóa user

---

## 📁 Projects Endpoints

### GET /projects
Danh sách projects của user

**Query Parameters:**
- `skip` (int): Offset
- `limit` (int): Limit

**Response:**
```json
[
  {
    "id": 1,
    "name": "Dự án tủ điện 630A",
    "category": "Tủ điện",
    "user_id": 1,
    "created_at": "2026-08-25T10:00:00Z",
    "updated_at": "2026-08-25T10:00:00Z"
  }
]
```

### POST /projects
Tạo project mới

**Request Body:**
```json
{
  "name": "Dự án tủ điện 630A",
  "category": "Tủ điện"
}
```

### GET /projects/{id}
Chi tiết project

### PUT /projects/{id}
Cập nhật project

**Request Body:**
```json
{
  "name": "Updated Name",
  "category": "Trạm sạc"
}
```

### DELETE /projects/{id}
Xóa project (soft delete)

### POST /projects/{id}/upload
Upload file cho project

**Request:**
- Content-Type: multipart/form-data
- Body: file (binary)

**Response:**
```json
{
  "id": 1,
  "project_id": 1,
  "filename": "drawing.dwg",
  "file_path": "storage/projects/1/drawing.dwg",
  "file_size": 1048576,
  "file_type": "application/dwg",
  "created_at": "2026-08-25T10:00:00Z"
}
```

### GET /projects/{id}/files
Danh sách files của project

### DELETE /projects/{id}/files/{file_id}
Xóa file

---

## 🔌 Device Library Endpoints

### GET /device-library/brands
Danh sách brands

**Response:**
```json
[
  {
    "id": 1,
    "name": "Schneider Electric"
  },
  {
    "id": 2,
    "name": "ABB"
  }
]
```

### GET /device-library/categories
Danh sách categories

**Response:**
```json
[
  {
    "id": 1,
    "name": "MCCB",
    "description": "Molded Case Circuit Breaker"
  }
]
```

### GET /device-library/series
Danh sách series

**Query Parameters:**
- `brand_id` (int, optional): Filter by brand

### GET /device-library/models
Danh sách device models

**Query Parameters:**
- `brand_id` (int, optional)
- `category_id` (int, optional)
- `skip` (int)
- `limit` (int)

**Response:**
```json
[
  {
    "id": 1,
    "brand_id": 1,
    "category_id": 1,
    "series_id": 1,
    "model_code": "NSX250F",
    "name": "MCCB 250A",
    "rated_current_a": 250.0,
    "breaking_capacity_ka": 36.0,
    "poles": 3
  }
]
```

### GET /device-library/user-items
Danh sách thiết bị của user

### POST /device-library/user-items
Thêm thiết bị vào library

**Request Body:**
```json
{
  "brand": "Schneider",
  "code": "NSX250F",
  "name": "MCCB 250A",
  "spec": "3P, 36kA",
  "unit_price": 5000000
}
```

### DELETE /device-library/user-items/{id}
Xóa thiết bị

---

## 🤖 AI Providers Endpoints

### GET /providers
Danh sách AI providers

**Response:**
```json
[
  {
    "id": 1,
    "name": "Google Gemini",
    "api_type": "gemini",
    "base_url": null,
    "is_active": true
  }
]
```

### GET /providers/{provider_id}/models
Danh sách models của provider

**Response:**
```json
[
  {
    "id": 1,
    "provider_id": 1,
    "model_key": "gemini-pro",
    "model_name": "Gemini Pro",
    "is_active": true
  }
]
```

---

## 📚 User Library Endpoints

### GET /user-library/files
Danh sách files trong library của user

**Response:**
```json
[
  {
    "id": 1,
    "filename": "template.xlsx",
    "file_path": "storage/user_library/1/template.xlsx",
    "file_size": 524288,
    "file_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "created_at": "2026-08-25T10:00:00Z"
  }
]
```

### POST /user-library/files
Upload file vào library

**Request:**
- Content-Type: multipart/form-data
- Body: file (binary)

### GET /user-library/files/{file_id}
Chi tiết file

### DELETE /user-library/files/{file_id}
Xóa file

---

## 🔍 Analysis Endpoints

### POST /analyze/start
Bắt đầu phân tích

**Request Body:**
```json
{
  "project_id": "550e8400-e29b-41d4-a716-446655440000",
  "provider": "gemini",
  "model": "gemini-pro"
}
```

**Response:**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "iteration_number": 1,
  "devices": [],
  "warnings": [],
  "topology_preview": {}
}
```

### POST /analyze/refine
Tinh chỉnh kết quả phân tích

**Request Body:**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "user_corrections": [],
  "user_message": "Cập nhật lại số lượng",
  "focus_zone": "panel_1"
}
```

### POST /analyze/finalize
Hoàn tất phân tích

**Request Body:**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

### GET /analyze/history/{session_id}
Lịch sử phân tích

---

## 📊 BOM Endpoints

### POST /bom/calculate
Tính toán BOM

**Request Body:**
```json
{
  "project_id": "550e8400-e29b-41d4-a716-446655440000",
  "devices": []
}
```

**Response:**
```json
{
  "enclosure": {
    "H": 1000,
    "W": 800,
    "D": 300,
    "tole_thickness_mm": 1.5,
    "tole_mass_kg": 45.0,
    "din_rail_count": 4
  },
  "busbar": {
    "profile": "rectangular",
    "section_mm2": 200,
    "L_total_m": 5.0,
    "mass_Cu_kg": 8.9,
    "phase_allocation": {}
  },
  "accessories": [],
  "labor": {
    "T_total_hours": 12,
    "estimated_days": 1.5,
    "breakdown": {}
  },
  "total_material_cost": 0.0,
  "total_labor_cost": 0.0
}
```

### GET /bom/topology/{project_id}
Lấy topology graph

### GET /bom/enclosure-preview/{project_id}
Preview kích thước tủ điện

---

## 📤 Export Endpoints

### POST /export/quotation
Export báo giá

**Request Body:**
```json
{
  "project_id": "550e8400-e29b-41d4-a716-446655440000",
  "scope": "full",
  "layout": "detailed",
  "brand_preference": "schneider"
}
```

**Response:**
```json
{
  "download_url": "/export/download/report.xlsx",
  "filename": "report.xlsx",
  "file_size": 1024000
}
```

### GET /export/download/{filename}
Download file đã export

---

## 💬 Chat Endpoints

### POST /chat
Gửi message chat với AI

**Request Body:**
```json
{
  "project_id": "550e8400-e29b-41d4-a716-446655440000",
  "message": "Phân tích file bản vẽ",
  "session_id": null,
  "context": {}
}
```

**Response:**
```json
{
  "reply": "Đã phân tích file bản vẽ...",
  "suggested_corrections": [],
  "artifacts": []
}
```

---

## ⚙️ Settings Endpoints

### GET /settings/settings
Lấy system settings

### GET /settings/accessories-catalog
Lấy catalog phụ kiện

---

## 📄 Pages Endpoints

### GET /pages/{slug}
Lấy nội dung page

**Response:**
```json
{
  "slug": "about",
  "content": "Page content here"
}
```

---

## 🔔 Notifications Endpoints

### GET /notifications
Lấy notifications của user

**Response:**
```json
[]
```

---

## 🏥 Health Check

### GET /health
Kiểm tra trạng thái server

**Response:**
```json
{
  "status": "ok"
}
```

---

## Error Responses

### 400 Bad Request
```json
{
  "detail": "Invalid request parameters"
}
```

### 401 Unauthorized
```json
{
  "detail": "Could not validate credentials"
}
```

### 403 Forbidden
```json
{
  "detail": "Not enough privileges"
}
```

### 404 Not Found
```json
{
  "detail": "Resource not found"
}
```

### 500 Internal Server Error
```json
{
  "detail": "Internal server error"
}
```

---

## Rate Limiting
Hiện tại chưa có rate limiting. Sẽ được thêm trong phiên bản tiếp theo.

## Pagination
Các endpoint list thường hỗ trợ pagination với parameters:
- `skip`: Số record bỏ qua (default: 0)
- `limit`: Số record tối đa (default: 100)

## File Upload
File upload sử dụng `multipart/form-data` với key là `file`.

Maximum file size: 50MB (có thể config trong `.env`)

## Supported File Types
- DWG/DXF files
- PDF files
- Excel files (.xlsx, .xls)
- Image files (.png, .jpg, .jpeg)

---

## Testing với Postman
Import file `BE_BOM_API.postman_collection.json` vào Postman để test nhanh.

## Swagger UI
Truy cập http://127.0.0.1:8001/docs để xem interactive API documentation.
