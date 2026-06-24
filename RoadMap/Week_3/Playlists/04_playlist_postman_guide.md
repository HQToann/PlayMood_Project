# 04 — Hướng Dẫn Test API `playlists` Trên Postman

**11 endpoints | Session + CSRF Authentication**

---

## Mục Lục

1. [Thiết lập Postman trước khi test](#1-thiết-lập-postman-trước-khi-test)
2. [Quy trình xác thực bắt buộc](#2-quy-trình-xác-thực-bắt-buộc)
3. [Test Playlist CRUD](#3-test-playlist-crud)
4. [Test Playlist Visibility](#4-test-playlist-visibility)
5. [Test Playlist Cover Upload](#5-test-playlist-cover-upload)
6. [Test Playlist Songs Management](#6-test-playlist-songs-management)
7. [Test Scenarios — Luồng kết hợp](#7-test-scenarios--luồng-kết-hợp)
8. [Bảng tổng hợp checklist](#8-bảng-tổng-hợp-checklist)

---

## 1. Thiết Lập Postman Trước Khi Test

### 1.1 Tạo Environment

Vào **Environments** → **New** → đặt tên `Music Platform - Playlists`

| Variable | Initial Value | Mô tả |
|----------|--------------|-------|
| `base_url` | `http://localhost:8000` | URL server |
| `csrftoken` | *(để trống)* | Tự cập nhật sau khi gọi `/csrf/` |
| `sessionid` | *(để trống)* | Tự cập nhật sau khi login |
| `playlist_id` | *(để trống)* | ID playlist vừa tạo |
| `song_id` | *(để trống)* | ID bài hát sẵn có (từ Tuần 2) |

### 1.2 Cấu hình Cookie

Vào **Settings** (icon bánh răng) → **General**:
- Automatically follow redirects: ON
- Send cookies: ON
- Store cookies in cookie jar: ON

### 1.3 Collection-level Pre-request Script

```javascript
const cookieJar = pm.cookies.jar();
cookieJar.get(pm.environment.get('base_url'), 'csrftoken', (err, value) => {
    if (value) pm.environment.set('csrftoken', value);
});
```

---

## 2. Quy Trình Xác Thực Bắt Buộc

> Đây là bước quan trọng nhất — nếu bỏ qua, mọi request POST/PATCH/DELETE sẽ trả về lỗi `403 CSRF Failed`.

### Bước 1 — Lấy CSRF Token

```
Method:  GET
URL:     {{base_url}}/api/v1/auth/csrf/
Headers: (không cần)
Body:    (không có)
```

**Response mong đợi (200):**
```json
{ "success": true, "detail": "CSRF cookie set" }
```

Sau bước này: vào tab **Cookies** của Postman (dưới ô URL) → copy giá trị `csrftoken` → paste vào Environment variable `csrftoken`.

> **Giải thích cơ chế:** Django set cookie `csrftoken` (không `HttpOnly` — JS đọc được). Mọi request thay đổi dữ liệu (POST/PATCH/DELETE) phải gửi kèm giá trị này qua header `X-CSRFToken`. Nếu thiếu, Django CSRF middleware chặn ngay với `403`.

---

### Bước 2 — Đăng nhập

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
    "data": { "id": "uuid", "username": "testuser", "role": "user", "email": "user@example.com" }
}
```

Sau bước này: cookie `sessionid` được Postman tự lưu — mọi request tiếp theo trong cùng Collection sẽ tự động gửi kèm cookie này.

> **Lưu ý:** Nếu chưa có tài khoản, đăng ký trước bằng `POST /api/v1/auth/register/` hoặc tạo nhanh qua Django shell:
> ```bash
> python manage.py shell -c "
> from accounts.models import User
> User.objects.create_user(username='testuser', email='user@example.com', password='Test1234')
> "
> ```

---

### Bước 3 — Đảm bảo có ít nhất 1 bài hát published để test thêm vào playlist

Tạo nhanh qua Django shell nếu chưa có:
```bash
python manage.py shell -c "
from accounts.models import User
from music.models import Genre, Song
from django.core.files.uploadedfile import SimpleUploadedFile

artist = User.objects.filter(role='artist').first()
if not artist:
    artist = User.objects.create_user(username='testartist', email='artist@example.com', password='Artist1234', role='artist')

genre, _ = Genre.objects.get_or_create(name='Pop')

song = Song.objects.create(
    title='Test Song For Playlist',
    artist=artist, genre=genre, duration=200,
    status=Song.STATUS_PUBLISHED,
    audio_file=SimpleUploadedFile('test.mp3', b'\x00'*1024, content_type='audio/mpeg'),
)
print('Song ID:', song.id)
"
```
Copy `Song ID` in ra → paste vào Environment variable `song_id`.

---

## 3. Test Playlist CRUD

### 1. GET /api/v1/playlists/ — Danh sách playlist của tôi

```
Method:  GET
URL:     {{base_url}}/api/v1/playlists/
Headers: (Postman tự gửi cookie sessionid)
Body:    (không có)
```

**Response mong đợi (200):**
```json
{
    "success": true,
    "data": { "items": [], "pagination": { "page": 1, "page_size": 20, "total": 0, "total_pages": 1 } }
}
```

**Test lỗi — chưa đăng nhập (401):**
> Xóa cookie `sessionid` hoặc dùng tab Incognito, gọi lại:
```json
{ "success": false, "error": { "code": "AUTH_REQUIRED", "message": "Bạn cần đăng nhập để thực hiện hành động này" } }
```

---

### 2. POST /api/v1/playlists/ — Tạo playlist mới

```
Method:  POST
URL:     {{base_url}}/api/v1/playlists/
Headers:
    Content-Type: application/json
    X-CSRFToken:  {{csrftoken}}
Body (raw JSON):
```
```json
{
    "title": "Chill Vibes",
    "description": "Nhạc nhẹ nhàng nghe buổi tối",
    "is_public": true
}
```

**Response mong đợi (201):**
```json
{
    "success": true,
    "data": {
        "id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
        "title": "Chill Vibes",
        "description": "Nhạc nhẹ nhàng nghe buổi tối",
        "cover_image": null,
        "is_public": true,
        "owner": { "id": "uuid", "username": "testuser", "display_name": "testuser", "avatar": null },
        "song_count": 0,
        "is_owner": true,
        "created_at": "2026-06-24T08:00:00+07:00",
        "updated_at": "2026-06-24T08:00:00+07:00"
    }
}
```

Copy giá trị `id` → paste vào Environment variable `playlist_id`.

**Test playlist riêng tư:**
```json
{ "title": "My Private List", "is_public": false }
```

**Test lỗi — thiếu title (400):**
```json
{ "description": "Không có title" }
```
```json
{
    "success": false,
    "error": { "code": "VALIDATION_ERROR", "message": "Dữ liệu playlist không hợp lệ",
               "fields": { "title": ["Tên playlist là bắt buộc"] } }
}
```

**Test XSS sanitize (Fix R12):**
```json
{ "title": "<script>alert(1)</script>Test Title" }
```
Response — title đã bị strip script:
```json
{ "data": { "title": "Test Title" } }
```

---

### 3. GET /api/v1/playlists/<id>/ — Chi tiết playlist

```
Method:  GET
URL:     {{base_url}}/api/v1/playlists/{{playlist_id}}/
Headers: (không cần auth nếu playlist public)
```

**Response mong đợi (200):** Giống cấu trúc ở bước 2.

**Test playlist riêng tư bị người khác xem (404):**
> Tạo 1 playlist `is_public: false`, đăng nhập user khác, gọi GET vào playlist đó:
```json
{ "success": false, "error": { "code": "NOT_FOUND", "message": "Playlist không tồn tại" } }
```

**Test playlist không tồn tại (404):**
```
URL: {{base_url}}/api/v1/playlists/00000000-0000-0000-0000-000000000000/
```

---

### 4. PATCH /api/v1/playlists/<id>/ — Cập nhật playlist

```
Method:  PATCH
URL:     {{base_url}}/api/v1/playlists/{{playlist_id}}/
Headers:
    Content-Type: application/json
    X-CSRFToken:  {{csrftoken}}
Body (raw JSON):
```
```json
{
    "title": "Chill Vibes (Updated)",
    "description": "Đã cập nhật mô tả mới"
}
```

**Response mong đợi (200):**
```json
{
    "success": true,
    "data": { "id": "{{playlist_id}}", "title": "Chill Vibes (Updated)", "description": "Đã cập nhật mô tả mới" }
}
```

**Test phân quyền — không phải owner (403):**
> Đăng nhập bằng tài khoản KHÁC, gọi lại PATCH vào playlist của người khác:
```json
{ "success": false, "error": { "code": "PERMISSION_DENIED",
  "message": "Bạn không có quyền thực hiện hành động này với playlist này" } }
```

**Test lỗi — không có dữ liệu (400):**
```json
{}
```
```json
{ "success": false, "error": { "code": "VALIDATION_ERROR", "message": "Không có dữ liệu để cập nhật" } }
```

---

### 5. DELETE /api/v1/playlists/<id>/ — Xóa playlist

> Nên tạo 1 playlist test riêng để xóa, tránh mất `playlist_id` đang dùng cho các bước khác.

```
Method:  DELETE
URL:     {{base_url}}/api/v1/playlists/{{playlist_id}}/
Headers:
    X-CSRFToken: {{csrftoken}}
Body:    (không có)
```

**Response mong đợi (204):** Không có body.

**Test phân quyền — không phải owner (403):**
```json
{ "success": false, "error": { "code": "PERMISSION_DENIED", "message": "..." } }
```

---

## 4. Test Playlist Visibility

### 6. PATCH /api/v1/playlists/<id>/visibility/ — Đặt công khai / riêng tư

```
Method:  PATCH
URL:     {{base_url}}/api/v1/playlists/{{playlist_id}}/visibility/
Headers:
    Content-Type: application/json
    X-CSRFToken:  {{csrftoken}}
Body (raw JSON):
```
```json
{ "is_public": false }
```

**Response mong đợi (200):**
```json
{ "success": true, "data": { "is_public": false } }
```

**Test lỗi — giá trị không phải boolean (400):**
```json
{ "is_public": "yes" }
```
```json
{ "success": false, "error": { "code": "VALIDATION_ERROR", "fields": { "is_public": ["Giá trị phải là true hoặc false"] } } }
```

---

## 5. Test Playlist Cover Upload

### 7. POST /api/v1/playlists/<id>/cover/ — Upload ảnh bìa

```
Method:  POST
URL:     {{base_url}}/api/v1/playlists/{{playlist_id}}/cover/
Headers:
    X-CSRFToken: {{csrftoken}}
    (KHÔNG đặt Content-Type — Postman tự set multipart/form-data)
Body: form-data
```

| Key | Type | Value |
|-----|------|-------|
| `cover_image` | File | [Chọn file .jpg hoặc .png từ máy] |

**Response mong đợi (200):**
```json
{ "success": true, "data": { "cover_image": "http://res.cloudinary.com/.../covers/playlists/uuid.jpg" } }
```

**Test lỗi — sai MIME type (400):**
Upload file `.txt`:
```json
{ "success": false, "error": { "code": "VALIDATION_ERROR", "fields": { "cover_image": ["Chỉ chấp nhận JPG, PNG, WEBP"] } } }
```

**Test lỗi — thiếu file (400):**
```json
{ "success": false, "error": { "fields": { "cover_image": ["File ảnh là bắt buộc"] } } }
```

---

## 6. Test Playlist Songs Management

### 8. POST /api/v1/playlists/<id>/songs/ — Thêm bài hát

```
Method:  POST
URL:     {{base_url}}/api/v1/playlists/{{playlist_id}}/songs/
Headers:
    Content-Type: application/json
    X-CSRFToken:  {{csrftoken}}
Body (raw JSON):
```
```json
{ "song_id": "{{song_id}}" }
```

**Response mong đợi (201):**
```json
{
    "success": true,
    "data": {
        "id": "uuid",
        "song": {
            "id": "{{song_id}}", "title": "Test Song For Playlist",
            "artist": { "id": "uuid", "username": "testartist", "display_name": "testartist" },
            "cover_image": null, "duration": 200, "status": "published"
        },
        "order": 1,
        "added_at": "2026-06-24T08:10:00+07:00"
    }
}
```

**Test lỗi — bài hát đã có trong playlist (409):**
> Gọi lại đúng request trên lần thứ 2:
```json
{ "success": false, "error": { "code": "ALREADY_EXISTS", "message": "Bài hát này đã có trong playlist" } }
```

**Test lỗi — bài hát không tồn tại (404):**
```json
{ "song_id": "00000000-0000-0000-0000-000000000000" }
```
```json
{ "success": false, "error": { "code": "NOT_FOUND", "message": "Bài hát không tồn tại" } }
```

**Test phân quyền — không phải owner (403):**
> Đăng nhập user khác, gọi thêm bài vào playlist không phải của mình.

---

### 9. GET /api/v1/playlists/<id>/songs/ — Danh sách bài hát trong playlist

```
Method:  GET
URL:     {{base_url}}/api/v1/playlists/{{playlist_id}}/songs/?page=1&page_size=20
Headers: (không cần auth nếu playlist public)
```

**Response mong đợi (200):**
```json
{
    "success": true,
    "data": {
        "items": [
            { "id": "uuid", "song": { "title": "Test Song For Playlist" }, "order": 1, "added_at": "..." }
        ],
        "pagination": { "page": 1, "page_size": 20, "total": 1, "total_pages": 1 }
    }
}
```

---

### 10. PATCH /api/v1/playlists/<id>/songs/reorder/ — Sắp xếp lại thứ tự

> Thêm ít nhất 2-3 bài hát vào playlist trước khi test bước này (lặp lại bước 8 với các `song_id` khác nhau).

```
Method:  PATCH
URL:     {{base_url}}/api/v1/playlists/{{playlist_id}}/songs/reorder/
Headers:
    Content-Type: application/json
    X-CSRFToken:  {{csrftoken}}
Body (raw JSON):
```
```json
{
    "song_ids": ["uuid-bai-2", "uuid-bai-1", "uuid-bai-3"]
}
```

> Lấy đúng danh sách `song_id` hiện có trong playlist từ kết quả bước 9, sau đó đổi thứ tự theo ý muốn.

**Response mong đợi (200):**
```json
{ "success": true, "message": "Đã cập nhật thứ tự" }
```

Gọi lại bước 9 để xác nhận thứ tự `order` đã thay đổi đúng.

**Test lỗi — thiếu bài hát trong danh sách gửi lên (400):**
```json
{ "song_ids": ["uuid-bai-1"] }
```
```json
{
    "success": false,
    "error": { "code": "VALIDATION_ERROR",
               "message": "Danh sách song_ids phải khớp chính xác với các bài hát hiện có trong playlist" }
}
```

**Test lỗi — ID không phải UUID hợp lệ (400):**
```json
{ "song_ids": ["not-a-uuid", "uuid-bai-2"] }
```

**Test lỗi — trùng lặp trong danh sách (400):**
```json
{ "song_ids": ["uuid-bai-1", "uuid-bai-1"] }
```

---

### 11. DELETE /api/v1/playlists/<id>/songs/<song_id>/ — Xóa bài hát khỏi playlist

```
Method:  DELETE
URL:     {{base_url}}/api/v1/playlists/{{playlist_id}}/songs/{{song_id}}/
Headers:
    X-CSRFToken: {{csrftoken}}
Body:    (không có)
```

**Response mong đợi (204):** Không có body.

**Test lỗi — bài hát không có trong playlist (404):**
> Gọi lại đúng request trên lần thứ 2 (đã xóa rồi):
```json
{ "success": false, "error": { "code": "NOT_FOUND", "message": "Bài hát không có trong playlist này" } }
```

---

## 7. Test Scenarios — Luồng Kết Hợp

### Scenario A — Luồng đầy đủ từ đầu đến cuối

```
1.  GET  /api/v1/auth/csrf/                               -> lấy CSRF token
2.  POST /api/v1/auth/login/                               -> đăng nhập
3.  POST /api/v1/playlists/                                 -> tạo playlist (public)
4.  POST /api/v1/playlists/{{playlist_id}}/songs/           -> thêm bài 1
5.  POST /api/v1/playlists/{{playlist_id}}/songs/           -> thêm bài 2 (song_id khác)
6.  POST /api/v1/playlists/{{playlist_id}}/songs/           -> thêm bài 3 (song_id khác)
7.  GET  /api/v1/playlists/{{playlist_id}}/songs/           -> xem đủ 3 bài, đúng thứ tự
8.  PATCH /api/v1/playlists/{{playlist_id}}/songs/reorder/  -> đổi thứ tự
9.  DELETE /api/v1/playlists/{{playlist_id}}/songs/<song1>/ -> xóa 1 bài
10. PATCH /api/v1/playlists/{{playlist_id}}/visibility/     -> đặt private
11. DELETE /api/v1/playlists/{{playlist_id}}/               -> xóa playlist
```

---

### Scenario B — Test Phân Quyền Owner Đầy Đủ

| Action | Owner | User khác (đăng nhập) | Anonymous |
|--------|-------|------------------------|-----------|
| GET playlist (public) | 200 | 200 | 200 |
| GET playlist (private) | 200 | 404 | 404 |
| PATCH playlist | 200 | 403 | 401 |
| DELETE playlist | 204 | 403 | 401 |
| POST thêm bài hát | 201 | 403 | 401 |
| DELETE xóa bài hát | 204 | 403 | 401 |
| PATCH reorder | 200 | 403 | 401 |
| PATCH visibility | 200 | 403 | 401 |
| POST upload cover | 200 | 403 | 401 |

**Cách test nhanh:** Mở 2 tab Postman, login user A ở tab 1, login user B ở tab 2 (dùng Environment khác nhau để tránh đè cookie), thử các action trên playlist của A từ tab của B.

---

### Scenario C — Test Toàn Vẹn Dữ Liệu Reorder

```
1. Tạo playlist, thêm 3 bài: A, B, C -> order: A=1, B=2, C=3
2. PATCH reorder voi [C, A, B] -> order: C=1, A=2, B=3        OK 200
3. PATCH reorder voi [A, B]    (thieu C)                       FAIL 400 InvalidReorderData
4. PATCH reorder voi [A, B, C, random-uuid]  (du 1 ID la)      FAIL 400 InvalidReorderData
5. PATCH reorder voi [A, A, B]  (trung lap)                    FAIL 400 (chan o validator)
```

---

## 8. Bảng Tổng Hợp Checklist

| # | Method | Endpoint | Test Status |
|---|--------|----------|-------------|
| 1 | GET | /api/v1/playlists/ | [ ] |
| 2 | POST | /api/v1/playlists/ | [ ] |
| 3 | GET | /api/v1/playlists/<id>/ | [ ] |
| 4 | PATCH | /api/v1/playlists/<id>/ | [ ] |
| 5 | DELETE | /api/v1/playlists/<id>/ | [ ] |
| 6 | PATCH | /api/v1/playlists/<id>/visibility/ | [ ] |
| 7 | POST | /api/v1/playlists/<id>/cover/ | [ ] |
| 8 | POST | /api/v1/playlists/<id>/songs/ | [ ] |
| 9 | GET | /api/v1/playlists/<id>/songs/ | [ ] |
| 10 | PATCH | /api/v1/playlists/<id>/songs/reorder/ | [ ] |
| 11 | DELETE | /api/v1/playlists/<id>/songs/<song_id>/ | [ ] |

> Tick [ ] -> [x] khi đã test thành công từng endpoint, bao gồm cả test case lỗi tương ứng.

---

## Lưu Ý Quan Trọng

### Thứ tự URL reorder/ vs <song_id>/

Route `songs/reorder/` được khai báo **trước** `songs/<uuid:song_id>/` trong `urls.py`. Nếu gọi sai thứ tự khi tự thêm route mới, Django có thể hiểu nhầm `reorder` là một UUID và trả lỗi 404 thay vì vào đúng view.

### Session khác nhau khi test phân quyền

Postman dùng cookie jar chung theo domain. Khi login user khác, session cũ bị ghi đè. Để test Scenario B (owner vs người khác) cùng lúc:
- Dùng nhiều Environment Postman khác nhau, mỗi Environment lưu riêng `sessionid`
- Hoặc test tuần tự: login A -> thực hiện hết test của A -> logout -> login B -> test tiếp

### Kiểm tra nhanh trạng thái dữ liệu qua Django Admin

Truy cập `http://localhost:8000/admin/` -> Playlists -> xem trực tiếp các Playlist và PlaylistSong (inline) để đối chiếu kết quả test.
