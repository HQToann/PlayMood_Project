# WEEK 1 — Setup Guide & Postman Testing

**Hệ thống Âm nhạc Django | Backend Roadmap**
**Tuần 1: Nền tảng, Base Architecture, App `accounts` & Authentication**

---

## 1. Tổng Quan Những Gì Đã Làm Tuần Này

| Hạng mục | Chi tiết |
|---|---|
| **Cấu trúc project** | `music_platform/` (settings, urls, wsgi, sanitize) |
| **App `accounts`** | models, validators, services, selectors, decorators, views, urls |
| **Auth flow** | Session + CSRF (không JWT) |
| **Bảo mật** | bleach XSS sanitize (Fix R12), block policy (Fix R10) |
| **API Versioning** | `/api/v1/` prefix (Fix R15) |
| **Cloudinary** | Cấu hình sẵn trong settings, chờ điền key thật từ Tuần 2 |
| **Tests** | 79 test cases — 100% PASS |

---

## 2. Yêu Cầu Môi Trường

```
Python  3.11+
Django  5.2.3
PostgreSQL 14+ (production) | SQLite (dev/test)
```

---

## 3. Setup Từ Đầu

### Bước 1 — Clone & Tạo môi trường ảo

```bash
# Clone project về máy
git clone <repo-url> music_platform
cd music_platform

# Tạo virtual environment
python3 -m venv venv
source venv/bin/activate          # Linux/Mac
# venv\Scripts\activate           # Windows

# Cài dependencies
pip install -r requirements.txt
```

### Bước 2 — Cấu hình biến môi trường

```bash
cp .env.example .env
# Mở .env và điền các giá trị thật
```

Các biến **bắt buộc** phải điền:

```ini
SECRET_KEY=<chuỗi ngẫu nhiên ≥50 ký tự>
DB_NAME=music_platform
DB_USER=postgres
DB_PASSWORD=<mật khẩu PostgreSQL của bạn>
DB_HOST=localhost
DB_PORT=5432

# Cloudinary — đăng ký miễn phí tại https://cloudinary.com
# Tuần 1 có thể để placeholder, chưa upload file thật
CLOUDINARY_CLOUD_NAME=your_cloud_name
CLOUDINARY_API_KEY=your_api_key
CLOUDINARY_API_SECRET=your_api_secret
```

> **Tạo SECRET_KEY nhanh:**
> ```bash
> python3 -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
> ```

### Bước 3 — Tạo Database và chạy Migration

```bash
# Tạo database trong PostgreSQL
psql -U postgres -c "CREATE DATABASE music_platform;"

# Chạy migration
python manage.py migrate

# Tạo superuser để test Django Admin
python manage.py createsuperuser
# → Nhập email, username, password khi được hỏi
```

### Bước 4 — Khởi động server

```bash
python manage.py runserver 8000
```

Truy cập Django Admin: http://localhost:8000/admin/

---

## 4. Chạy Tests

```bash
# Chạy toàn bộ test app accounts
python manage.py test accounts --verbosity=2

# Chạy một test class cụ thể
python manage.py test accounts.tests.RegisterViewTest --verbosity=2

# Chạy một test case cụ thể
python manage.py test accounts.tests.RegisterViewTest.test_register_success

# Kết quả mong đợi:
# Ran 79 tests in ~45s
# OK
```

> **Lưu ý:** Tests dùng SQLite in-memory, KHÔNG cần PostgreSQL. Chạy độc lập.

---

## 5. Cấu Trúc Thư Mục Tuần 1

```
music_platform/
├── manage.py
├── requirements.txt
├── .env.example
├── .env                        ← (tự tạo, không commit)
│
├── music_platform/             ← Django project package
│   ├── __init__.py
│   ├── settings.py             ← Cấu hình toàn hệ thống
│   ├── urls.py                 ← URL gốc + /api/v1/ versioning
│   ├── wsgi.py
│   └── sanitize.py             ← bleach XSS sanitizer (Fix R12)
│
└── accounts/                   ← App quản lý tài khoản
    ├── __init__.py
    ├── apps.py
    ├── models.py               ← User, ArtistVerification, BlockList
    ├── validators.py           ← Input validation (không gọi DB)
    ├── selectors.py            ← Read-only queries
    ├── services.py             ← Business logic ghi dữ liệu
    ├── decorators.py           ← require_auth, require_artist, require_admin
    ├── views.py                ← HTTP layer, gọi validators/services
    ├── auth_urls.py            ← /api/v1/auth/ endpoints
    ├── urls.py                 ← /api/v1/accounts/ endpoints
    ├── admin.py
    ├── tests.py                ← 79 test cases
    └── migrations/
        └── 0001_initial.py
```

---

## 6. Danh Sách API Tuần 1

| Method | URL | Auth | Mô tả |
|--------|-----|------|-------|
| GET | `/api/v1/auth/csrf/` | — | Lấy CSRF token |
| POST | `/api/v1/auth/register/` | CSRF | Đăng ký tài khoản |
| POST | `/api/v1/auth/login/` | CSRF | Đăng nhập |
| POST | `/api/v1/auth/logout/` | Session + CSRF | Đăng xuất |
| GET | `/api/v1/auth/me/` | Session | Xem thông tin đăng nhập |
| POST | `/api/v1/auth/password/change/` | Session + CSRF | Đổi mật khẩu |
| GET | `/api/v1/accounts/me/` | Session | Xem hồ sơ cá nhân |
| PATCH | `/api/v1/accounts/me/` | Session + CSRF | Cập nhật hồ sơ |
| POST | `/api/v1/accounts/me/avatar/` | Session + CSRF | Upload avatar |
| PATCH | `/api/v1/accounts/me/privacy/` | Session + CSRF | Bật/tắt chế độ riêng tư |
| GET | `/api/v1/accounts/users/<uuid>/` | — | Xem profile công khai |
| POST | `/api/v1/accounts/users/<uuid>/block/` | Session + CSRF | Block/unblock user |
| GET | `/api/v1/accounts/artist-verification/me/` | Session | Xem trạng thái xác thực |
| POST | `/api/v1/accounts/artist-verification/` | Session + CSRF | Nộp yêu cầu xác thực |
| GET | `/api/v1/accounts/admin/verifications/` | Admin + Session | Danh sách chờ duyệt |
| POST | `/api/v1/accounts/admin/verifications/<uuid>/approve/` | Admin + CSRF | Duyệt xác thực |
| POST | `/api/v1/accounts/admin/verifications/<uuid>/reject/` | Admin + CSRF | Từ chối xác thực |

---

## 7. Hướng Dẫn Test API qua Postman

### 7.1. Thiết Lập Postman Collection

**Tạo Environment trong Postman:**
- `base_url` = `http://localhost:8000`
- `csrftoken` = *(để trống, sẽ tự cập nhật)*
- `sessionid` = *(để trống, sẽ tự cập nhật)*

**Tạo Collection-level Pre-request Script** để tự extract cookie:
```javascript
// Chạy mỗi lần trước request
const jar = pm.cookies.jar();
jar.get(pm.environment.get('base_url'), 'csrftoken', (err, val) => {
    if (val) pm.environment.set('csrftoken', val);
});
```

---

### 7.2. Giải Thích Cơ Chế CSRF + Session

```
┌─────────────────────────────────────────────────────────────────┐
│  LUỒNG XÁC THỰC BẮT BUỘC CHO MỌI POST/PATCH/DELETE             │
│                                                                 │
│  Bước 1: GET /api/v1/auth/csrf/                                 │
│          → Server set cookie: csrftoken=<token>                 │
│                                                                 │
│  Bước 2: POST /api/v1/auth/login/                               │
│          Header: X-CSRFToken: <token từ cookie>                 │
│          → Server set cookie: sessionid=<session>               │
│                                                                 │
│  Bước 3: Mọi request tiếp theo                                  │
│          Cookie: sessionid=<session>     ← xác định danh tính   │
│          Header: X-CSRFToken: <token>    ← chống CSRF attack     │
└─────────────────────────────────────────────────────────────────┘
```

**Lý do `CSRF_COOKIE_HTTPONLY = False`:** JS frontend cần đọc giá trị cookie `csrftoken` để gắn vào header `X-CSRFToken`. Nếu `HttpOnly = True`, JS không đọc được cookie → không thể gửi CSRF token.

**Lý do `SESSION_COOKIE_HTTPONLY = True`:** Cookie `sessionid` chứa thông tin phiên làm việc, JS không được phép đọc để tránh XSS đánh cắp session.

---

### 7.3. Cấu Hình Chung Postman

Vào **Settings → Cookies** trong Postman:
- Bật **"Automatically follow redirects"**
- Bật **"Send cookies"** 

Trong mỗi request **POST/PATCH/DELETE**, thêm header:
```
X-CSRFToken: {{csrftoken}}
```

---

### 7.4. Test Từng Endpoint

---

#### ① GET /api/v1/auth/csrf/ — Lấy CSRF Token

```
Method:  GET
URL:     {{base_url}}/api/v1/auth/csrf/
Headers: (không cần gì)
Body:    (không có)
```

**Response mong đợi (200):**
```json
{
    "success": true,
    "detail": "CSRF cookie set"
}
```

**Sau khi gọi:** Cookie `csrftoken` sẽ xuất hiện trong Postman Cookie Manager.
Vào **Cookies** tab → copy giá trị `csrftoken` → paste vào Environment variable `csrftoken`.

---

#### ② POST /api/v1/auth/register/ — Đăng Ký

```
Method:  POST
URL:     {{base_url}}/api/v1/auth/register/
Headers:
    Content-Type:  application/json
    X-CSRFToken:   {{csrftoken}}
Body (raw JSON):
```
```json
{
    "username": "nguyenvana",
    "email": "nguyenvana@example.com",
    "password": "Test1234"
}
```

**Response mong đợi (201):**
```json
{
    "success": true,
    "data": {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "username": "nguyenvana",
        "display_name": "nguyenvana",
        "avatar": null,
        "bio": "",
        "role": "user",
        "is_private": false,
        "created_at": "2026-06-11T10:00:00+07:00",
        "email": "nguyenvana@example.com"
    }
}
```

**Test case lỗi — Email trùng (409):**
```json
{
    "success": false,
    "error": {
        "code": "ALREADY_EXISTS",
        "message": "Email này đã được đăng ký"
    }
}
```

**Test case lỗi — Validation (400):**
```json
{
    "success": false,
    "error": {
        "code": "VALIDATION_ERROR",
        "message": "Dữ liệu đăng ký không hợp lệ",
        "fields": {
            "password": ["Mật khẩu phải có ít nhất 1 chữ hoa, 1 chữ thường và 1 số"]
        }
    }
}
```

---

#### ③ POST /api/v1/auth/login/ — Đăng Nhập

```
Method:  POST
URL:     {{base_url}}/api/v1/auth/login/
Headers:
    Content-Type:  application/json
    X-CSRFToken:   {{csrftoken}}
Body (raw JSON):
```
```json
{
    "email": "nguyenvana@example.com",
    "password": "Test1234"
}
```

**Response mong đợi (200):**
```json
{
    "success": true,
    "data": {
        "id": "550e8400-...",
        "username": "nguyenvana",
        "role": "user",
        "email": "nguyenvana@example.com",
        ...
    }
}
```

**Sau khi login thành công:**
Postman sẽ tự nhận cookie `sessionid`. Vào **Cookies** → copy `sessionid` → lưu vào Environment.

**Test case lỗi — Sai mật khẩu (401):**
```json
{
    "success": false,
    "error": {
        "code": "AUTH_REQUIRED",
        "message": "Email hoặc mật khẩu không đúng"
    }
}
```

---

#### ④ GET /api/v1/auth/me/ — Kiểm Tra Đăng Nhập

```
Method:  GET
URL:     {{base_url}}/api/v1/auth/me/
Headers: (Postman tự gửi cookie sessionid)
Body:    (không có)
```

**Response mong đợi (200):** Trả thông tin user đang đăng nhập.

**Khi chưa đăng nhập (401):**
```json
{
    "success": false,
    "error": {
        "code": "AUTH_REQUIRED",
        "message": "Bạn cần đăng nhập để thực hiện hành động này"
    }
}
```

---

#### ⑤ PATCH /api/v1/accounts/me/ — Cập Nhật Hồ Sơ

```
Method:  PATCH
URL:     {{base_url}}/api/v1/accounts/me/
Headers:
    Content-Type:  application/json
    X-CSRFToken:   {{csrftoken}}
    Cookie:        sessionid={{sessionid}}
Body (raw JSON):
```
```json
{
    "display_name": "Nguyễn Văn A",
    "bio": "Yêu âm nhạc và lập trình"
}
```

**Response mong đợi (200):** Trả user đã cập nhật.

> **Test XSS Protection:** Gửi `"bio": "<script>alert(1)</script>Bio thật"` → response sẽ trả `"bio": "Bio thật"` — script bị strip hoàn toàn.

---

#### ⑥ POST /api/v1/accounts/me/avatar/ — Upload Avatar

```
Method:  POST
URL:     {{base_url}}/api/v1/accounts/me/avatar/
Headers:
    X-CSRFToken: {{csrftoken}}
    (KHÔNG đặt Content-Type — Postman tự set multipart/form-data)
Body: form-data
    avatar: [chọn file] test_avatar.jpg
```

**Response mong đợi (200):**
```json
{
    "success": true,
    "data": {
        "avatar": "https://res.cloudinary.com/your_cloud/image/upload/avatars/users/uuid.jpg"
    }
}
```

> **Lưu ý:** Khi chưa cấu hình Cloudinary thật, URL trả về sẽ là path local `/media/avatars/users/...`

---

#### ⑦ PATCH /api/v1/accounts/me/privacy/ — Bật Chế Độ Riêng Tư

```
Method:  PATCH
URL:     {{base_url}}/api/v1/accounts/me/privacy/
Headers:
    Content-Type:  application/json
    X-CSRFToken:   {{csrftoken}}
Body:
```
```json
{
    "is_private": true
}
```

**Response mong đợi (200):**
```json
{
    "success": true,
    "data": {
        "is_private": true
    }
}
```

---

#### ⑧ GET /api/v1/accounts/users/<uuid>/ — Xem Profile Công Khai

```
Method:  GET
URL:     {{base_url}}/api/v1/accounts/users/550e8400-e29b-41d4-a716-446655440000/
Headers: (không cần auth)
```

**Response mong đợi (200):** Trả profile không có trường `email`.

**Test Block Policy (Fix R10):**
1. Đăng nhập với User A → block User B: `POST /api/v1/accounts/users/<B_id>/block/`
2. Đăng nhập với User B → xem profile User A: `GET /api/v1/accounts/users/<A_id>/`
3. Response phải là **404** (giả vờ không tồn tại, không để lộ bị block)

---

#### ⑨ POST /api/v1/accounts/users/<uuid>/block/ — Block/Unblock

```
Method:  POST
URL:     {{base_url}}/api/v1/accounts/users/<target_uuid>/block/
Headers:
    X-CSRFToken: {{csrftoken}}
Body:    (không có)
```

**Response block lần đầu (200):**
```json
{
    "success": true,
    "data": {
        "action": "blocked",
        "blocked_user_id": "550e8400-..."
    }
}
```

**Response unblock (200):**
```json
{
    "success": true,
    "data": {
        "action": "unblocked",
        "blocked_user_id": "550e8400-..."
    }
}
```

---

#### ⑩ POST /api/v1/auth/logout/ — Đăng Xuất

```
Method:  POST
URL:     {{base_url}}/api/v1/auth/logout/
Headers:
    X-CSRFToken: {{csrftoken}}
```

**Response mong đợi (200):**
```json
{
    "success": true,
    "message": "Đã đăng xuất thành công"
}
```

Sau khi logout, cookie `sessionid` bị xóa. Gọi lại `GET /auth/me/` → nhận 401.

---

#### ⑪ POST /api/v1/accounts/artist-verification/ — Nộp Yêu Cầu Xác Thực Nghệ Sĩ

```
Method:  POST
URL:     {{base_url}}/api/v1/accounts/artist-verification/
Headers:
    X-CSRFToken: {{csrftoken}}
    (Không đặt Content-Type — Postman tự set multipart)
Body: form-data
    real_name:     Nguyễn Văn A
    note:          Tôi là ca sĩ độc lập từ năm 2020
    id_card_image: [chọn file] cccd.jpg
```

**Response mong đợi (201):**
```json
{
    "success": true,
    "data": {
        "id": "uuid...",
        "user": {"id": "...", "username": "nguyenvana"},
        "real_name": "Nguyễn Văn A",
        "note": "...",
        "status": "pending",
        "created_at": "..."
    }
}
```

---

#### ⑫ Admin: Duyệt / Từ Chối Xác Thực

*Phải đăng nhập bằng tài khoản có `role = admin`.*

```
# Xem danh sách pending
GET /api/v1/accounts/admin/verifications/

# Duyệt
Method:  POST
URL:     {{base_url}}/api/v1/accounts/admin/verifications/<uuid>/approve/
Headers: X-CSRFToken: {{csrftoken}}
Body:    (không có)

# Từ chối
Method:  POST
URL:     {{base_url}}/api/v1/accounts/admin/verifications/<uuid>/reject/
Headers: X-CSRFToken: {{csrftoken}}
Body (JSON):
{
    "reason": "Ảnh CMND không rõ nét"
}
```

---

## 8. Nâng Role User lên Admin (Để Test)

```bash
# Cách 1: Django shell
python manage.py shell
>>> from accounts.models import User
>>> u = User.objects.get(email='admin@example.com')
>>> u.role = 'admin'
>>> u.save()

# Cách 2: Django Admin UI
# http://localhost:8000/admin/ → Users → chọn user → đổi Role = admin
```

---

## 9. Cấu Hình Cloudinary Thật (Tùy Chọn Tuần 1)

```bash
# 1. Đăng ký tại https://cloudinary.com (free tier: 25GB storage, 25GB bandwidth/tháng)
# 2. Vào Dashboard → copy Cloud Name, API Key, API Secret
# 3. Điền vào .env:
CLOUDINARY_CLOUD_NAME=abc123
CLOUDINARY_API_KEY=123456789012345
CLOUDINARY_API_SECRET=abcdefghijklmnopqrstuvwxyz

# 4. Trong settings.py, đảm bảo dòng này không bị comment:
DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.MediaCloudinaryStorage'

# 5. Test upload avatar → URL trả về sẽ là Cloudinary URL
```

---

## 10. Các Lỗi Thường Gặp & Cách Xử Lý

| Lỗi | Nguyên nhân | Cách fix |
|-----|-------------|----------|
| `403 CSRF verification failed` | Thiếu header `X-CSRFToken` | Gọi `/csrf/` trước, thêm header `X-CSRFToken` |
| `401 AUTH_REQUIRED` | Chưa đăng nhập hoặc session hết hạn | Gọi lại `/login/` |
| `500 Server Error` | Lỗi DB hoặc code | Xem log terminal `python manage.py runserver` |
| `No module named 'decouple'` | Chưa cài requirements | `pip install -r requirements.txt` |
| `DATABASES settings improperly configured` | Thiếu `DB_*` trong .env | Copy `.env.example` → `.env`, điền DB info |

---

## 11. Checklist Tuần 1 ✅

- [x] Khởi tạo Django project với cấu trúc phân tầng (models/validators/selectors/services/views)
- [x] Custom User model với UUID PK, role, `USERNAME_FIELD = 'email'`
- [x] Session + CSRF authentication (không JWT)
- [x] API versioning `/api/v1/` (Fix R15)
- [x] bleach XSS sanitization cho mọi text field (Fix R12)
- [x] Block policy: người bị block xem profile → 404 (Fix R10)
- [x] Decorators: `require_auth`, `require_artist`, `require_admin`
- [x] Cloudinary cấu hình sẵn trong settings
- [x] ArtistVerification với upload CMND/CCCD, MIME validation (Fix R4)
- [x] 79 unit tests — 100% PASS
- [x] `WEEK_1_GUIDE.md` hoàn chỉnh

---

## 12. Kế Hoạch Tuần 2

**App `accounts` (nâng cao) + App `artists`:**
- Hoàn thiện block list endpoints (list blocked users)
- `ArtistProfile` model với `avatar`, `cover_image` → upload lên Cloudinary
- Upload avatar nghệ sĩ: `avatars/artists/<uuid>.<ext>`
- Upload cover: `covers/artists/<uuid>.<ext>`
- Stats endpoint: số followers, số bài hát, số lượt nghe tổng
- Password reset via email (token-based)
- Tests cho toàn bộ artists flow
