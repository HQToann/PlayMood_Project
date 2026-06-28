# 02 — Features & API Chi Tiết App `artists`

**6 endpoints | Session + CSRF Authentication | Phân quyền Role Artist + Owner**

---

## Mục Lục

1. [Artist Discovery](#1-artist-discovery)
2. [My Artist Profile](#2-my-artist-profile)
3. [Artist Cover Upload](#3-artist-cover-upload)
4. [Artist Stats](#4-artist-stats)
5. [Public Artist Detail](#5-public-artist-detail)
6. [Bảng tổng hợp tất cả endpoints](#6-bảng-tổng-hợp-tất-cả-endpoints)

---

## 1. Artist Discovery

### GET /api/v1/artists/ — Danh sách nghệ sĩ

| Thuộc tính | Giá trị |
|---|---|
| **Method** | `GET` |
| **Quyền** | `Public` |
| **Query params** | `q` (tìm theo stage_name/username), `page`, `page_size` (max 100) |

**Luồng logic:**
```
ArtistListView.get
  -> validate_list_artists_params(request.GET)     [validators.py]
  -> list_artists(filters, viewer=request.user)      [selectors.py]
     -> an nghe si da block viewer (Fix R10)
  -> tra JSON
```

**Response 200:**
```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": "uuid",
        "user": { "id": "uuid", "username": "edsheeran", "avatar": null },
        "stage_name": "Ed Sheeran",
        "display_name": "Ed Sheeran",
        "bio": "Singer-songwriter tu UK",
        "cover_image": "https://res.cloudinary.com/.../covers/artists/uuid.jpg",
        "website_url": "https://edsheeran.com",
        "facebook_url": "",
        "youtube_url": "",
        "is_owner": false,
        "created_at": "2026-06-20T08:00:00+07:00",
        "updated_at": "2026-06-20T08:00:00+07:00"
      }
    ],
    "pagination": { "page": 1, "page_size": 20, "total": 1, "total_pages": 1 }
  }
}
```

---

## 2. My Artist Profile

### GET /api/v1/artists/me/ — Xem hồ sơ của chính mình (tự tạo nếu chưa có)

| Thuộc tính | Giá trị |
|---|---|
| **Method** | `GET` |
| **Quyền** | `Artist` (role='artist') |

**Luồng logic:**
```
MyArtistProfileView.get
  -> get_or_create_my_profile(request.user)     [services.py]
     -> neu request.user.role != 'artist': raise UserNotArtist (403)
     -> neu chua co profile: tu dong tao moi rong
     -> neu da co: tra ve profile hien co
  -> tra JSON
```

> **Quan trọng:** Endpoint này KHÔNG bắt artist phải gọi `POST` trước. Lần đầu gọi `GET /me/`, hệ thống tự tạo `ArtistProfile` rỗng.

**Response 200:**
```json
{
  "success": true,
  "data": {
    "id": "uuid", "user": { "id": "uuid", "username": "myartist", "avatar": null },
    "stage_name": "", "display_name": "myartist", "bio": "",
    "cover_image": null, "website_url": "", "facebook_url": "", "youtube_url": "",
    "is_owner": true, "created_at": "...", "updated_at": "..."
  }
}
```

**Response 403** (user không phải artist):
```json
{ "success": false, "error": { "code": "ARTIST_ONLY", "message": "Chi nghe si moi duoc thuc hien hanh dong nay" } }
```

---

### POST /api/v1/artists/me/ — Tạo hồ sơ nghệ sĩ

| Thuộc tính | Giá trị |
|---|---|
| **Method** | `POST` |
| **Quyền** | `Artist+CSRF` |
| **Request Body** | JSON |

**Request Body:**
```json
{
  "stage_name": "DJ Coolio",
  "bio": "Nghe si dien tu tu Ha Noi",
  "website_url": "https://djcoolio.com",
  "facebook_url": "https://facebook.com/djcoolio",
  "youtube_url": ""
}
```

| Field | Kiểu | Bắt buộc | Ràng buộc |
|-------|------|----------|-----------|
| `stage_name` | string | Không | max 100 ký tự, sanitized XSS |
| `bio` | string | Không | max 1000 ký tự, sanitized XSS |
| `website_url` | string | Không | phải bắt đầu http://  https:// |
| `facebook_url` | string | Không | phải bắt đầu http://  https:// |
| `youtube_url` | string | Không | phải bắt đầu http://  https:// |

**Luồng logic:**
```
MyArtistProfileView.post
  -> parse_json_body(request)
  -> validate_artist_profile_create(data)        [validators.py - sanitize + check URL]
  -> create_artist_profile(request.user, validated)  [services.py]
     -> check role='artist' -> raise UserNotArtist neu khong (403)
     -> check da co profile chua -> raise ArtistProfileAlreadyExists neu co (409)
  -> tra JSON 201
```

**Response 201:** (giống cấu trúc GET ở trên với data đã điền)

**Response 409** (đã có hồ sơ):
```json
{ "success": false, "error": { "code": "ALREADY_EXISTS", "message": "Ho so nghe si da ton tai" } }
```

---

### PATCH /api/v1/artists/me/ — Cập nhật hồ sơ

| Thuộc tính | Giá trị |
|---|---|
| **Method** | `PATCH` |
| **Quyền** | `Artist+Owner+CSRF` |
| **Request Body** | JSON, partial update |

**Request Body:**
```json
{ "stage_name": "DJ Coolio Updated", "bio": "Mo ta moi" }
```

**Luồng logic:**
```
MyArtistProfileView.patch
  -> get_artist_profile_by_user_id(request.user.id)   [selectors.py]
  -> validate_artist_profile_update(data)              [validators.py]
  -> update_artist_profile(profile, request.user, validated)  [services.py]
     -> check owner -> raise NotArtistProfileOwner neu khong phai (403)
  -> tra JSON
```

**Response 200:** trả hồ sơ đã cập nhật.

**Response 400** (không có dữ liệu):
```json
{ "success": false, "error": { "code": "VALIDATION_ERROR", "message": "Khong co du lieu de cap nhat" } }
```

---

## 3. Artist Cover Upload

### POST /api/v1/artists/me/cover/ — Upload ảnh bìa

| Thuộc tính | Giá trị |
|---|---|
| **Method** | `POST` |
| **Quyền** | `Artist+Owner+CSRF` |
| **Request Body** | `multipart/form-data` |

| Field | Kiểu | Bắt buộc | Ràng buộc |
|-------|------|----------|-----------|
| `cover_image` | file | Co | JPG/PNG/WEBP, max 5MB |

**Luồng logic:**
```
ArtistCoverUploadView.post
  -> validate_cover_image(request.FILES)          [validators.py - check MIME + size]
  -> get_artist_profile_by_user_id(request.user.id)  [selectors.py]
     -> raise ArtistProfileNotFound neu chua tao profile (404)
  -> update_cover_image(profile, request.user, file)  [services.py]
     -> xoa anh bia cu tren Cloudinary neu co (tranh file mo coi)
     -> check owner -> raise NotArtistProfileOwner neu khong phai (403)
  -> tra JSON
```

**Response 200:**
```json
{ "success": true, "data": { "cover_image": "https://res.cloudinary.com/.../covers/artists/uuid.jpg" } }
```

**Response 404** (chưa tạo hồ sơ — phải gọi `GET /me/` hoặc `POST /me/` trước):
```json
{ "success": false, "error": { "code": "NOT_FOUND", "message": "Ho so nghe si khong ton tai" } }
```

---

## 4. Artist Stats

### GET /api/v1/artists/me/stats/ — Thống kê của chính mình

| Thuộc tính | Giá trị |
|---|---|
| **Method** | `GET` |
| **Quyền** | `Artist` |

**Luồng logic:**
```
MyArtistStatsView.get
  -> get_artist_stats(request.user.id)        [selectors.py - tinh tu nhieu bang music]
  -> list_artist_top_songs(request.user.id, limit=10)  [selectors.py]
  -> tra JSON gop ca 2 ket qua
```

**Response 200:**
```json
{
  "success": true,
  "data": {
    "total_songs": 12,
    "total_play_count": 45200,
    "total_likes": 890,
    "total_comments": 234,
    "total_listeners": 3100,
    "avg_rating": 4.3,
    "rating_count": 567,
    "top_songs": [
      { "id": "uuid", "title": "Shape of You", "play_count": 15420, "like_count": 320, "cover_image": "https://..." }
    ]
  }
}
```

> Xem chi tiết cách tính từng chỉ số ở Mục 6 của `01_artists_overview.md` và source code `selectors.py::get_artist_stats()`.

---

### GET /api/v1/artists/\<user_id\>/stats/ — Thống kê công khai của một nghệ sĩ

| Thuộc tính | Giá trị |
|---|---|
| **Method** | `GET` |
| **Quyền** | `Public` |

**Luồng logic:**
```
ArtistStatsView.get
  -> get_artist_profile_detail(user_id, viewer=request.user)  [selectors.py]
     -> raise ArtistProfileNotFound neu khong ton tai hoac viewer bi block (Fix R10)
  -> get_artist_stats(user_id)
  -> list_artist_top_songs(user_id, limit=10)
  -> tra JSON
```

**Response 200:** giống cấu trúc ở trên (không phân biệt owner/người khác — số liệu công khai).

**Response 404** (nghệ sĩ không tồn tại hoặc bạn bị block):
```json
{ "success": false, "error": { "code": "NOT_FOUND", "message": "Ho so nghe si khong ton tai" } }
```

---

## 5. Public Artist Detail

### GET /api/v1/artists/\<user_id\>/ — Xem hồ sơ nghệ sĩ công khai

| Thuộc tính | Giá trị |
|---|---|
| **Method** | `GET` |
| **Quyền** | `Public` |

**Luồng logic:**
```
ArtistDetailView.get
  -> get_artist_profile_detail(user_id, viewer=request.user)  [selectors.py]
     -> raise ArtistProfileNotFound neu khong ton tai
     -> raise ArtistProfileNotFound neu viewer bi nghe si block (Fix R10)
  -> tra JSON
```

**Response 200:**
```json
{
  "success": true,
  "data": {
    "id": "uuid", "user": { "id": "uuid", "username": "edsheeran", "avatar": null },
    "stage_name": "Ed Sheeran", "display_name": "Ed Sheeran",
    "bio": "...", "cover_image": "https://...",
    "website_url": "https://edsheeran.com", "facebook_url": "", "youtube_url": "",
    "is_owner": false, "created_at": "...", "updated_at": "..."
  }
}
```

**Response 404** (không tồn tại hoặc bị block):
```json
{ "success": false, "error": { "code": "NOT_FOUND", "message": "Ho so nghe si khong ton tai" } }
```

---

## 6. Bảng Tổng Hợp Tất Cả Endpoints

| # | Method | Endpoint | Quyền |
|---|--------|----------|-------|
| 1 | GET | `/api/v1/artists/` | Public |
| 2 | GET | `/api/v1/artists/me/` | Artist (tự tạo nếu chưa có) |
| 3 | POST | `/api/v1/artists/me/` | Artist+CSRF |
| 4 | PATCH | `/api/v1/artists/me/` | Artist+Owner+CSRF |
| 5 | POST | `/api/v1/artists/me/cover/` | Artist+Owner+CSRF |
| 6 | GET | `/api/v1/artists/me/stats/` | Artist |
| 7 | GET | `/api/v1/artists/<user_id>/` | Public |
| 8 | GET | `/api/v1/artists/<user_id>/stats/` | Public |
