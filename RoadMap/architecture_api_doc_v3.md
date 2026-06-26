# TÀI LIỆU KIẾN TRÚC & API — HỆ THỐNG ÂM NHẠC
## Django Thuần (Không DRF, Không Pydantic)

> **Phiên bản 3.0** | Django **5.2** | Python 3.11+
>
> ⚠️ **Ghi chú phiên bản:** Tài liệu cũ ghi Django 4.x là sai — thực tế `requirements.txt` dùng `Django==5.2.14`. Toàn bộ tài liệu này đã cập nhật đúng phiên bản. *(Fix R13)*

---

## Mục lục

1. [Tổng quan kiến trúc](#1-tổng-quan-kiến-trúc)
2. [Authentication](#2-authentication)
3. [Quy ước chung API](#3-quy-ước-chung-api)
4. [APP: accounts](#4-app-accounts)
5. [APP: music](#5-app-music)
6. [APP: playlists](#6-app-playlists)
7. [APP: artists](#7-app-artists)
8. [APP: social](#8-app-social)
9. [APP: notifications](#9-app-notifications)
10. [APP: search](#10-app-search)
11. [Sơ đồ quan hệ (ERD)](#11-sơ-đồ-quan-hệ-erd)
12. [Quy ước chung & Triển khai](#12-quy-ước-chung--triển-khai)
13. [Bảo mật & Xử lý rủi ro](#13-bảo-mật--xử-lý-rủi-ro)

---

# 1. Tổng Quan Kiến Trúc

Dự án sử dụng Django thuần (không DRF Serializer, không Pydantic) với kiến trúc phân tầng rõ ràng. Mỗi Django App đại diện cho một nghiệp vụ độc lập.

## 1.1 Cấu Trúc Thư Mục Mỗi App

```
app_name/
├── models.py        # Định nghĩa schema Database (Django ORM)
├── services.py      # Logic Ghi: Create, Update, Delete
├── selectors.py     # Logic Đọc: Truy vấn, Lọc dữ liệu
├── views.py         # Tầng HTTP: Nhận Request, trả về JsonResponse
├── validators.py    # Kiểm tra dữ liệu đầu vào
├── exceptions.py    # Custom exception nghiệp vụ
└── urls.py          # Định tuyến URL
```

## 1.2 Nguyên Tắc Phân Tầng

| Tầng | Trách nhiệm | Không được làm |
|------|-------------|----------------|
| `views.py` | Nhận request, gọi validator/service, trả JsonResponse | Chứa business logic, truy vấn DB trực tiếp |
| `validators.py` | Kiểm tra kiểu dữ liệu, bắt buộc, độ dài, format | Gọi service, truy vấn DB |
| `services.py` | Toàn bộ logic Ghi (Create/Update/Delete) | Trả về HTTP response, chứa query phức tạp |
| `selectors.py` | Toàn bộ logic Đọc (truy vấn, lọc, thống kê) | Ghi dữ liệu, raise HTTP exception |
| `models.py` | Định nghĩa schema, quan hệ, constraints | Chứa business logic phức tạp |
| `exceptions.py` | Custom exception cho từng loại lỗi nghiệp vụ | Chứa logic xử lý |

> ⚠️ **Lưu ý quan trọng:** App `search` **phải** tuân thủ nguyên tắc này — views.py không được import và query models trực tiếp. Mọi truy vấn phải đi qua `search/selectors.py`. *(Fix R7)*

## 1.3 Danh Sách Apps

| App | Nghiệp vụ chính |
|-----|-----------------|
| `accounts` | Đăng ký, đăng nhập, quản lý tài khoản, xác thực nghệ sĩ, block user |
| `music` | Bài hát, thể loại, lượt thích, đánh giá, bình luận, lịch sử nghe, report |
| `playlists` | Playlist của người dùng, quản lý bài hát trong playlist |
| `artists` | Hồ sơ nghệ sĩ, thống kê hoạt động, quản lý nhạc đã đăng |
| `social` | Theo dõi user/nghệ sĩ, hoạt động bạn bè, tâm trạng (mood) |
| `notifications` | Thông báo trong hệ thống |
| `search` | Tìm kiếm nhạc, nghệ sĩ, playlist, người dùng |

---

# 2. Authentication

## 2.1 Cơ Chế: Django Session + CSRF Token

Dự án dùng cơ chế xác thực mặc định của Django: Session-based authentication kết hợp CSRF Token để bảo vệ các request thay đổi dữ liệu.

| Thành phần | Vai trò | Lưu ở đâu |
|------------|---------|-----------|
| Session ID | Định danh phiên đăng nhập, Django tự quản lý | Cookie: `sessionid` (httpOnly) |
| CSRF Token | Bảo vệ chống tấn công Cross-Site Request Forgery | Cookie: `csrftoken` (readable by JS) |

**Luồng hoạt động:**

1. Client gọi `GET /api/auth/csrf/` để lấy CSRF token lần đầu (hoặc đọc từ cookie `csrftoken`)
2. Client đăng nhập qua `POST /api/auth/login/` — Django tạo session, set cookie `sessionid`
3. Mọi request `POST/PUT/PATCH/DELETE` sau đó phải gửi kèm CSRF token trong header `X-CSRFToken`
4. Django tự xác thực session qua cookie `sessionid`, gán `request.user` tự động

## 2.2 Cấu Hình Django (settings.py)

```python
INSTALLED_APPS = [..., 'django.contrib.sessions', ...]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',   # CORS — phải đứng trước CommonMiddleware
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    ...
]

# Session config
SESSION_ENGINE          = 'django.contrib.sessions.backends.db'
SESSION_COOKIE_AGE      = 1209600      # 14 ngày (tính bằng giây)
SESSION_COOKIE_HTTPONLY = True         # JS không đọc được sessionid
SESSION_COOKIE_SECURE   = True         # Chỉ gửi qua HTTPS (production)
SESSION_COOKIE_SAMESITE = 'Lax'       # Bảo vệ CSRF cơ bản

# CSRF config
CSRF_COOKIE_HTTPONLY  = False          # JS cần đọc csrftoken để gửi kèm header
CSRF_COOKIE_SECURE    = True           # Chỉ gửi qua HTTPS (production)
CSRF_COOKIE_SAMESITE  = 'Lax'
CSRF_TRUSTED_ORIGINS  = ['https://yourdomain.com']

# CORS — chỉ whitelist domain cụ thể, KHÔNG dùng CORS_ALLOW_ALL_ORIGINS=True (Fix R3)
CORS_ALLOWED_ORIGINS = [
    'https://yourdomain.com',
    'https://www.yourdomain.com',
]
CORS_ALLOW_CREDENTIALS = True
```

> ⚠️ **Bảo mật CORS (Fix R3):** Tuyệt đối **không** dùng `CORS_ALLOW_ALL_ORIGINS = True` trên production. Chỉ whitelist domain frontend chính xác. Trong môi trường dev có thể dùng `localhost:3000`, `localhost:8080` nhưng phải tắt trên production.

## 2.3 Gửi CSRF Token Trong Request

Client phải gửi CSRF token theo một trong hai cách:

### Cách 1 — Header X-CSRFToken (khuyến nghị cho AJAX/fetch)

```javascript
// Đọc csrftoken từ cookie
const csrfToken = document.cookie.match(/csrftoken=([^;]+)/)?.[1];

fetch('/api/music/songs/', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'X-CSRFToken': csrfToken,
  },
  credentials: 'include',   // bắt buộc để gửi kèm cookie sessionid
  body: JSON.stringify(data),
});
```

### Cách 2 — Form field csrfmiddlewaretoken (HTML form truyền thống)

```html
<input type="hidden" name="csrfmiddlewaretoken" value="{{ csrf_token }}">
```

## 2.4 Mức Phân Quyền

| Ký hiệu | Mô tả |
|---------|-------|
| `Public` | Không cần đăng nhập, GET không cần CSRF |
| `Public+CSRF` | Không cần đăng nhập nhưng là POST nên cần CSRF token |
| `Auth` | Phải đăng nhập (sessionid hợp lệ); GET không cần CSRF |
| `Auth+CSRF` | Phải đăng nhập và gửi CSRF token (POST/PUT/PATCH/DELETE) |
| `Artist` | Phải đăng nhập và có `role = artist` |
| `Admin` | Phải đăng nhập và có `role = admin` |
| `Owner` | Phải là chủ sở hữu tài nguyên đó |

## 2.5 Decorator Xác Thực

```python
from functools import wraps
from django.http import JsonResponse

def require_auth(view_func):
    """Kiểm tra đã đăng nhập — trả 401 thay vì redirect login."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse(
                {'success': False, 'error': {'code': 'AUTH_REQUIRED', 'message': 'Bạn cần đăng nhập'}},
                status=401,
            )
        if not request.user.is_active:
            return JsonResponse(
                {'success': False, 'error': {'code': 'ACCOUNT_INACTIVE', 'message': 'Tài khoản đã bị khóa'}},
                status=403,
            )
        return view_func(request, *args, **kwargs)
    return wrapper

def require_artist(view_func):
    """Kiểm tra role = artist."""
    @wraps(view_func)
    @require_auth
    def wrapper(request, *args, **kwargs):
        if request.user.role != 'artist':
            return JsonResponse(
                {'success': False, 'error': {'code': 'ARTIST_ONLY', 'message': 'Chỉ nghệ sĩ mới được thực hiện'}},
                status=403,
            )
        return view_func(request, *args, **kwargs)
    return wrapper

def require_admin(view_func):
    """Kiểm tra role = admin."""
    @wraps(view_func)
    @require_auth
    def wrapper(request, *args, **kwargs):
        if request.user.role != 'admin':
            return JsonResponse(
                {'success': False, 'error': {'code': 'ADMIN_ONLY', 'message': 'Chỉ admin mới được thực hiện'}},
                status=403,
            )
        return view_func(request, *args, **kwargs)
    return wrapper

# Dùng trong views — thứ tự decorator: csrf_protect ngoài, require_auth trong
@csrf_protect
@require_auth
def song_create(request): ...
```

## 2.6 API Endpoints Authentication

| Method | Endpoint | Mô tả | Quyền |
|--------|----------|-------|-------|
| `GET` | `/api/auth/csrf/` | Lấy CSRF token — set cookie csrftoken | Public |
| `POST` | `/api/auth/register/` | Đăng ký tài khoản mới | Public+CSRF |
| `POST` | `/api/auth/login/` | Đăng nhập — Django set cookie sessionid | Public+CSRF |
| `POST` | `/api/auth/logout/` | Đăng xuất — Django xóa session | Auth+CSRF |
| `GET` | `/api/auth/me/` | Kiểm tra trạng thái đăng nhập hiện tại | Auth |
| `POST` | `/api/auth/password/reset/request/` | Gửi email đặt lại mật khẩu | Public+CSRF |
| `POST` | `/api/auth/password/reset/confirm/` | Đặt lại mật khẩu qua token email | Public+CSRF |
| `POST` | `/api/auth/password/change/` | Đổi mật khẩu khi đã đăng nhập | Auth+CSRF |

## 2.7 Request / Response Mẫu

### GET /api/auth/csrf/ — Lấy CSRF token

```
Response 200:
  Set-Cookie: csrftoken=abc123...; Path=/; SameSite=Lax
  Body: { "success": true, "detail": "CSRF cookie set" }
```

### POST /api/auth/login/

```
Request Headers: X-CSRFToken: abc123...
Request Body:    { "email": "john@example.com", "password": "Abc@1234" }

Response 200:
  Set-Cookie: sessionid=xyz...; HttpOnly; Secure; SameSite=Lax
  Body: { "success": true, "data": { "id": "uuid", "username": "john", "role": "user" } }
```

### POST /api/auth/register/

```
Request Headers: X-CSRFToken: abc123...
Request Body:    { "username": "john", "email": "john@example.com", "password": "Abc@1234" }

Response 201: { "success": true, "data": { "id": "uuid", "username": "john", "email": "john@example.com", "role": "user" } }
```

### POST /api/auth/logout/

```
Request Headers: X-CSRFToken: abc123...
Response 200: { "success": true, "message": "Đã đăng xuất" }
```

*(Django gọi `request.session.flush()` — xóa session khỏi DB và clear cookie)*

### GET /api/auth/me/

```
Response 200: { "success": true, "data": { "id": "uuid", "username": "john", "role": "user" } }
Response 401: { "success": false, "error": { "code": "AUTH_REQUIRED" } }
```

---

# 3. Quy Ước Chung API

## 3.1 URL Pattern

| Pattern | Ví dụ |
|---------|-------|
| Danh sách | `/api/<resource>/` |
| Chi tiết | `/api/<resource>/<id>/` |
| Hành động đặc biệt | `/api/<resource>/<id>/<action>/` |
| Nested resource | `/api/<resource>/<id>/<sub-resource>/` |

## 3.2 HTTP Methods

| Method | Dùng khi |
|--------|----------|
| `GET` | Lấy dữ liệu (không thay đổi state) |
| `POST` | Tạo mới tài nguyên hoặc thực hiện action |
| `PUT` | Cập nhật toàn bộ tài nguyên |
| `PATCH` | Cập nhật một phần tài nguyên |
| `DELETE` | Xóa tài nguyên |

## 3.3 Response Format

Tất cả response đều là JSON với cấu trúc thống nhất:

```json
// Success
{ "success": true, "data": { ... }, "message": "..." }

// Success - danh sách có phân trang
{
  "success": true,
  "data": {
    "items": [...],
    "pagination": { "page": 1, "page_size": 20, "total": 150, "total_pages": 8 }
  }
}

// Error
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Email không hợp lệ",
    "fields": { "email": ["Email không đúng định dạng"] }
  }
}
```

## 3.4 HTTP Status Codes

| Code | Tên | Dùng khi |
|------|-----|----------|
| `200` | OK | GET thành công, PUT/PATCH thành công |
| `201` | Created | POST tạo mới thành công |
| `204` | No Content | DELETE thành công |
| `400` | Bad Request | Dữ liệu đầu vào không hợp lệ (ValidationError) |
| `401` | Unauthorized | Chưa đăng nhập hoặc token hết hạn |
| `403` | Forbidden | Đã đăng nhập nhưng không đủ quyền |
| `404` | Not Found | Tài nguyên không tồn tại |
| `409` | Conflict | Trùng lặp dữ liệu (email đã tồn tại, đã like rồi...) |
| `429` | Too Many Requests | Vượt quá rate limit *(Fix R6)* |
| `500` | Internal Server Error | Lỗi server không mong muốn |

## 3.5 Phân Trang (Pagination)

Tất cả API trả về danh sách đều hỗ trợ phân trang qua query params:

```
GET /api/music/songs/?page=2&page_size=20
```

| Query Param | Default | Mô tả |
|-------------|---------|-------|
| `page` | `1` | Trang hiện tại (bắt đầu từ 1) |
| `page_size` | `20` | Số item mỗi trang (tối đa 100) |
| `ordering` | `-created_at` | Sắp xếp theo trường, dùng `-` để DESC |

## 3.6 Error Codes

| Error Code | Mô tả |
|------------|-------|
| `VALIDATION_ERROR` | Dữ liệu đầu vào không hợp lệ |
| `AUTH_REQUIRED` | Cần đăng nhập |
| `PERMISSION_DENIED` | Không đủ quyền |
| `NOT_FOUND` | Tài nguyên không tìm thấy |
| `ALREADY_EXISTS` | Dữ liệu đã tồn tại (like, follow, email...) |
| `TOKEN_EXPIRED` | Access token đã hết hạn |
| `TOKEN_INVALID` | Token không hợp lệ |
| `BLOCKED` | Người dùng đã bị chặn |
| `ACCOUNT_INACTIVE` | Tài khoản bị khóa |
| `ARTIST_ONLY` | Chỉ nghệ sĩ mới được thực hiện |
| `ADMIN_ONLY` | Chỉ admin mới được thực hiện |
| `RATE_LIMITED` | Vượt quá giới hạn request *(Fix R6)* |

---

# 4. APP: accounts

Quản lý toàn bộ vòng đời tài khoản: đăng ký, đăng nhập, phân quyền, xác thực nghệ sĩ, block user.

## 4.1 Models

### User (kế thừa AbstractUser)

| Trường | Kiểu | Mô tả |
|--------|------|-------|
| `id` | UUIDField (PK) | Khóa chính UUID |
| `username` | CharField unique | Tên đăng nhập |
| `email` | EmailField unique | Email đăng nhập |
| `password` | CharField | Mật khẩu đã hash (PBKDF2/bcrypt) |
| `display_name` | CharField | Tên hiển thị |
| `avatar` | ImageField | Ảnh đại diện |
| `bio` | TextField | Giới thiệu bản thân |
| `role` | CharField | Phân quyền: `user` / `artist` / `admin` |
| `is_active` | BooleanField | Trạng thái tài khoản |
| `is_private` | BooleanField | Chế độ riêng tư |
| `created_at` | DateTimeField auto | Ngày tạo |
| `updated_at` | DateTimeField auto | Ngày cập nhật |

### ArtistVerification

| Trường | Kiểu | Mô tả |
|--------|------|-------|
| `id` | UUIDField (PK) | Khóa chính UUID |
| `user` | FK → User | Người dùng yêu cầu xác thực |
| `real_name` | CharField | Tên thật |
| `id_card_image` | ImageField | Ảnh CMND/CCCD (lưu S3 private bucket) |
| `note` | TextField null | Ghi chú bổ sung |
| `status` | CharField | `pending` / `approved` / `rejected` |
| `reviewed_by` | FK → User null | Admin duyệt |
| `reviewed_at` | DateTimeField null | Thời điểm duyệt |
| `created_at` | DateTimeField auto | Ngày tạo |

### BlockList

| Trường | Kiểu | Mô tả |
|--------|------|-------|
| `id` | UUIDField (PK) | Khóa chính UUID |
| `blocker` | FK → User | Người thực hiện chặn |
| `blocked` | FK → User | Người bị chặn |
| `created_at` | DateTimeField auto | Ngày chặn |

## 4.2 API Endpoints

### Tài khoản cá nhân

| Method | Endpoint | Mô tả | Quyền |
|--------|----------|-------|-------|
| `GET` | `/api/accounts/me/` | Xem thông tin cá nhân | Auth |
| `PATCH` | `/api/accounts/me/` | Cập nhật thông tin cá nhân | Auth+CSRF |
| `POST` | `/api/accounts/me/avatar/` | Upload ảnh đại diện | Auth+CSRF |
| `PATCH` | `/api/accounts/me/privacy/` | Cập nhật cài đặt riêng tư | Auth+CSRF |
| `GET` | `/api/accounts/users/<id>/` | Xem hồ sơ công khai | Public |

### Xác thực nghệ sĩ

| Method | Endpoint | Mô tả | Quyền |
|--------|----------|-------|-------|
| `POST` | `/api/accounts/artist-verification/` | Nộp yêu cầu xác thực nghệ sĩ | Auth+CSRF |
| `GET` | `/api/accounts/artist-verification/me/` | Xem trạng thái yêu cầu của mình | Auth |
| `GET` | `/api/accounts/admin/verifications/` | Danh sách yêu cầu chờ duyệt | Admin |
| `POST` | `/api/accounts/admin/verifications/<id>/approve/` | Duyệt xác thực nghệ sĩ | Admin |
| `POST` | `/api/accounts/admin/verifications/<id>/reject/` | Từ chối xác thực | Admin |
| `POST` | `/api/accounts/admin/users/<id>/revoke-artist/` | Thu hồi tư cách nghệ sĩ | Admin |

### Quản lý tài khoản (Admin)

| Method | Endpoint | Mô tả | Quyền |
|--------|----------|-------|-------|
| `GET` | `/api/accounts/admin/users/` | Danh sách tất cả user | Admin |
| `POST` | `/api/accounts/admin/users/<id>/deactivate/` | Khóa tài khoản | Admin |
| `POST` | `/api/accounts/admin/users/<id>/activate/` | Mở khóa tài khoản | Admin |

### Block user

| Method | Endpoint | Mô tả | Quyền |
|--------|----------|-------|-------|
| `GET` | `/api/accounts/me/blocklist/` | Danh sách người đã chặn | Auth |
| `POST` | `/api/accounts/me/blocklist/<id>/` | Chặn người dùng | Auth+CSRF |
| `DELETE` | `/api/accounts/me/blocklist/<id>/` | Bỏ chặn người dùng | Auth+CSRF |

## 4.3 Validation Rules — File Upload *(Fix R3, R4)*

> **Bắt buộc** kiểm tra cả `content_type` lẫn kích thước cho mọi file upload.

| Loại file | MIME types cho phép | Kích thước tối đa | Ghi chú |
|-----------|---------------------|-------------------|---------|
| Avatar user/artist | `image/jpeg`, `image/png`, `image/webp` | 5 MB | Resize về max 1024×1024 trước khi lưu |
| Ảnh bìa song/playlist/artist | `image/jpeg`, `image/png`, `image/webp` | 5 MB | — |
| CMND/CCCD nghệ sĩ | `image/jpeg`, `image/png`, `application/pdf` | 10 MB | Lưu S3 **private** bucket |

```python
# accounts/validators.py — validate_verification_submit()
ALLOWED_ID_TYPES = ['image/jpeg', 'image/png', 'application/pdf']
MAX_ID_SIZE      = 10 * 1024 * 1024  # 10 MB

if 'id_card_image' not in files:
    errors['id_card_image'] = ['Ảnh CMND/CCCD là bắt buộc']
else:
    f = files['id_card_image']
    if f.content_type not in ALLOWED_ID_TYPES:
        errors['id_card_image'] = ['Chỉ chấp nhận JPG, PNG hoặc PDF']
    elif f.size > MAX_ID_SIZE:
        errors['id_card_image'] = ['File tối đa 10 MB']
```

## 4.4 Block Interaction Policy *(Fix R10)*

Khi người dùng A chặn người dùng B, hệ thống phải áp dụng các rule sau **ở tầng selectors/services**:

| Hành động của B (bị chặn) | Behavior |
|---------------------------|----------|
| Xem profile của A | Trả `404` (giả vờ không tồn tại) |
| Xem bài hát của A | Ẩn khỏi danh sách; trả `404` khi truy cập trực tiếp |
| Follow A | Trả `403 BLOCKED` |
| Bình luận bài hát của A | Trả `403 BLOCKED` |
| A nhận thông báo từ B | Không tạo notification |

```python
# accounts/selectors.py
def is_blocked(viewer_id, target_id):
    """Kiểm tra target có bị viewer chặn không."""
    return BlockList.objects.filter(
        blocker_id=target_id, blocked_id=viewer_id
    ).exists()

# Dùng trong views trước khi trả profile
if is_blocked(request.user.id, target_user.id):
    raise NotFound('Người dùng không tìm thấy')
```

## 4.5 Request/Response Mẫu

### PATCH /api/accounts/me/

```json
// Request Body
{ "display_name": "John Doe", "bio": "Music lover" }

// Response 200
{ "success": true, "data": { "id": "uuid", "display_name": "John Doe", "bio": "Music lover", "role": "user", "is_private": false } }
```

### POST /api/accounts/artist-verification/

```
Request: multipart/form-data { real_name, id_card_image (file), note }
Response 201: { "success": true, "data": { "id": "uuid", "status": "pending", "created_at": "..." } }
```

---

# 5. APP: music

Quản lý toàn bộ nội dung âm nhạc: bài hát, thể loại, lượt thích, đánh giá, bình luận, báo cáo vi phạm.

## 5.1 Models (tóm tắt)

| Model | Các trường chính |
|-------|-----------------|
| `Genre` | id (UUID), name (unique), slug, description, created_at |
| `Song` | id, title, artist (FK User), genre (FK), audio_file, cover_image, lyrics, duration, status (`draft`/`published`/`hidden`), allow_download, is_trending, play_count, released_at |
| `Like` | id, user (FK), song (FK), created_at — `unique_together: user+song` |
| `Rating` | id, user (FK), song (FK), score (1–5), created_at — `unique_together: user+song` |
| `Comment` | id, user (FK), song (FK), parent (FK self null), content, is_hidden, created_at |
| `CommentLike` | id, user (FK), comment (FK), created_at — `unique_together: user+comment` |
| `ListenHistory` | id, user (FK), song (FK), listened_at |
| `Report` | id, reporter (FK), target_type (song/comment/user), target_id (UUID), reason, description null, status (pending/resolved/dismissed), resolved_by null, created_at |

## 5.2 API Endpoints

### Thể loại nhạc (Genre)

| Method | Endpoint | Mô tả | Quyền |
|--------|----------|-------|-------|
| `GET` | `/api/music/genres/` | Danh sách tất cả thể loại | Public |
| `POST` | `/api/music/genres/` | Tạo thể loại mới | Admin |
| `PUT` | `/api/music/genres/<id>/` | Cập nhật thể loại | Admin |
| `DELETE` | `/api/music/genres/<id>/` | Xóa thể loại | Admin |

### Bài hát (Song)

| Method | Endpoint | Mô tả | Quyền |
|--------|----------|-------|-------|
| `GET` | `/api/music/songs/` | Danh sách bài hát (filter, search, phân trang) | Public |
| `POST` | `/api/music/songs/` | Nghệ sĩ upload bài hát mới | Artist |
| `GET` | `/api/music/songs/<id>/` | Chi tiết bài hát (kèm like count, avg rating) | Public |
| `PATCH` | `/api/music/songs/<id>/` | Cập nhật thông tin bài hát | Artist+Owner |
| `DELETE` | `/api/music/songs/<id>/` | Xóa bài hát | Artist+Owner |
| `POST` | `/api/music/songs/<id>/hide/` | Nghệ sĩ ẩn bài hát của mình | Artist+Owner |
| **`POST`** | **`/api/music/songs/<id>/publish/`** | **Phát hành bài hát (draft → published)** *(Fix R9)* | **Artist+Owner** |
| `POST` | `/api/music/songs/<id>/play/` | Ghi lượt nghe (có dedup 5 phút) | Auth |
| **`GET`** | **`/api/music/songs/<id>/download/`** | **Tải file audio (chỉ khi allow_download=True)** *(Fix R2)* | **Auth** |
| `GET` | `/api/music/songs/trending/` | Danh sách bài hát trending | Public |
| `POST` | `/api/music/admin/songs/<id>/trending/` | Admin bật/tắt trending | Admin |

### Filter bài hát (query params)

| Param | Mô tả | Ví dụ |
|-------|-------|-------|
| `q` | Tìm kiếm theo tên bài hát | `q=shape+of+you` |
| `genre` | Lọc theo slug thể loại | `genre=pop` |
| `artist_id` | Lọc theo ID nghệ sĩ | `artist_id=uuid` |
| `status` | Lọc theo trạng thái (cho artist/admin) | `status=published` |
| `ordering` | Sắp xếp | `ordering=-play_count` |

### Like bài hát

| Method | Endpoint | Mô tả | Quyền |
|--------|----------|-------|-------|
| `POST` | `/api/music/songs/<id>/like/` | Thích bài hát (toggle: like/unlike) | Auth+CSRF |
| `GET` | `/api/music/songs/<id>/likes/` | Số lượt thích của bài hát | Public |

### Đánh giá (Rating)

| Method | Endpoint | Mô tả | Quyền |
|--------|----------|-------|-------|
| `POST` | `/api/music/songs/<id>/rate/` | Đánh giá bài hát (1–5 sao) | Auth+CSRF |
| `GET` | `/api/music/songs/<id>/rating/` | Điểm đánh giá trung bình | Public |

### Bình luận (Comment)

| Method | Endpoint | Mô tả | Quyền |
|--------|----------|-------|-------|
| `GET` | `/api/music/songs/<id>/comments/` | Danh sách bình luận | Public |
| `POST` | `/api/music/songs/<id>/comments/` | Thêm bình luận / trả lời | Auth+CSRF |
| `DELETE` | `/api/music/comments/<id>/` | Xóa bình luận của mình | Auth+Owner+CSRF |
| `POST` | `/api/music/comments/<id>/like/` | Thích/bỏ thích bình luận (toggle) | Auth+CSRF |
| `POST` | `/api/music/admin/comments/<id>/hide/` | Admin ẩn bình luận vi phạm | Admin |

### Lịch sử nghe

| Method | Endpoint | Mô tả | Quyền |
|--------|----------|-------|-------|
| `GET` | `/api/music/me/history/` | Lịch sử nghe của tôi (có phân trang) | Auth |
| `DELETE` | `/api/music/me/history/` | Xóa toàn bộ lịch sử nghe | Auth+CSRF |

### Báo cáo vi phạm

| Method | Endpoint | Mô tả | Quyền |
|--------|----------|-------|-------|
| `POST` | `/api/music/reports/` | Gửi báo cáo vi phạm (bài hát/bình luận/user) | Auth+CSRF |
| `GET` | `/api/music/admin/reports/` | Danh sách báo cáo (filter theo status) | Admin |
| `POST` | `/api/music/admin/reports/<id>/resolve/` | Admin xử lý báo cáo | Admin |

## 5.3 Quy tắc nghiệp vụ quan trọng

### play_count — Atomic Increment *(Fix R1)*

> ❌ **KHÔNG được dùng:**
> ```python
> Song.objects.filter(id=song.id).update(play_count=song.play_count + 1)
> ```
> Cách này gây race condition: hai request đồng thời cùng đọc `play_count=100` rồi cùng ghi `101`, mất 1 lượt đếm.

> ✅ **Bắt buộc dùng Django `F()` expression:**
> ```python
> from django.db.models import F
>
> Song.objects.filter(id=song.id).update(play_count=F('play_count') + 1)
> ```
> `F()` dịch ra SQL `UPDATE ... SET play_count = play_count + 1` — atomic ở cấp DB, không bao giờ mất dữ liệu.

### ListenHistory — Chống spam (dedup 5 phút) *(Fix R8)*

Mỗi user chỉ được tính 1 lượt nghe cho 1 bài trong vòng 5 phút:

```python
# music/services.py — record_play()
from django.db.models import F
from django.utils import timezone
from datetime import timedelta

def record_play(user, song):
    """Ghi lượt nghe — atomic F() increment + dedup 5 phút."""
    cutoff = timezone.now() - timedelta(minutes=5)
    already = ListenHistory.objects.filter(
        user=user, song=song, listened_at__gte=cutoff
    ).exists()
    if already:
        return  # Không tăng counter, không tạo bản ghi trùng

    Song.objects.filter(id=song.id).update(play_count=F('play_count') + 1)
    ListenHistory.objects.create(user=user, song=song)

    # Log FriendActivity
    try:
        from social.services import create_friend_activity
        create_friend_activity(user=user, activity_type='playing', song=song)
    except Exception:
        pass
```

### Download nhạc *(Fix R2)*

```python
# music/views.py — SongDownloadView
@method_decorator([require_auth], name='dispatch')
class SongDownloadView(View):
    def get(self, request, song_id):
        song = get_song_by_id(song_id)
        if not song:
            return JsonResponse({'success': False, 'error': {'code': 'NOT_FOUND'}}, status=404)
        if not song.status == Song.STATUS_PUBLISHED:
            return JsonResponse({'success': False, 'error': {'code': 'NOT_FOUND'}}, status=404)
        if not song.allow_download:
            return JsonResponse({'success': False, 'error': {'code': 'PERMISSION_DENIED', 'message': 'Bài hát này không cho phép tải về'}}, status=403)

        # Với S3: redirect đến presigned URL (khuyến nghị)
        # Với local storage (dev): dùng FileResponse
        from django.http import FileResponse
        return FileResponse(
            song.audio_file.open('rb'),
            as_attachment=True,
            filename=f"{song.title}.mp3",
        )
```

### Validate Audio File MIME type *(Fix R5)*

```python
# music/validators.py — validate_song_create()
ALLOWED_AUDIO_TYPES = ['audio/mpeg', 'audio/flac', 'audio/wav', 'audio/ogg', 'audio/mp4']
MAX_AUDIO_SIZE = 50 * 1024 * 1024  # 50 MB

if 'audio_file' not in files:
    errors['audio_file'] = ['File audio là bắt buộc']
else:
    audio = files['audio_file']
    if audio.content_type not in ALLOWED_AUDIO_TYPES:
        errors['audio_file'] = [f'Chỉ chấp nhận: {", ".join(ALLOWED_AUDIO_TYPES)}']
    elif audio.size > MAX_AUDIO_SIZE:
        errors['audio_file'] = ['File audio tối đa 50 MB']
```

## 5.4 Request/Response Mẫu

### POST /api/music/songs/ — Upload bài hát

```
Request: multipart/form-data
{ title, genre_id, audio_file (file), cover_image (file), lyrics?, duration, allow_download, released_at? }

Response 201:
{ "success": true, "data": { "id": "uuid", "title": "...", "status": "draft", "artist": {...}, "genre": {...} } }
```

### POST /api/music/songs/\<id\>/publish/ — Phát hành bài hát *(Fix R9)*

```json
// Response 200
{ "success": true, "data": { "id": "uuid", "status": "published", "released_at": "2025-06-10T..." } }

// Lỗi nếu không phải owner
{ "success": false, "error": { "code": "PERMISSION_DENIED" } }
```

### GET /api/music/songs/\<id\>/ — Chi tiết bài hát

```json
{
  "success": true,
  "data": {
    "id": "uuid", "title": "...",
    "artist": { "id": "...", "stage_name": "..." },
    "genre": { "id": "...", "name": "Pop" },
    "duration": 214, "play_count": 15000,
    "like_count": 320, "avg_rating": 4.2,
    "allow_download": true, "is_trending": false
  }
}
```

### POST /api/music/songs/\<id\>/comments/ — Thêm bình luận

```json
// Request Body
{ "content": "Bài hát hay quá!", "parent_id": null }

// Response 201
{ "success": true, "data": { "id": "uuid", "content": "...", "user": {...}, "created_at": "..." } }
```

### POST /api/music/reports/ — Gửi báo cáo

```json
// Request Body
{ "target_type": "song", "target_id": "uuid", "reason": "copyright", "description": "..." }

// Response 201
{ "success": true, "data": { "id": "uuid", "status": "pending" } }
```

---

# 6. APP: playlists

Quản lý playlist do người dùng tạo, thêm/xóa bài hát, cài đặt quyền truy cập.

## 6.1 Models

### Playlist

| Trường | Kiểu | Mô tả |
|--------|------|-------|
| `id` | UUIDField (PK) | Khóa chính UUID |
| `owner` | FK → User | Người tạo playlist |
| `title` | CharField | Tên playlist |
| `description` | TextField null | Mô tả |
| `cover_image` | ImageField null | Ảnh bìa playlist |
| `is_public` | BooleanField default True | Công khai hay riêng tư |
| `created_at` | DateTimeField auto | Ngày tạo |
| `updated_at` | DateTimeField auto | Ngày cập nhật |

### PlaylistSong

| Trường | Kiểu | Mô tả |
|--------|------|-------|
| `id` | UUIDField (PK) | Khóa chính UUID |
| `playlist` | FK → Playlist | Playlist chứa bài hát |
| `song` | FK → Song | Bài hát trong playlist |
| `order` | PositiveIntegerField | Thứ tự bài hát trong playlist |
| `added_at` | DateTimeField auto | Ngày thêm vào |

## 6.2 API Endpoints

| Method | Endpoint | Mô tả | Quyền |
|--------|----------|-------|-------|
| `GET` | `/api/playlists/` | Danh sách playlist của tôi | Auth |
| `POST` | `/api/playlists/` | Tạo playlist mới | Auth+CSRF |
| `GET` | `/api/playlists/<id>/` | Chi tiết playlist (kiểm tra quyền xem) | Auth/Public |
| `PATCH` | `/api/playlists/<id>/` | Chỉnh sửa tên, mô tả, ảnh bìa | Auth+Owner+CSRF |
| `DELETE` | `/api/playlists/<id>/` | Xóa playlist | Auth+Owner+CSRF |
| `PATCH` | `/api/playlists/<id>/visibility/` | Đặt công khai / riêng tư | Auth+Owner+CSRF |
| `GET` | `/api/playlists/<id>/songs/` | Danh sách bài hát trong playlist | Auth/Public |
| `POST` | `/api/playlists/<id>/songs/` | Thêm bài hát vào playlist | Auth+Owner+CSRF |
| `DELETE` | `/api/playlists/<id>/songs/<song_id>/` | Xóa bài hát khỏi playlist | Auth+Owner+CSRF |
| `PATCH` | `/api/playlists/<id>/songs/reorder/` | Sắp xếp lại thứ tự bài hát | Auth+Owner+CSRF |

## 6.3 Request/Response Mẫu

### POST /api/playlists/

```json
// Request Body
{ "title": "My Chill Playlist", "description": "...", "is_public": true }

// Response 201
{ "success": true, "data": { "id": "uuid", "title": "...", "is_public": true, "song_count": 0 } }
```

### POST /api/playlists/\<id\>/songs/

```json
// Request Body
{ "song_id": "uuid" }

// Response 201
{ "success": true, "data": { "song": { "id": "...", "title": "..." }, "order": 5 } }
```

### PATCH /api/playlists/\<id\>/songs/reorder/

```json
// Request Body
{ "song_ids": ["uuid1", "uuid2", "uuid3"] }

// Response 200
{ "success": true, "message": "Đã cập nhật thứ tự" }
```

---

# 7. APP: artists

Quản lý hồ sơ nghệ sĩ và thống kê chi tiết về hoạt động đăng nhạc.

## 7.1 Models

### ArtistProfile

| Trường | Kiểu | Mô tả |
|--------|------|-------|
| `id` | UUIDField (PK) | Khóa chính UUID |
| `user` | OneToOneField → User | Tài khoản nghệ sĩ |
| `stage_name` | CharField | Tên nghệ danh |
| `bio` | TextField null | Tiểu sử nghệ sĩ |
| `avatar` | ImageField null | Ảnh đại diện riêng cho artist page |
| `cover_image` | ImageField null | Ảnh bìa trang nghệ sĩ |
| `website` | URLField null | Website cá nhân (chỉ chấp nhận http/https) |
| `created_at` | DateTimeField auto | Ngày tạo hồ sơ |

> **Lưu ý:** `ArtistProfile.avatar` ưu tiên hiển thị trên trang nghệ sĩ. Nếu null, fallback về `User.avatar`.

## 7.2 API Endpoints

| Method | Endpoint | Mô tả | Quyền |
|--------|----------|-------|-------|
| `GET` | `/api/artists/<id>/` | Hồ sơ công khai của nghệ sĩ | Public |
| `PATCH` | `/api/artists/me/` | Cập nhật thông tin hồ sơ nghệ sĩ | Artist+CSRF |
| `POST` | `/api/artists/me/avatar/` | Upload ảnh đại diện artist | Artist+CSRF |
| `POST` | `/api/artists/me/cover/` | Upload ảnh bìa artist | Artist+CSRF |
| `GET` | `/api/artists/me/songs/` | Danh sách bài hát của tôi (có filter status) | Artist |
| `GET` | `/api/artists/me/stats/` | Thống kê tổng: lượt nghe, thích, bình luận, số bài | Artist |
| `GET` | `/api/artists/me/stats/songs/` | Thống kê chi tiết theo từng bài hát | Artist |

## 7.3 Response Mẫu

### GET /api/artists/\<id\>/

```json
{
  "success": true,
  "data": {
    "id": "uuid", "stage_name": "...", "bio": "...",
    "avatar": "url", "cover_image": "url", "website": "...",
    "follower_count": 1500, "song_count": 24
  }
}
```

### GET /api/artists/me/stats/

```json
{
  "success": true,
  "data": { "total_plays": 50000, "total_likes": 3200, "total_comments": 450, "total_songs": 24 }
}
```

---

# 8. APP: social

Quản lý các tính năng mạng xã hội: theo dõi, hoạt động bạn bè, tâm trạng (mood).

## 8.1 Models

### Follow

| Trường | Kiểu | Mô tả |
|--------|------|-------|
| `id` | UUIDField (PK) | Khóa chính UUID |
| `follower` | FK → User | Người theo dõi |
| `following` | FK → User | Người được theo dõi |
| `created_at` | DateTimeField auto | Ngày theo dõi |

### Mood (Tâm trạng)

| Trường | Kiểu | Mô tả |
|--------|------|-------|
| `id` | UUIDField (PK) | Khóa chính UUID |
| `user` | FK → User | Người đăng tâm trạng |
| `mood_type` | CharField | `happy` / `sad` / `love` / `angry` / `chill` / `party` |
| `status_text` | TextField null | Dòng trạng thái tùy ý |
| `song` | FK → Song null | Bài hát đính kèm tâm trạng |
| `expires_at` | DateTimeField null | Thời điểm hết hiển thị (null = không hết hạn) |
| `created_at` | DateTimeField auto | Ngày tạo |

### FriendActivity

| Trường | Kiểu | Mô tả |
|--------|------|-------|
| `id` | UUIDField (PK) | Khóa chính UUID |
| `user` | FK → User | Người thực hiện hành động |
| `activity_type` | CharField | `playing` / `liked` / `added_to_playlist` |
| `song` | FK → Song null | Bài hát liên quan |
| `playlist` | FK → Playlist null | Playlist liên quan |
| `created_at` | DateTimeField auto | Thời điểm hoạt động |

> **Lưu ý:** `FriendActivity` cần có cleanup job định kỳ (xóa activity > 30 ngày) để tránh bảng phình. Xem mục 12.4.

## 8.2 API Endpoints

### Follow

| Method | Endpoint | Mô tả | Quyền |
|--------|----------|-------|-------|
| `GET` | `/api/social/me/following/` | Danh sách người tôi đang theo dõi | Auth |
| `GET` | `/api/social/me/followers/` | Danh sách người theo dõi tôi | Auth |
| `POST` | `/api/social/users/<id>/follow/` | Theo dõi user / nghệ sĩ (toggle) | Auth+CSRF |
| `DELETE` | `/api/social/me/followers/<id>/` | Xóa người theo dõi mình | Auth+CSRF |

### Tâm trạng (Mood)

| Method | Endpoint | Mô tả | Quyền |
|--------|----------|-------|-------|
| `GET` | `/api/social/me/mood/` | Xem tâm trạng hiện tại của tôi | Auth |
| `POST` | `/api/social/me/mood/` | Đặt tâm trạng mới | Auth+CSRF |
| `DELETE` | `/api/social/me/mood/` | Xóa tâm trạng hiện tại | Auth+CSRF |

### Hoạt động bạn bè

| Method | Endpoint | Mô tả | Quyền |
|--------|----------|-------|-------|
| `GET` | `/api/social/feed/` | Hoạt động gần đây của người đang theo dõi | Auth |

## 8.3 Request/Response Mẫu

### POST /api/social/me/mood/

```json
// Request Body
{ "mood_type": "happy", "status_text": "Nghe nhạc thôi!", "song_id": "uuid", "expires_at": "2025-12-31T23:59:00Z" }

// Response 200
{ "success": true, "data": { "mood_type": "happy", "status_text": "...", "song": {...} } }
```

### GET /api/social/feed/

```json
{
  "success": true,
  "data": {
    "items": [
      { "user": {...}, "activity_type": "liked", "song": {...}, "created_at": "..." },
      { "user": {...}, "activity_type": "added_to_playlist", "playlist": {...}, "song": {...}, "created_at": "..." }
    ],
    "pagination": { "page": 1, "page_size": 20, "total": 45, "total_pages": 3 }
  }
}
```

---

# 9. APP: notifications

Quản lý thông báo trong hệ thống. Thông báo được tạo tự động khi có sự kiện liên quan.

## 9.1 Models

### Notification

| Trường | Kiểu | Mô tả |
|--------|------|-------|
| `id` | UUIDField (PK) | Khóa chính UUID |
| `recipient` | FK → User | Người nhận thông báo |
| `sender` | FK → User null | Người gửi (null nếu là thông báo hệ thống) |
| `notif_type` | CharField | `follow` / `like` / `comment` / `reply` / `system` / `verify_result` |
| `target_type` | CharField null | `song` / `playlist` / `comment` / `user` |
| `target_id` | UUIDField null | ID đối tượng liên quan |
| `message` | TextField | Nội dung thông báo (đã render sẵn) |
| `is_read` | BooleanField default False | Đã đọc chưa |
| `created_at` | DateTimeField auto | Ngày tạo |

> ⚠️ **Bắt buộc truyền `target_type` và `target_id`** khi tạo notification *(Fix R11)*. Frontend dùng hai field này để điều hướng khi user bấm vào thông báo. Không được để null trừ loại `system` và `verify_result`.

### Các loại thông báo (notif_type)

| Loại | Khi nào tạo | `target_type` | Message mẫu |
|------|-------------|---------------|-------------|
| `follow` | Ai đó follow mình | `user` | `<user>` đã bắt đầu theo dõi bạn |
| `like` | Ai đó like bài hát của mình | `song` | `<user>` đã thích bài hát `<song>` |
| `comment` | Có bình luận mới trên bài hát của mình | `song` | `<user>` đã bình luận: `<preview>` |
| `reply` | Ai đó reply bình luận của mình | `comment` | `<user>` đã trả lời bình luận của bạn |
| `system` | Thông báo từ hệ thống / admin | null | Nội dung tùy |
| `verify_result` | Kết quả duyệt xác thực nghệ sĩ | null | Yêu cầu xác thực nghệ sĩ của bạn đã được duyệt |

## 9.2 API Endpoints

| Method | Endpoint | Mô tả | Quyền |
|--------|----------|-------|-------|
| `GET` | `/api/notifications/` | Danh sách thông báo của tôi (phân trang) | Auth |
| `GET` | `/api/notifications/unread-count/` | Số lượng thông báo chưa đọc | Auth |
| `POST` | `/api/notifications/<id>/read/` | Đánh dấu một thông báo đã đọc | Auth+CSRF |
| `POST` | `/api/notifications/read-all/` | Đánh dấu tất cả đã đọc | Auth+CSRF |
| `DELETE` | `/api/notifications/<id>/` | Xóa một thông báo | Auth+CSRF |

## 9.3 Response Mẫu

### GET /api/notifications/

```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": "uuid", "notif_type": "like",
        "sender": { "id": "...", "display_name": "Anna" },
        "target_type": "song", "target_id": "uuid-of-song",
        "message": "Anna đã thích bài hát Shape of You",
        "is_read": false, "created_at": "..."
      }
    ],
    "pagination": {...}
  }
}
```

---

# 10. APP: search

Xử lý tìm kiếm toàn hệ thống. App `search` không có models riêng — truy vấn **phải** đi qua `search/selectors.py`, không được import models trực tiếp trong `views.py`. *(Fix R7)*

## 10.1 API Endpoints

| Method | Endpoint | Mô tả | Quyền |
|--------|----------|-------|-------|
| `GET` | `/api/search/` | Tìm kiếm tổng hợp (songs + artists + playlists + users) | Public |
| `GET` | `/api/search/songs/` | Tìm kiếm bài hát (nhiều filter) | Public |
| `GET` | `/api/search/artists/` | Tìm kiếm nghệ sĩ theo tên nghệ danh | Public |
| `GET` | `/api/search/playlists/` | Tìm kiếm playlist công khai theo tên | Public |
| `GET` | `/api/search/users/` | Tìm kiếm người dùng (username / display_name) | Auth |

## 10.2 Query Params

### GET /api/search/ — Tìm kiếm tổng hợp

| Param | Bắt buộc | Mô tả |
|-------|----------|-------|
| `q` | Có | Từ khóa tìm kiếm (min 2 ký tự) |
| `limit` | Không | Số kết quả mỗi loại (default 5, max 10) |

### GET /api/search/songs/ — Tìm kiếm bài hát

| Param | Mô tả |
|-------|-------|
| `q` | Tên bài hát hoặc tên nghệ sĩ |
| `genre` | Slug thể loại |
| `artist_id` | UUID của nghệ sĩ |
| `ordering` | `play_count` / `-play_count` / `released_at` / `-released_at` / `title` |
| `page`, `page_size` | Phân trang |

## 10.3 Selectors bắt buộc *(Fix R7)*

```python
# search/selectors.py — Toàn bộ truy vấn phải nằm ở đây
from django.db.models import Q
from music.models import Song
from accounts.models import User
from artists.models import ArtistProfile
from playlists.models import Playlist
from accounts.models import BlockList


def search_songs(q, genre=None, artist_id=None, ordering='-play_count'):
    qs = Song.objects.filter(status=Song.STATUS_PUBLISHED).select_related('artist', 'genre')
    if q:
        qs = qs.filter(Q(title__icontains=q) | Q(artist__display_name__icontains=q))
    if genre:
        qs = qs.filter(genre__slug=genre)
    if artist_id:
        qs = qs.filter(artist_id=artist_id)
    return qs.order_by(ordering)


def search_users(q, requester=None):
    """Lọc user riêng tư — chỉ trả về public + user mà requester đang follow."""
    qs = User.objects.filter(
        Q(username__icontains=q) | Q(display_name__icontains=q),
        is_active=True,
    )
    if requester and requester.is_authenticated:
        following_ids = requester.following_set.values_list('following_id', flat=True)
        qs = qs.filter(Q(is_private=False) | Q(id__in=following_ids))
    else:
        qs = qs.filter(is_private=False)
    return qs


def search_artists(q):
    return ArtistProfile.objects.filter(
        stage_name__icontains=q, user__is_active=True
    ).select_related('user')


def search_playlists(q):
    return Playlist.objects.filter(
        title__icontains=q, is_public=True, owner__is_active=True
    ).select_related('owner')
```

## 10.4 Response Mẫu

### GET /api/search/?q=adele

```json
{
  "success": true,
  "data": {
    "songs": [ { "id": "...", "title": "Hello", "artist": { "stage_name": "Adele" }, "play_count": 500000 } ],
    "artists": [ { "id": "...", "stage_name": "Adele", "avatar": "url", "follower_count": 2000000 } ],
    "playlists": [],
    "users": []
  }
}
```

---

# 11. Sơ Đồ Quan Hệ (ERD)

| Quan hệ | Loại | Mô tả |
|---------|------|-------|
| User — ArtistProfile | 1-1 (OneToOne) | Mỗi user artist có đúng 1 profile |
| User — ArtistVerification | 1-N | User có thể nộp nhiều lần (khi bị rejected) |
| User — BlockList | N-N self | Người dùng chặn lẫn nhau |
| User — Follow | N-N self | Người dùng theo dõi nhau |
| User — Song | 1-N (artist FK) | Nghệ sĩ đăng nhiều bài hát |
| User — Like | N-N via Song | Người dùng like nhiều bài hát |
| User — Rating | N-N via Song | Người dùng đánh giá nhiều bài hát |
| User — Comment | 1-N via Song | Người dùng bình luận nhiều bài |
| User — CommentLike | N-N via Comment | Người dùng like nhiều bình luận |
| User — ListenHistory | 1-N via Song | Lịch sử nghe của người dùng |
| User — Playlist | 1-N | Người dùng tạo nhiều playlist |
| User — Mood | 1-N | Người dùng có nhiều mood (current = latest) |
| User — FriendActivity | 1-N | Hoạt động được log lại |
| User — Notification | 1-N | Người dùng nhận nhiều thông báo |
| User — Report | 1-N | Người dùng gửi nhiều báo cáo |
| Song — Genre | N-1 | Nhiều bài cùng 1 thể loại |
| Song — PlaylistSong | N-N via Playlist | Bài hát có thể ở nhiều playlist |
| Comment — Comment | Self-ref 1-N | Bình luận cha-con (reply) |

---

# 12. Quy Ước Chung & Triển Khai

## 12.1 Quy Ước Chung

| Quy ước | Chi tiết |
|---------|---------|
| Primary Key | Tất cả bảng dùng `UUIDField` làm PK |
| Soft Delete | `Song`, `Comment` dùng `is_hidden` / `status` thay vì xóa thật |
| Timestamps | Tất cả bảng có `created_at`; bảng hay thay đổi có thêm `updated_at` |
| Phân quyền | Kiểm tra role trong `services.py`, không trong `views.py` |
| Lỗi nghiệp vụ | Raise custom exception từ `exceptions.py`, views chỉ bắt và trả JSON |
| Validator | `validators.py` kiểm tra kiểu dữ liệu, bắt buộc, độ dài **TRƯỚC** khi gọi service |
| Tên hàm service | Dùng động từ hành động: `create_`, `update_`, `delete_`, `approve_`, ... |
| Tên hàm selector | Prefix cố định: `list_*`, `get_*`, `count_*`, `is_*`, `check_*`, `search_*` |
| File Upload | Audio/Image lưu vào cloud storage (S3 hoặc Cloudinary), **không lưu local trên production** |
| Pagination | Tất cả list API đều phân trang, default `page_size=20`, max=100 |
| Counter update | **Bắt buộc dùng `F()` expression** cho mọi increment/decrement counter *(Fix R1)* |
| Input sanitization | Strip HTML khỏi mọi trường text public trước khi lưu *(Fix R12)* |

## 12.2 Xử Lý Lỗi Trong Views

```python
@method_decorator([csrf_protect, require_auth], name='dispatch')
class SongCreateView(View):
    def post(self, request):
        try:
            data = json.loads(request.body or '{}')
            validated = validate_song_create(data, request.FILES)  # raise ValidationError
            song = create_song(artist=request.user, data=validated) # raise BusinessError
            return JsonResponse({'success': True, 'data': song_to_dict(song)}, status=201)
        except ValidationError as e:
            return JsonResponse({'success': False, 'error': {'code': 'VALIDATION_ERROR', 'fields': e.fields}}, status=400)
        except PermissionDenied as e:
            return JsonResponse({'success': False, 'error': {'code': 'PERMISSION_DENIED', 'message': e.message}}, status=403)
        except NotFound as e:
            return JsonResponse({'success': False, 'error': {'code': 'NOT_FOUND', 'message': e.message}}, status=404)
        except Exception:
            return JsonResponse({'success': False, 'error': {'code': 'SERVER_ERROR', 'message': 'Lỗi server'}}, status=500)
```

## 12.3 File Storage

| Loại file | Cấu hình | Path pattern |
|-----------|----------|-------------|
| Audio (.mp3, .flac) | S3 / Cloudinary | `audio/<artist_id>/<uuid>.<ext>` |
| Ảnh bìa bài hát | S3 / Cloudinary | `covers/songs/<uuid>.<ext>` |
| Avatar user | S3 / Cloudinary | `avatars/users/<uuid>.<ext>` |
| Avatar artist | S3 / Cloudinary | `avatars/artists/<uuid>.<ext>` |
| Ảnh bìa artist | S3 / Cloudinary | `covers/artists/<uuid>.<ext>` |
| Ảnh bìa playlist | S3 / Cloudinary | `covers/playlists/<uuid>.<ext>` |
| CMND/CCCD nghệ sĩ | **S3 private bucket** | `verifications/<uuid>.<ext>` |

> **Quan trọng:** File CMND/CCCD phải dùng **S3 private bucket** với presigned URL. Không bao giờ để public URL.

## 12.4 Cleanup Jobs (Định kỳ)

| Job | Tần suất | Mô tả | Management command |
|-----|----------|-------|-------------------|
| Xóa FriendActivity cũ | Hàng ngày | Xóa activity > 30 ngày để tránh bảng phình | `manage.py cleanup_friend_activities` |
| Xóa Mood hết hạn | Mỗi giờ | Xóa hoặc ẩn Mood đã qua `expires_at` | `manage.py cleanup_expired_moods` |
| Xóa Session hết hạn | Hàng ngày | Dọn session cũ khỏi DB | `manage.py clearsessions` (built-in) |
| Dọn file orphan | Hàng tuần | Xóa file trên cloud không còn record DB | `manage.py cleanup_orphan_files` |

```python
# social/management/commands/cleanup_friend_activities.py
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from social.models import FriendActivity

class Command(BaseCommand):
    help = 'Xóa FriendActivity cũ hơn 30 ngày'

    def handle(self, *args, **options):
        cutoff = timezone.now() - timedelta(days=30)
        deleted, _ = FriendActivity.objects.filter(created_at__lt=cutoff).delete()
        self.stdout.write(f'Đã xóa {deleted} FriendActivity records.')
```

## 12.5 Biến Môi Trường (.env)

```env
SECRET_KEY=your-django-secret-key-change-in-production
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com

# Database
DB_NAME=music_platform
DB_USER=postgres
DB_PASSWORD=strong-password-here
DB_HOST=localhost
DB_PORT=5432

# Session
SESSION_COOKIE_AGE=1209600
SESSION_COOKIE_SECURE=True

# CSRF
CSRF_COOKIE_SECURE=True
CSRF_TRUSTED_ORIGINS=https://yourdomain.com

# CORS — chỉ domain frontend, KHÔNG để trống hay *
CORS_ALLOWED_ORIGINS=https://yourdomain.com

# File storage
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_STORAGE_BUCKET_NAME=music-platform-prod
AWS_S3_REGION_NAME=ap-southeast-1
# CLOUDINARY_URL=...   # hoặc dùng Cloudinary thay S3

# Email
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=noreply@yourdomain.com
EMAIL_HOST_PASSWORD=...
DEFAULT_FROM_EMAIL=noreply@yourdomain.com
FRONTEND_URL=https://yourdomain.com
```

---

# 13. Bảo Mật & Xử Lý Rủi Ro

> Chương này ghi lại đầy đủ 16 rủi ro đã được phát hiện và hướng giải quyết cụ thể. Mỗi fix đã được tích hợp vào các chương tương ứng ở trên — chương này là tài liệu tham chiếu tập trung.

## 13.1 Bảng Tổng Hợp

| # | Mức độ | Vấn đề | Vị trí | Trạng thái |
|---|--------|--------|--------|------------|
| R1 | 🔴 Cao | Race condition trên `play_count` | `music/services.py` | Fix ở §5.3 |
| R2 | 🔴 Cao | Thiếu endpoint download nhạc | `music/views.py` | Fix ở §5.2, §5.3 |
| R3 | 🔴 Cao | CORS production không được định nghĩa | `settings.py` | Fix ở §2.2 |
| R4 | 🔴 Cao | File CMND/CCCD không validate type/size | `accounts/validators.py` | Fix ở §4.3 |
| R5 | 🔴 Cao | Audio file không check MIME type | `music/validators.py` | Fix ở §5.3 |
| R6 | 🟠 Trung bình | Không có Rate Limiting | Toàn bộ auth endpoints | Fix ở §13.2 |
| R7 | 🟠 Trung bình | `search/views.py` vi phạm phân tầng | `search/views.py` | Fix ở §10.3 |
| R8 | 🟠 Trung bình | `ListenHistory` không dedup | `music/services.py` | Fix ở §5.3 |
| R9 | 🟠 Trung bình | Thiếu endpoint publish bài hát | `music/views.py` | Fix ở §5.2 |
| R10 | 🟠 Trung bình | Block check không áp dụng khi xem content | Nhiều views | Fix ở §4.4 |
| R11 | 🟠 Trung bình | Notification thiếu `target_type`/`target_id` | `notifications/services.py` | Fix ở §9.1 |
| R12 | 🟠 Trung bình | Thiếu input sanitization (XSS) | `validators.py` các app | Fix ở §13.3 |
| R13 | 🟡 Thấp | Tài liệu ghi Django 4.x sai version | Tài liệu | Fixed (header tài liệu) |
| R14 | 🟡 Thấp | Cleanup jobs không có implementation | Nhiều app | Fix ở §12.4 |
| R15 | 🟡 Thấp | Không có API versioning | `urls.py` | Fix ở §13.4 |
| R16 | 🟡 Thấp | Search trả cả user `is_private=True` | `search/views.py` | Fix ở §10.3 |

---

## 13.2 Rate Limiting — Chống Brute Force *(Fix R6)*

Cài đặt `django-ratelimit`:

```bash
pip install django-ratelimit
```

Áp dụng vào auth views:

```python
# accounts/views.py
from ratelimit.decorators import ratelimit

class LoginView(View):
    @method_decorator(csrf_protect)
    @method_decorator(ratelimit(key='ip', rate='10/15m', method='POST', block=True))
    def post(self, request):
        ...

class RegisterView(View):
    @method_decorator(csrf_protect)
    @method_decorator(ratelimit(key='ip', rate='5/h', method='POST', block=True))
    def post(self, request):
        ...

class PasswordResetRequestView(View):
    @method_decorator(csrf_protect)
    # Rate limit theo email field để tránh lộ thông tin qua timing
    @method_decorator(ratelimit(key='post:email', rate='3/h', method='POST', block=True))
    def post(self, request):
        ...
```

Bảng giới hạn đầy đủ:

| Endpoint | Giới hạn | Key | HTTP khi vượt |
|----------|----------|-----|---------------|
| `POST /api/auth/login/` | 10 lần thất bại / 15 phút | IP | `429 + Retry-After` |
| `POST /api/auth/register/` | 5 lần / giờ | IP | `429` |
| `POST /api/auth/password/reset/request/` | 3 lần / giờ | email field | `429` (im lặng) |
| `POST .../play/` | 1 lần / bài / 5 phút / user | user+song | bỏ qua, không `429` |

Xử lý lỗi rate limit trả về chuẩn:

```python
# music_platform/settings.py
RATELIMIT_ENABLE = True

# Trong views — bắt lỗi RatelimitExceeded
from ratelimit.exceptions import Ratelimited

def handler429(request, exception):
    return JsonResponse(
        {'success': False, 'error': {'code': 'RATE_LIMITED', 'message': 'Quá nhiều yêu cầu, vui lòng thử lại sau'}},
        status=429,
    )
```

---

## 13.3 Input Sanitization — Chống XSS *(Fix R12)*

Cài đặt:

```bash
pip install bleach
```

Tạo helper dùng chung:

```python
# music_platform/sanitize.py
import bleach

def sanitize_text(value: str) -> str:
    """Strip toàn bộ HTML tags và attributes. Dùng cho mọi trường text public."""
    if not value:
        return ''
    return bleach.clean(value, tags=[], attributes={}, strip=True).strip()

def sanitize_url(value: str) -> str:
    """Chỉ cho phép http/https URL."""
    if not value:
        return ''
    if not value.startswith(('http://', 'https://')):
        raise ValueError('URL phải bắt đầu bằng http:// hoặc https://')
    return value.strip()
```

Áp dụng trong validators:

```python
# music/validators.py
from music_platform.sanitize import sanitize_text

def validate_song_create(data, files):
    ...
    return {
        ...
        'lyrics':      sanitize_text(data.get('lyrics', '')),
    }

# accounts/validators.py
def validate_update_profile(data):
    result = {}
    if 'display_name' in data:
        result['display_name'] = sanitize_text(data['display_name'])
    if 'bio' in data:
        result['bio'] = sanitize_text(data['bio'])
    return result

# social/validators.py
def validate_mood(data):
    return {
        'mood_type':   data.get('mood_type'),
        'status_text': sanitize_text(data.get('status_text', '')),
        ...
    }
```

---

## 13.4 API Versioning *(Fix R15)*

Thêm prefix `/v1/` vào `music_platform/urls.py` để hỗ trợ nâng cấp backward-compatible trong tương lai:

```python
# music_platform/urls.py
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/auth/',          include('accounts.auth_urls')),
    path('api/v1/accounts/',      include('accounts.urls')),
    path('api/v1/music/',         include('music.urls')),
    path('api/v1/playlists/',     include('playlists.urls')),
    path('api/v1/artists/',       include('artists.urls')),
    path('api/v1/social/',        include('social.urls')),
    path('api/v1/notifications/', include('notifications.urls')),
    path('api/v1/search/',        include('search.urls')),
]
```

> **Migration path:** Nếu muốn giữ backward compatibility, có thể alias `/api/` → `/api/v1/` trong giai đoạn chuyển tiếp bằng cách include cả hai.

---

## 13.5 Checklist Bảo Mật Production

Trước khi deploy, kiểm tra tất cả các mục sau:

```
✅ DEBUG = False
✅ SECRET_KEY mạnh (>= 50 ký tự random)
✅ ALLOWED_HOSTS chỉ chứa domain thật
✅ SESSION_COOKIE_SECURE = True
✅ CSRF_COOKIE_SECURE = True
✅ CORS_ALLOWED_ORIGINS chỉ chứa domain frontend
✅ CORS_ALLOW_ALL_ORIGINS không tồn tại hoặc = False
✅ File CMND/CCCD lưu S3 private bucket
✅ Toàn bộ audio/image lưu cloud, không local
✅ Rate limiting bật trên auth endpoints
✅ Django version >= 5.2 (security patches)
✅ pip install --upgrade django django-cors-headers django-ratelimit bleach
✅ manage.py check --deploy  ← chạy lệnh này và fix mọi warning
```

---

*— Hết tài liệu — Phiên bản 3.0*
