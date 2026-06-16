# WEEK 2 — Hướng Dẫn Test API Trên Postman

**App `music` — 30 endpoints | Session + CSRF Authentication**

---

## Mục Lục

1. [Thiết lập Postman trước khi test](#1-thiết-lập-postman-trước-khi-test)
2. [Quy trình xác thực bắt buộc](#2-quy-trình-xác-thực-bắt-buộc)
3. [Genre — Thể loại nhạc](#3-genre--thể-loại-nhạc)
4. [Song — Bài hát](#4-song--bài-hát)
5. [Play & Download](#5-play--download)
6. [Like — Yêu thích](#6-like--yêu-thích)
7. [Rating — Đánh giá](#7-rating--đánh-giá)
8. [Comment — Bình luận](#8-comment--bình-luận)
9. [ListenHistory — Lịch sử nghe](#9-listenhistory--lịch-sử-nghe)
10. [Report — Báo cáo vi phạm](#10-report--báo-cáo-vi-phạm)
11. [Admin Endpoints](#11-admin-endpoints)
12. [Test Scenarios — Luồng test kết hợp](#12-test-scenarios--luồng-test-kết-hợp)
13. [Bảng tổng hợp tất cả endpoints](#13-bảng-tổng-hợp-tất-cả-endpoints)

---

## 1. Thiết Lập Postman Trước Khi Test

### 1.1 Tạo Environment

Vào **Environments** → **New** → đặt tên `Music Platform - Dev`

Thêm các variables sau:

| Variable | Initial Value | Mô tả |
|----------|--------------|-------|
| `base_url` | `http://localhost:8000` | URL server |
| `csrftoken` | *(để trống)* | Tự cập nhật sau khi gọi /csrf/ |
| `sessionid` | *(để trống)* | Tự cập nhật sau khi login |
| `artist_session` | *(để trống)* | Session của tài khoản artist |
| `admin_session` | *(để trống)* | Session của tài khoản admin |
| `song_id` | *(để trống)* | ID bài hát vừa tạo |
| `genre_id` | *(để trống)* | ID thể loại vừa tạo |
| `comment_id` | *(để trống)* | ID bình luận vừa tạo |
| `report_id` | *(để trống)* | ID báo cáo vừa tạo |

### 1.2 Cấu hình Cookie

Vào **Settings** (icon bánh răng) → **General**:
- ✅ **Automatically follow redirects**: ON
- ✅ **Send cookies**: ON (quan trọng nhất)
- ✅ **Store cookies in cookie jar**: ON

### 1.3 Collection-level Pre-request Script

Tạo **Collection** mới → vào tab **Pre-request Script** → paste:

```javascript
// Tự động đọc csrftoken từ cookie jar và set vào environment
const cookieJar = pm.cookies.jar();
cookieJar.get(pm.environment.get('base_url'), 'csrftoken', (err, value) => {
    if (value) {
        pm.environment.set('csrftoken', value);
    }
});
```

### 1.4 Header mặc định cho mọi request

Trong Collection → **Authorization** → **No Auth**

Với mọi request **POST / PATCH / PUT / DELETE**, thêm header:
```
X-CSRFToken: {{csrftoken}}
```

---

## 2. Quy Trình Xác Thực Bắt Buộc

> ⚠️ **Phải thực hiện đúng thứ tự này trước khi test bất kỳ API nào cần auth.**

### Bước 1 — Lấy CSRF Token

```
Method:  GET
URL:     {{base_url}}/api/v1/auth/csrf/
Headers: (không cần)
Body:    (không có)
```

**Response mong đợi (200):**
```json
{
    "success": true,
    "detail": "CSRF cookie set"
}
```

✅ Sau bước này: cookie `csrftoken` xuất hiện trong Postman **Cookies** tab.
Copy giá trị đó vào Environment variable `csrftoken`.

---

### Bước 2 — Đăng nhập tài khoản thường (User)

```
Method:  POST
URL:     {{base_url}}/api/v1/auth/login/
Headers:
    Content-Type: application/json
    X-CSRFToken:  {{csrftoken}}
Body (raw JSON):
```
```json
{
    "email": "user@example.com",
    "password": "Test1234"
}
```

**Response mong đợi (200):**
```json
{
    "success": true,
    "data": {
        "id": "uuid...",
        "username": "normaluser",
        "role": "user",
        "email": "user@example.com"
    }
}
```

✅ Sau bước này: cookie `sessionid` được set tự động.

---

### Bước 3 — Đăng nhập tài khoản Artist (để upload nhạc)

> Mở **tab mới** trong Postman hoặc dùng User riêng có `role=artist`.

```
Method:  POST
URL:     {{base_url}}/api/v1/auth/login/
Headers:
    Content-Type: application/json
    X-CSRFToken:  {{csrftoken}}
Body (raw JSON):
```
```json
{
    "email": "artist@example.com",
    "password": "Artist1234"
}
```

> **Tạo tài khoản artist nếu chưa có:**
> ```bash
> python manage.py shell -c "
> from accounts.models import User
> u = User.objects.create_user(
>     username='testartist',
>     email='artist@example.com',
>     password='Artist1234',
>     role='artist'
> )
> print('Created:', u.username, u.role)
> "
> ```

---

### Bước 4 — Đăng nhập tài khoản Admin

```json
{
    "email": "admin@example.com",
    "password": "Admin1234"
}
```

> **Nâng role lên admin nếu chưa:**
> ```bash
> python manage.py shell -c "
> from accounts.models import User
> User.objects.filter(email='admin@example.com').update(role='admin')
> "
> ```

---

## 3. Genre — Thể Loại Nhạc

### ① GET /api/v1/music/genres/ — Danh sách thể loại

```
Method:  GET
URL:     {{base_url}}/api/v1/music/genres/
Headers: (không cần auth)
Body:    (không có)
```

**Response mong đợi (200):**
```json
{
    "success": true,
    "data": {
        "items": [],
        "total": 0
    }
}
```

> Lần đầu chạy sẽ trả list rỗng. Tạo genre ở bước tiếp theo.

---

### ② POST /api/v1/music/genres/ — Tạo thể loại (Admin)

> ⚠️ Phải đăng nhập bằng tài khoản **admin** trước.

```
Method:  POST
URL:     {{base_url}}/api/v1/music/genres/
Headers:
    Content-Type: application/json
    X-CSRFToken:  {{csrftoken}}
Body (raw JSON):
```
```json
{
    "name": "Pop",
    "description": "Nhạc Pop quốc tế và Việt Nam"
}
```

**Response mong đợi (201):**
```json
{
    "success": true,
    "data": {
        "id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
        "name": "Pop",
        "slug": "pop",
        "description": "Nhạc Pop quốc tế và Việt Nam",
        "created_at": "2026-06-11T08:00:00+07:00"
    }
}
```

✅ Copy giá trị `id` → paste vào Environment variable `genre_id`.

**Tạo thêm vài thể loại để test filter:**
```json
{ "name": "V-Pop", "description": "Nhạc Pop Việt Nam" }
{ "name": "Rock", "description": "Nhạc Rock" }
{ "name": "Ballad", "description": "Nhạc Ballad" }
```

**Test lỗi — tên đã tồn tại (409):**
```json
{ "name": "Pop", "description": "Thử tạo trùng" }
```

Response mong đợi:
```json
{
    "success": false,
    "error": {
        "code": "ALREADY_EXISTS",
        "message": "Thể loại đã tồn tại"
    }
}
```

**Test lỗi — không phải admin (403):**
> Đăng nhập bằng tài khoản user thường, gọi lại endpoint này.

```json
{
    "success": false,
    "error": {
        "code": "ADMIN_ONLY",
        "message": "Chỉ quản trị viên mới được thực hiện hành động này"
    }
}
```

---

### ③ PUT /api/v1/music/genres/<id>/ — Cập nhật thể loại (Admin)

```
Method:  PUT
URL:     {{base_url}}/api/v1/music/genres/{{genre_id}}/
Headers:
    Content-Type: application/json
    X-CSRFToken:  {{csrftoken}}
Body (raw JSON):
```
```json
{
    "name": "Pop & Dance",
    "description": "Nhạc Pop và Dance"
}
```

**Response mong đợi (200):**
```json
{
    "success": true,
    "data": {
        "id": "{{genre_id}}",
        "name": "Pop & Dance",
        "slug": "pop-dance",
        "description": "Nhạc Pop và Dance"
    }
}
```

---

### ④ DELETE /api/v1/music/genres/<id>/ — Xóa thể loại (Admin)

> ⚠️ Chỉ xóa được khi genre KHÔNG có bài hát. Tạo genre mới để test xóa.

```
Method:  DELETE
URL:     {{base_url}}/api/v1/music/genres/{{genre_id}}/
Headers:
    X-CSRFToken: {{csrftoken}}
Body:    (không có)
```

**Response mong đợi (204):** Không có body.

**Test lỗi — genre có bài hát (400):**
```json
{
    "success": false,
    "error": {
        "code": "GENRE_HAS_SONGS",
        "message": "Không thể xóa thể loại đang có bài hát"
    }
}
```

---

## 4. Song — Bài Hát

### ⑤ POST /api/v1/music/songs/ — Upload bài hát (Artist)

> ⚠️ Phải đăng nhập bằng tài khoản **artist**. Dùng `multipart/form-data` (KHÔNG phải JSON).

```
Method:  POST
URL:     {{base_url}}/api/v1/music/songs/
Headers:
    X-CSRFToken: {{csrftoken}}
    (KHÔNG set Content-Type — Postman tự set multipart/form-data)
Body: form-data
```

| Key | Type | Value |
|-----|------|-------|
| `title` | Text | `Shape of You` |
| `genre_id` | Text | `{{genre_id}}` |
| `duration` | Text | `234` |
| `lyrics` | Text | `The club isn't the best place to find a lover...` |
| `allow_download` | Text | `false` |
| `audio_file` | File | [Chọn file .mp3 hoặc .flac từ máy] |
| `cover_image` | File | [Chọn file .jpg hoặc .png từ máy] |

**Response mong đợi (201):**
```json
{
    "success": true,
    "data": {
        "id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
        "title": "Shape of You",
        "status": "draft",
        "audio_file": "http://res.cloudinary.com/.../audio/uuid.mp3",
        "cover_image": "http://res.cloudinary.com/.../covers/uuid.jpg",
        "artist": {
            "id": "uuid",
            "username": "testartist",
            "display_name": "testartist"
        },
        "genre": { "id": "uuid", "name": "Pop", "slug": "pop" },
        "duration": 234,
        "play_count": 0,
        "allow_download": false,
        "released_at": null,
        "created_at": "2026-06-11T08:00:00+07:00"
    }
}
```

✅ Copy `id` → paste vào Environment variable `song_id`.

**Test lỗi — MIME type sai (400):**
Upload file `.txt` thay vì audio:
```json
{
    "success": false,
    "error": {
        "code": "VALIDATION_ERROR",
        "message": "Dữ liệu bài hát không hợp lệ",
        "fields": {
            "audio_file": ["Chỉ chấp nhận: audio/flac, audio/mpeg, audio/mp4, audio/ogg, audio/wav, audio/x-flac"]
        }
    }
}
```

**Test lỗi — thiếu audio_file (400):**
```json
{
    "success": false,
    "error": {
        "code": "VALIDATION_ERROR",
        "fields": { "audio_file": ["File audio là bắt buộc"] }
    }
}
```

**Test lỗi — không phải artist (403):**
> Đăng nhập bằng user thường và gọi lại:
```json
{
    "success": false,
    "error": { "code": "ARTIST_ONLY" }
}
```

---

### ⑥ GET /api/v1/music/songs/ — Danh sách bài hát

```
Method:  GET
URL:     {{base_url}}/api/v1/music/songs/
Headers: (không cần auth)
Body:    (không có)
```

**Response mong đợi (200):**
```json
{
    "success": true,
    "data": {
        "items": [],
        "pagination": {
            "page": 1,
            "page_size": 20,
            "total": 0,
            "total_pages": 1
        }
    }
}
```

> Bài hát vừa tạo có `status=draft` nên **không hiện** ở đây khi xem bằng anonymous.
> Sau khi publish (bước ⑨) sẽ hiện ra.

**Test với query params:**
```
URL: {{base_url}}/api/v1/music/songs/?q=Shape&genre=pop&ordering=-play_count&page=1&page_size=10
```

**Test filter theo artist:**
```
URL: {{base_url}}/api/v1/music/songs/?artist_id={{artist_uuid}}
```

---

### ⑦ GET /api/v1/music/songs/trending/ — Bài hát trending

```
Method:  GET
URL:     {{base_url}}/api/v1/music/songs/trending/
Headers: (không cần auth)
```

**Response mong đợi (200):**
```json
{
    "success": true,
    "data": {
        "items": [],
        "total": 0
    }
}
```

> Sẽ có dữ liệu sau khi Admin bật trending ở bước ㉔.

---

### ⑧ GET /api/v1/music/songs/<id>/ — Chi tiết bài hát

> Bài đang ở `status=draft` → chỉ owner (artist đã login) mới xem được.

```
Method:  GET
URL:     {{base_url}}/api/v1/music/songs/{{song_id}}/
Headers: (đang login bằng artist)
```

**Response mong đợi (200):**
```json
{
    "success": true,
    "data": {
        "id": "{{song_id}}",
        "title": "Shape of You",
        "status": "draft",
        "play_count": 0,
        "like_count": 0,
        "avg_rating": null,
        "rating_count": 0,
        "is_liked": false,
        "my_rating": null
    }
}
```

**Test lỗi — xem draft bằng user khác (404):**
> Đăng nhập bằng user thường → gọi endpoint này → phải trả 404.

---

### ⑨ POST /api/v1/music/songs/<id>/publish/ — Phát hành bài hát

> Phải đăng nhập bằng **artist owner**.

```
Method:  POST
URL:     {{base_url}}/api/v1/music/songs/{{song_id}}/publish/
Headers:
    X-CSRFToken: {{csrftoken}}
Body:    (không có)
```

**Response mong đợi (200):**
```json
{
    "success": true,
    "data": {
        "id": "{{song_id}}",
        "status": "published",
        "released_at": "2026-06-11T08:30:00+07:00"
    }
}
```

✅ Sau bước này, bài hát xuất hiện trong `GET /api/v1/music/songs/`.

**Test lỗi — publish lần 2 (400):**
```json
{
    "success": false,
    "error": {
        "code": "ALREADY_PUBLISHED",
        "message": "Bài hát đã được phát hành"
    }
}
```

**Test lỗi — không phải owner (403):**
> Đăng nhập bằng artist khác → gọi publish → phải trả 403.

---

### ⑩ PATCH /api/v1/music/songs/<id>/ — Cập nhật bài hát

> Đăng nhập bằng **artist owner**. Dùng `form-data` nếu có file, JSON nếu chỉ update text.

**Chỉ update text (JSON):**
```
Method:  PATCH
URL:     {{base_url}}/api/v1/music/songs/{{song_id}}/
Headers:
    Content-Type: application/json
    X-CSRFToken:  {{csrftoken}}
Body (raw JSON):
```
```json
{
    "title": "Shape of You (Remastered)",
    "allow_download": true,
    "lyrics": "Updated lyrics here..."
}
```

**Update kèm ảnh bìa mới (form-data):**
```
Method:  PATCH
URL:     {{base_url}}/api/v1/music/songs/{{song_id}}/
Headers:
    X-CSRFToken: {{csrftoken}}
Body: form-data
    title:        Shape of You (Remastered)
    cover_image:  [Chọn file ảnh mới]
```

**Response mong đợi (200):**
```json
{
    "success": true,
    "data": {
        "id": "{{song_id}}",
        "title": "Shape of You (Remastered)",
        "allow_download": true
    }
}
```

---

### ⑪ POST /api/v1/music/songs/<id>/hide/ — Ẩn bài hát

```
Method:  POST
URL:     {{base_url}}/api/v1/music/songs/{{song_id}}/hide/
Headers:
    X-CSRFToken: {{csrftoken}}
Body:    (không có)
```

**Response mong đợi (200):**
```json
{
    "success": true,
    "data": { "id": "{{song_id}}", "status": "hidden" }
}
```

> Sau khi ẩn, `GET /songs/{{song_id}}/` trả **404** cho tất cả mọi người.
> Để test tiếp, publish lại bằng cách tạo bài hát mới hoặc dùng Django Admin đổi status.

---

### ⑫ DELETE /api/v1/music/songs/<id>/ — Xóa bài hát

> ⚠️ Xóa vĩnh viễn cả record lẫn file Cloudinary. Nên tạo bài test riêng để xóa.

```
Method:  DELETE
URL:     {{base_url}}/api/v1/music/songs/{{song_id}}/
Headers:
    X-CSRFToken: {{csrftoken}}
Body:    (không có)
```

**Response mong đợi (204):** Không có body.

---

## 5. Play & Download

### ⑬ POST /api/v1/music/songs/<id>/play/ — Ghi lượt nghe

> Phải đăng nhập. Bài hát phải ở trạng thái **published**.

```
Method:  POST
URL:     {{base_url}}/api/v1/music/songs/{{song_id}}/play/
Headers:
    X-CSRFToken: {{csrftoken}}
Body:    (không có)
```

**Response mong đợi (200):**
```json
{
    "success": true,
    "data": { "play_count": 1 }
}
```

**Test dedup 5 phút (Fix R8):**
Gọi lại ngay lập tức → `play_count` **KHÔNG tăng** (vẫn là 1):
```json
{
    "success": true,
    "data": { "play_count": 1 }
}
```

> Đây là behavior đúng — tránh spam counter. Chờ 5 phút hoặc xóa record trong DB để test tăng tiếp.

**Kiểm tra play_count tăng atomic:**
Gọi đồng thời nhiều request bằng Postman Runner → `play_count` phải tăng đúng số lần (không bị race condition nhờ `F()` expression).

---

### ⑭ GET /api/v1/music/songs/<id>/download/ — Tải nhạc

> Bài hát phải `status=published` VÀ `allow_download=true`.
> Cập nhật `allow_download=true` trước (bước ⑩), sau đó gọi:

```
Method:  GET
URL:     {{base_url}}/api/v1/music/songs/{{song_id}}/download/
Headers: (đang đăng nhập)
Body:    (không có)
```

**Response mong đợi (200):**
```json
{
    "success": true,
    "data": {
        "download_url": "https://res.cloudinary.com/...",
        "filename": "Shape-of-You-Remastered.mp3",
        "expires_in": 300
    }
}
```

**Test lỗi — allow_download=false (403):**
Đặt `allow_download=false` rồi gọi:
```json
{
    "success": false,
    "error": {
        "code": "DOWNLOAD_NOT_ALLOWED",
        "message": "Bài hát này không cho phép tải về"
    }
}
```

**Test lỗi — chưa đăng nhập (401):**
Logout rồi gọi:
```json
{
    "success": false,
    "error": { "code": "AUTH_REQUIRED" }
}
```

---

## 6. Like — Yêu Thích

### ⑮ POST /api/v1/music/songs/<id>/like/ — Toggle Like

> Phải đăng nhập.

```
Method:  POST
URL:     {{base_url}}/api/v1/music/songs/{{song_id}}/like/
Headers:
    X-CSRFToken: {{csrftoken}}
Body:    (không có)
```

**Response lần 1 — Like (200):**
```json
{
    "success": true,
    "data": {
        "action": "liked",
        "like_count": 1
    }
}
```

**Response lần 2 — Unlike (200):**
```json
{
    "success": true,
    "data": {
        "action": "unliked",
        "like_count": 0
    }
}
```

---

### ⑯ GET /api/v1/music/songs/<id>/likes/ — Xem số lượt thích

```
Method:  GET
URL:     {{base_url}}/api/v1/music/songs/{{song_id}}/likes/
Headers: (không cần auth — nhưng nếu đăng nhập sẽ có thêm is_liked)
```

**Response (200):**
```json
{
    "success": true,
    "data": {
        "like_count": 1,
        "is_liked": true
    }
}
```

---

## 7. Rating — Đánh Giá

### ⑰ POST /api/v1/music/songs/<id>/rate/ — Đánh giá bài hát

> Phải đăng nhập. Gọi nhiều lần sẽ **upsert** (cập nhật rating cũ).

```
Method:  POST
URL:     {{base_url}}/api/v1/music/songs/{{song_id}}/rate/
Headers:
    Content-Type: application/json
    X-CSRFToken:  {{csrftoken}}
Body (raw JSON):
```
```json
{ "score": 5 }
```

**Response (200):**
```json
{
    "success": true,
    "data": {
        "score": 5,
        "avg_rating": 5.0,
        "rating_count": 1
    }
}
```

**Test upsert — đánh giá lại:**
```json
{ "score": 3 }
```
Response:
```json
{
    "success": true,
    "data": {
        "score": 3,
        "avg_rating": 3.0,
        "rating_count": 1
    }
}
```

**Test lỗi — score ngoài 1–5 (400):**
```json
{ "score": 6 }
```
```json
{
    "success": false,
    "error": {
        "code": "VALIDATION_ERROR",
        "fields": { "score": ["Điểm phải từ 1 đến 5"] }
    }
}
```

---

### ⑱ GET /api/v1/music/songs/<id>/rating/ — Xem điểm đánh giá

```
Method:  GET
URL:     {{base_url}}/api/v1/music/songs/{{song_id}}/rating/
Headers: (đăng nhập để có my_rating)
```

**Response (200):**
```json
{
    "success": true,
    "data": {
        "avg_rating": 4.0,
        "rating_count": 2,
        "my_rating": 3
    }
}
```

---

## 8. Comment — Bình Luận

### ⑲ POST /api/v1/music/songs/<id>/comments/ — Thêm bình luận

> Phải đăng nhập.

```
Method:  POST
URL:     {{base_url}}/api/v1/music/songs/{{song_id}}/comments/
Headers:
    Content-Type: application/json
    X-CSRFToken:  {{csrftoken}}
Body (raw JSON):
```
```json
{
    "content": "Bài hát hay quá, nghe mãi không chán!",
    "parent_id": null
}
```

**Response mong đợi (201):**
```json
{
    "success": true,
    "data": {
        "id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
        "user": {
            "id": "uuid",
            "username": "normaluser",
            "display_name": "normaluser",
            "avatar": null
        },
        "content": "Bài hát hay quá, nghe mãi không chán!",
        "like_count": 0,
        "is_liked": false,
        "parent_id": null,
        "created_at": "2026-06-11T09:00:00+07:00"
    }
}
```

✅ Copy `id` → paste vào Environment variable `comment_id`.

**Test XSS sanitize (Fix R12):**
```json
{
    "content": "<script>alert('xss')</script>Bài này hay!",
    "parent_id": null
}
```
Response — `content` đã bị strip script tag:
```json
{
    "success": true,
    "data": {
        "content": "Bài này hay!"
    }
}
```

**Test lỗi — nội dung rỗng (400):**
```json
{ "content": "", "parent_id": null }
```
```json
{
    "success": false,
    "error": {
        "code": "VALIDATION_ERROR",
        "fields": { "content": ["Nội dung bình luận là bắt buộc"] }
    }
}
```

---

### ⑳ POST — Trả lời bình luận (Reply)

> Dùng `parent_id` là ID của comment gốc vừa tạo.

```
Method:  POST
URL:     {{base_url}}/api/v1/music/songs/{{song_id}}/comments/
Headers:
    Content-Type: application/json
    X-CSRFToken:  {{csrftoken}}
Body (raw JSON):
```
```json
{
    "content": "Đồng ý với bạn! Mình cũng nghĩ vậy.",
    "parent_id": "{{comment_id}}"
}
```

**Response mong đợi (201):**
```json
{
    "success": true,
    "data": {
        "id": "reply-uuid",
        "content": "Đồng ý với bạn! Mình cũng nghĩ vậy.",
        "parent_id": "{{comment_id}}"
    }
}
```

**Test lỗi — reply của reply (400):**
> Lấy ID của reply vừa tạo, dùng làm `parent_id`:
```json
{
    "success": false,
    "error": {
        "code": "INVALID_PARENT",
        "message": "Không thể trả lời bình luận đã là reply"
    }
}
```

---

### ㉑ GET /api/v1/music/songs/<id>/comments/ — Danh sách bình luận

```
Method:  GET
URL:     {{base_url}}/api/v1/music/songs/{{song_id}}/comments/?page=1&page_size=20
Headers: (không cần auth)
```

**Response mong đợi (200):**
```json
{
    "success": true,
    "data": {
        "items": [
            {
                "id": "{{comment_id}}",
                "user": { "username": "normaluser" },
                "content": "Bài hát hay quá, nghe mãi không chán!",
                "like_count": 0,
                "is_liked": false,
                "parent_id": null,
                "replies": [
                    {
                        "id": "reply-uuid",
                        "user": { "username": "normaluser" },
                        "content": "Đồng ý với bạn! Mình cũng nghĩ vậy.",
                        "parent_id": "{{comment_id}}"
                    }
                ],
                "created_at": "..."
            }
        ],
        "pagination": { "page": 1, "page_size": 20, "total": 1, "total_pages": 1 }
    }
}
```

---

### ㉒ POST /api/v1/music/comments/<id>/like/ — Like bình luận

```
Method:  POST
URL:     {{base_url}}/api/v1/music/comments/{{comment_id}}/like/
Headers:
    X-CSRFToken: {{csrftoken}}
Body:    (không có)
```

**Response (200):**
```json
{
    "success": true,
    "data": { "action": "liked", "like_count": 1 }
}
```

Gọi lần 2 → unlike:
```json
{
    "success": true,
    "data": { "action": "unliked", "like_count": 0 }
}
```

---

### ㉓ DELETE /api/v1/music/comments/<id>/ — Xóa bình luận

> Chỉ owner (người tạo bình luận) mới xóa được.

```
Method:  DELETE
URL:     {{base_url}}/api/v1/music/comments/{{comment_id}}/
Headers:
    X-CSRFToken: {{csrftoken}}
Body:    (không có)
```

**Response mong đợi (204):** Không có body.

**Test lỗi — không phải owner (403):**
> Đăng nhập bằng user khác → gọi xóa comment của người khác:
```json
{
    "success": false,
    "error": {
        "code": "PERMISSION_DENIED",
        "message": "Bạn không có quyền xóa bình luận này"
    }
}
```

---

## 9. ListenHistory — Lịch Sử Nghe

### ㉔ GET /api/v1/music/me/history/ — Xem lịch sử nghe

> Phải đăng nhập. Chỉ xem lịch sử của chính mình.

```
Method:  GET
URL:     {{base_url}}/api/v1/music/me/history/?page=1&page_size=10
Headers: (đang đăng nhập)
```

**Response mong đợi (200):**
```json
{
    "success": true,
    "data": {
        "items": [
            {
                "song": {
                    "id": "{{song_id}}",
                    "title": "Shape of You (Remastered)",
                    "artist": { "display_name": "testartist" },
                    "cover_image": "https://res.cloudinary.com/...",
                    "duration": 234
                },
                "listened_at": "2026-06-11T08:30:00+07:00"
            }
        ],
        "pagination": { "page": 1, "page_size": 10, "total": 1, "total_pages": 1 }
    }
}
```

---

### ㉕ DELETE /api/v1/music/me/history/ — Xóa lịch sử nghe

```
Method:  DELETE
URL:     {{base_url}}/api/v1/music/me/history/
Headers:
    X-CSRFToken: {{csrftoken}}
Body:    (không có)
```

**Response mong đợi (204):** Không có body.

Gọi `GET /me/history/` lại → items rỗng.

---

## 10. Report — Báo Cáo Vi Phạm

### ㉖ POST /api/v1/music/reports/ — Gửi báo cáo

> Phải đăng nhập.

```
Method:  POST
URL:     {{base_url}}/api/v1/music/reports/
Headers:
    Content-Type: application/json
    X-CSRFToken:  {{csrftoken}}
Body (raw JSON):
```
```json
{
    "target_type": "song",
    "target_id": "{{song_id}}",
    "reason": "copyright",
    "description": "Bài hát này vi phạm bản quyền của nghệ sĩ ABC"
}
```

**Response mong đợi (201):**
```json
{
    "success": true,
    "data": {
        "id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
        "target_type": "song",
        "target_id": "{{song_id}}",
        "reason": "copyright",
        "description": "Bài hát này vi phạm bản quyền của nghệ sĩ ABC",
        "status": "pending",
        "created_at": "2026-06-11T09:00:00+07:00"
    }
}
```

✅ Copy `id` → paste vào Environment variable `report_id`.

**Test báo cáo comment:**
```json
{
    "target_type": "comment",
    "target_id": "{{comment_id}}",
    "reason": "offensive",
    "description": "Bình luận này có nội dung phản cảm"
}
```

**Test lỗi — reason không hợp lệ (400):**
```json
{
    "target_type": "song",
    "target_id": "{{song_id}}",
    "reason": "invalid_reason"
}
```
```json
{
    "success": false,
    "error": {
        "code": "VALIDATION_ERROR",
        "fields": { "reason": ["reason phải là một trong: copyright, spam, offensive, other"] }
    }
}
```

---

## 11. Admin Endpoints

> ⚠️ Tất cả endpoints dưới đây yêu cầu đăng nhập bằng tài khoản **admin**.

### ㉗ GET /api/v1/music/admin/reports/ — Xem báo cáo (Admin)

```
Method:  GET
URL:     {{base_url}}/api/v1/music/admin/reports/?status=pending&page=1
Headers: (đang login admin)
```

**Response mong đợi (200):**
```json
{
    "success": true,
    "data": {
        "items": [
            {
                "id": "{{report_id}}",
                "reporter": { "id": "uuid", "username": "normaluser" },
                "target_type": "song",
                "target_id": "{{song_id}}",
                "reason": "copyright",
                "description": "...",
                "status": "pending"
            }
        ],
        "pagination": { "page": 1, "page_size": 20, "total": 1, "total_pages": 1 }
    }
}
```

**Test filter:**
```
?status=resolved         → Chỉ báo cáo đã xử lý
?target_type=comment     → Chỉ báo cáo bình luận
?status=pending&target_type=song  → Kết hợp
```

---

### ㉘ POST /api/v1/music/admin/reports/<id>/resolve/ — Xử lý báo cáo

```
Method:  POST
URL:     {{base_url}}/api/v1/music/admin/reports/{{report_id}}/resolve/
Headers:
    Content-Type: application/json
    X-CSRFToken:  {{csrftoken}}
Body (raw JSON):
```
```json
{
    "action": "resolved",
    "note": "Đã xác minh vi phạm bản quyền và xử lý bài hát"
}
```

**Response mong đợi (200):**
```json
{
    "success": true,
    "data": {
        "id": "{{report_id}}",
        "status": "resolved",
        "resolved_by": "admin-uuid",
        "resolved_note": "Đã xác minh vi phạm bản quyền và xử lý bài hát"
    }
}
```

**Test bỏ qua báo cáo:**
```json
{
    "action": "dismissed",
    "note": "Không đủ bằng chứng vi phạm"
}
```

**Test lỗi — action không hợp lệ (400):**
```json
{ "action": "invalid" }
```
```json
{
    "success": false,
    "error": {
        "code": "VALIDATION_ERROR",
        "fields": { "action": ["action phải là \"resolved\" hoặc \"dismissed\""] }
    }
}
```

---

### ㉙ POST /api/v1/music/admin/songs/<id>/trending/ — Bật/Tắt Trending

```
Method:  POST
URL:     {{base_url}}/api/v1/music/admin/songs/{{song_id}}/trending/
Headers:
    X-CSRFToken: {{csrftoken}}
Body:    (không có)
```

**Response lần 1 — Bật trending (200):**
```json
{
    "success": true,
    "data": { "id": "{{song_id}}", "is_trending": true }
}
```

**Response lần 2 — Tắt trending (200):**
```json
{
    "success": true,
    "data": { "id": "{{song_id}}", "is_trending": false }
}
```

> Sau khi bật trending, gọi `GET /api/v1/music/songs/trending/` → bài hát xuất hiện.

---

### ㉚ POST /api/v1/music/admin/songs/<id>/hide/ — Admin Ẩn Bài Hát

```
Method:  POST
URL:     {{base_url}}/api/v1/music/admin/songs/{{song_id}}/hide/
Headers:
    X-CSRFToken: {{csrftoken}}
Body:    (không có)
```

**Response (200):**
```json
{
    "success": true,
    "data": { "id": "{{song_id}}", "status": "hidden" }
}
```

> Sau khi admin ẩn, bài hát không còn xuất hiện trong `GET /songs/` và trả 404 khi xem trực tiếp.

---

### ㉛ POST /api/v1/music/admin/comments/<id>/hide/ — Admin Ẩn Bình Luận

```
Method:  POST
URL:     {{base_url}}/api/v1/music/admin/comments/{{comment_id}}/hide/
Headers:
    X-CSRFToken: {{csrftoken}}
Body:    (không có)
```

**Response (200):**
```json
{
    "success": true,
    "data": { "id": "{{comment_id}}", "is_hidden": true }
}
```

> Sau khi ẩn, bình luận không còn xuất hiện trong `GET /songs/<id>/comments/`.

---

## 12. Test Scenarios — Luồng Test Kết Hợp

### Scenario A — Luồng đầy đủ từ đầu đến cuối

```
1.  GET  /api/v1/auth/csrf/                    → lấy CSRF token
2.  POST /api/v1/auth/login/   (admin)         → đăng nhập admin
3.  POST /api/v1/music/genres/                 → tạo genre "Pop"
4.  POST /api/v1/auth/login/   (artist)        → đăng nhập artist
5.  POST /api/v1/music/songs/                  → upload bài hát (draft)
6.  GET  /api/v1/music/songs/{{song_id}}/      → xem (artist thấy draft)
7.  POST /api/v1/music/songs/{{song_id}}/publish/  → phát hành
8.  GET  /api/v1/music/songs/                  → bài hiện trong list
9.  POST /api/v1/auth/login/   (user)          → đổi sang user thường
10. POST /api/v1/music/songs/{{song_id}}/play/ → nghe (play_count=1)
11. POST /api/v1/music/songs/{{song_id}}/play/ → nghe lại (vẫn =1, dedup)
12. POST /api/v1/music/songs/{{song_id}}/like/ → like (action=liked)
13. POST /api/v1/music/songs/{{song_id}}/rate/ → đánh giá 5 sao
14. POST /api/v1/music/songs/{{song_id}}/comments/  → bình luận
15. GET  /api/v1/music/songs/{{song_id}}/comments/  → xem danh sách
16. GET  /api/v1/music/me/history/             → lịch sử nghe
17. POST /api/v1/music/songs/{{song_id}}/download/  → tải về
```

---

### Scenario B — Test Block Policy (Fix R10)

```
1.  Đăng nhập artist A
2.  POST /api/v1/accounts/users/{{user_b_id}}/block/  → A block user B
3.  Đăng nhập user B
4.  GET /api/v1/music/songs/?artist_id={{artist_a_id}}
    → Bài hát của A KHÔNG xuất hiện trong list
5.  GET /api/v1/music/songs/{{song_of_A_id}}/
    → Trả 404 (giả vờ không tồn tại)
6.  POST /api/v1/music/songs/{{song_of_A_id}}/comments/
    → Trả 403 BLOCKED
```

---

### Scenario C — Test CORS và CSRF

**Test thiếu X-CSRFToken (403):**
```
Method:  POST
URL:     {{base_url}}/api/v1/music/songs/{{song_id}}/like/
Headers: (KHÔNG có X-CSRFToken)
```
Response:
```json
{ "detail": "CSRF Failed: CSRF token missing." }
```

**Test CSRF token sai (403):**
```
Headers:
    X-CSRFToken: wrong_token_here
```

---

### Scenario D — Test Phân Quyền Đầy Đủ

| Action | Anonymous | User | Artist (not owner) | Artist (owner) | Admin |
|--------|-----------|------|-------------------|---------------|-------|
| GET /songs/ | ✅ | ✅ | ✅ | ✅ (+ draft của mình) | ✅ |
| POST /songs/ | ❌ 401 | ❌ 403 | ✅ | ✅ | ❌ 403 |
| POST /songs/publish/ | ❌ 401 | ❌ 403 | ❌ 403 | ✅ | ❌ 403 |
| POST /genres/ | ❌ 401 | ❌ 403 | ❌ 403 | ❌ 403 | ✅ |
| POST /admin/songs/.../hide/ | ❌ 401 | ❌ 403 | ❌ 403 | ❌ 403 | ✅ |
| POST /songs/.../like/ | ❌ 401 | ✅ | ✅ | ✅ | ✅ |

---

## 13. Bảng Tổng Hợp Tất Cả Endpoints

| # | Method | Endpoint | Auth | Test Status |
|---|--------|----------|------|-------------|
| ① | GET | `/api/v1/music/genres/` | Public | ☐ |
| ② | POST | `/api/v1/music/genres/` | Admin | ☐ |
| ③ | PUT | `/api/v1/music/genres/<id>/` | Admin | ☐ |
| ④ | DELETE | `/api/v1/music/genres/<id>/` | Admin | ☐ |
| ⑤ | POST | `/api/v1/music/songs/` | Artist | ☐ |
| ⑥ | GET | `/api/v1/music/songs/` | Public | ☐ |
| ⑦ | GET | `/api/v1/music/songs/trending/` | Public | ☐ |
| ⑧ | GET | `/api/v1/music/songs/<id>/` | Public | ☐ |
| ⑨ | POST | `/api/v1/music/songs/<id>/publish/` | Artist+Owner | ☐ |
| ⑩ | PATCH | `/api/v1/music/songs/<id>/` | Artist+Owner | ☐ |
| ⑪ | POST | `/api/v1/music/songs/<id>/hide/` | Artist+Owner | ☐ |
| ⑫ | DELETE | `/api/v1/music/songs/<id>/` | Artist+Owner | ☐ |
| ⑬ | POST | `/api/v1/music/songs/<id>/play/` | Auth | ☐ |
| ⑭ | GET | `/api/v1/music/songs/<id>/download/` | Auth | ☐ |
| ⑮ | POST | `/api/v1/music/songs/<id>/like/` | Auth | ☐ |
| ⑯ | GET | `/api/v1/music/songs/<id>/likes/` | Public | ☐ |
| ⑰ | POST | `/api/v1/music/songs/<id>/rate/` | Auth | ☐ |
| ⑱ | GET | `/api/v1/music/songs/<id>/rating/` | Public | ☐ |
| ⑲ | POST | `/api/v1/music/songs/<id>/comments/` | Auth | ☐ |
| ⑳ | POST | `/api/v1/music/songs/<id>/comments/` (reply) | Auth | ☐ |
| ㉑ | GET | `/api/v1/music/songs/<id>/comments/` | Public | ☐ |
| ㉒ | POST | `/api/v1/music/comments/<id>/like/` | Auth | ☐ |
| ㉓ | DELETE | `/api/v1/music/comments/<id>/` | Auth+Owner | ☐ |
| ㉔ | GET | `/api/v1/music/me/history/` | Auth | ☐ |
| ㉕ | DELETE | `/api/v1/music/me/history/` | Auth | ☐ |
| ㉖ | POST | `/api/v1/music/reports/` | Auth | ☐ |
| ㉗ | GET | `/api/v1/music/admin/reports/` | Admin | ☐ |
| ㉘ | POST | `/api/v1/music/admin/reports/<id>/resolve/` | Admin | ☐ |
| ㉙ | POST | `/api/v1/music/admin/songs/<id>/trending/` | Admin | ☐ |
| ㉚ | POST | `/api/v1/music/admin/songs/<id>/hide/` | Admin | ☐ |
| ㉛ | POST | `/api/v1/music/admin/comments/<id>/hide/` | Admin | ☐ |

> Tick ☐ → ✅ khi đã test thành công từng endpoint.

---

## Lưu Ý Quan Trọng

### Upload file audio trong Postman

- Body type phải là **form-data**, KHÔNG phải raw JSON
- Với field `audio_file`: chọn type là **File** (không phải Text)
- KHÔNG set header `Content-Type` thủ công khi dùng form-data — Postman tự set `multipart/form-data; boundary=...`
- File audio test có thể là file `.mp3` bất kỳ, kể cả file nhỏ vài KB

### Session khác nhau cho mỗi role

Postman dùng **cookie jar chung** cho cùng domain. Khi bạn login bằng admin thì session của user trước bị ghi đè. Để test nhiều role cùng lúc:
- Dùng nhiều **tab** khác nhau trong Postman
- Hoặc dùng **Postman Environments** khác nhau
- Hoặc mở **Incognito/Private window** trong browser để test song song

### Thứ tự test bắt buộc

```
LUÔN gọi GET /csrf/ → POST /login/ trước
rồi mới gọi các POST/PATCH/DELETE endpoint.
Nếu thấy lỗi 403 CSRF: gọi lại /csrf/ và /login/ từ đầu.
```
