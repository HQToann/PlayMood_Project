# 04 — Hướng Dẫn Test API `artists` Trên Postman

**8 endpoints | Session + CSRF Authentication | Trọng tâm: test role Artist + Stats**

---

## Mục Lục

1. [Thiết lập Postman trước khi test](#1-thiết-lập-postman-trước-khi-test)
2. [Quy trình xác thực bắt buộc](#2-quy-trình-xác-thực-bắt-buộc)
3. [Test Artist Discovery](#3-test-artist-discovery)
4. [Test My Artist Profile](#4-test-my-artist-profile)
5. [Test Artist Cover Upload](#5-test-artist-cover-upload)
6. [Test Artist Stats](#6-test-artist-stats)
7. [Test Scenarios — Luồng kết hợp](#7-test-scenarios--luồng-kết-hợp)
8. [Bảng tổng hợp checklist](#8-bảng-tổng-hợp-checklist)

---

## 1. Thiết Lập Postman Trước Khi Test

### 1.1 Tạo Environment

Vào **Environments** -> **New** -> đặt tên `Music Platform - Artists`

| Variable | Initial Value | Mô tả |
|----------|--------------|-------|
| `base_url` | `http://localhost:8000` | URL server |
| `csrftoken` | *(để trống)* | Tự cập nhật sau khi gọi `/csrf/` |
| `sessionid` | *(để trống)* | Tự cập nhật sau khi login |
| `artist_user_id` | *(để trống)* | ID user nghệ sĩ dùng để test endpoint công khai |

### 1.2 Cấu hình Cookie

Vào **Settings** (icon bánh răng) -> **General**:
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

> Đây là bước quan trọng nhất — nếu bỏ qua, mọi request POST/PATCH sẽ trả về lỗi `403 CSRF Failed`.

### Bước 1 — Lấy CSRF Token

```
Method:  GET
URL:     {{base_url}}/api/v1/auth/csrf/
Headers: (không cần)
```

**Response mong đợi (200):**
```json
{ "success": true, "detail": "CSRF cookie set" }
```

Copy giá trị `csrftoken` từ tab Cookies -> paste vào Environment variable `csrftoken`.

---

### Bước 2 — Tạo và đăng nhập tài khoản Artist

> **Quan trọng:** App `artists` yêu cầu `role='artist'`. Cần tạo tài khoản đúng role trước khi test.

```bash
python manage.py shell -c "
from accounts.models import User
u = User.objects.create_user(
    username='testartist', email='artist@example.com',
    password='Artist1234', role='artist'
)
print('Artist ID:', u.id)
"
```

Copy `Artist ID` -> paste vào Environment variable `artist_user_id`.

Đăng nhập:
```
Method:  POST
URL:     {{base_url}}/api/v1/auth/login/
Headers:
    Content-Type: application/json
    X-CSRFToken:  {{csrftoken}}
Body (raw JSON):
```
```json
{ "email": "artist@example.com", "password": "Artist1234" }
```

**Response mong đợi (200):**
```json
{ "success": true, "data": { "id": "{{artist_user_id}}", "username": "testartist", "role": "artist" } }
```

---

### Bước 3 — Tạo tài khoản User thường (để test phân quyền 403)

```bash
python manage.py shell -c "
from accounts.models import User
User.objects.create_user(username='normaluser', email='user@example.com', password='Test1234', role='user')
"
```

> Dùng tài khoản này ở **Scenario B** (Mục 7) để test các API artist-only phải trả `403 ARTIST_ONLY`.

---

## 3. Test Artist Discovery

### 1. GET /api/v1/artists/ — Danh sách nghệ sĩ

```
Method:  GET
URL:     {{base_url}}/api/v1/artists/
Headers: (không cần auth)
Body:    (không có)
```

**Response mong đợi (200) khi chưa có nghệ sĩ nào tạo hồ sơ:**
```json
{
    "success": true,
    "data": { "items": [], "pagination": { "page": 1, "page_size": 20, "total": 0, "total_pages": 1 } }
}
```

> Danh sách sẽ có dữ liệu sau khi hoàn thành Mục 4 (tạo hồ sơ nghệ sĩ).

**Test với query tìm kiếm:**
```
URL: {{base_url}}/api/v1/artists/?q=dj&page=1&page_size=10
```

---

## 4. Test My Artist Profile

### 2. GET /api/v1/artists/me/ — Xem hồ sơ của tôi (tự tạo nếu chưa có)

```
Method:  GET
URL:     {{base_url}}/api/v1/artists/me/
Headers: (đang đăng nhập bằng artist)
Body:    (không có)
```

**Response mong đợi (200) — lần đầu gọi sẽ tự tạo hồ sơ rỗng:**
```json
{
    "success": true,
    "data": {
        "id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
        "user": { "id": "{{artist_user_id}}", "username": "testartist", "avatar": null },
        "stage_name": "", "display_name": "testartist", "bio": "",
        "cover_image": null, "website_url": "", "facebook_url": "", "youtube_url": "",
        "is_owner": true,
        "created_at": "2026-06-28T08:00:00+07:00",
        "updated_at": "2026-06-28T08:00:00+07:00"
    }
}
```

**Test lỗi — đăng nhập bằng user thường (403):**
> Đăng nhập lại bằng `normaluser` (Bước 3 ở Mục 2), gọi lại endpoint này:
```json
{ "success": false, "error": { "code": "ARTIST_ONLY", "message": "Chi nghe si moi duoc thuc hien hanh dong nay" } }
```

**Test lỗi — chưa đăng nhập (401):**
```json
{ "success": false, "error": { "code": "AUTH_REQUIRED", "message": "Ban can dang nhap de thuc hien hanh dong nay" } }
```

---

### 3. POST /api/v1/artists/me/ — Tạo hồ sơ nghệ sĩ với đầy đủ thông tin

> Có thể bỏ qua bước này nếu đã có hồ sơ rỗng từ bước 2 — dùng `PATCH` để điền thông tin thay thế.
> Nếu muốn test rõ luồng tạo mới, xóa hồ sơ cũ qua Django Admin trước khi gọi lại.

```
Method:  POST
URL:     {{base_url}}/api/v1/artists/me/
Headers:
    Content-Type: application/json
    X-CSRFToken:  {{csrftoken}}
Body (raw JSON):
```
```json
{
    "stage_name": "DJ Coolio",
    "bio": "Nghe si dien tu tu Ha Noi, chuyen the loai EDM va Future Bass",
    "website_url": "https://djcoolio.com",
    "facebook_url": "https://facebook.com/djcoolio",
    "youtube_url": "https://youtube.com/djcoolio"
}
```

**Response mong đợi (201):**
```json
{
    "success": true,
    "data": {
        "id": "uuid", "stage_name": "DJ Coolio", "display_name": "DJ Coolio",
        "bio": "Nghe si dien tu tu Ha Noi, chuyen the loai EDM va Future Bass",
        "website_url": "https://djcoolio.com", "is_owner": true
    }
}
```

**Test lỗi — đã có hồ sơ (409):**
> Gọi lại đúng request trên lần thứ 2:
```json
{ "success": false, "error": { "code": "ALREADY_EXISTS", "message": "Ho so nghe si da ton tai" } }
```

**Test XSS sanitize (Fix R12):**
```json
{ "stage_name": "<script>alert(1)</script>DJ Test", "bio": "" }
```
Response — stage_name đã bị strip script:
```json
{ "data": { "stage_name": "DJ Test" } }
```

**Test lỗi — URL không hợp lệ (400):**
```json
{ "website_url": "javascript:alert(1)" }
```
```json
{
    "success": false,
    "error": { "code": "VALIDATION_ERROR", "fields": { "website_url": ["URL phai bat dau bang http:// hoac https://"] } }
}
```

---

### 4. PATCH /api/v1/artists/me/ — Cập nhật hồ sơ

```
Method:  PATCH
URL:     {{base_url}}/api/v1/artists/me/
Headers:
    Content-Type: application/json
    X-CSRFToken:  {{csrftoken}}
Body (raw JSON):
```
```json
{
    "stage_name": "DJ Coolio (Updated)",
    "bio": "Mo ta moi da cap nhat"
}
```

**Response mong đợi (200):**
```json
{ "success": true, "data": { "stage_name": "DJ Coolio (Updated)", "bio": "Mo ta moi da cap nhat" } }
```

**Test lỗi — không có dữ liệu (400):**
```json
{}
```
```json
{ "success": false, "error": { "code": "VALIDATION_ERROR", "message": "Khong co du lieu de cap nhat" } }
```

---

## 5. Test Artist Cover Upload

### 5. POST /api/v1/artists/me/cover/ — Upload ảnh bìa

```
Method:  POST
URL:     {{base_url}}/api/v1/artists/me/cover/
Headers:
    X-CSRFToken: {{csrftoken}}
    (KHONG dat Content-Type — Postman tu set multipart/form-data)
Body: form-data
```

| Key | Type | Value |
|-----|------|-------|
| `cover_image` | File | [Chon file .jpg hoac .png tu may] |

**Response mong đợi (200):**
```json
{ "success": true, "data": { "cover_image": "http://res.cloudinary.com/.../covers/artists/uuid.jpg" } }
```

**Test lỗi — sai MIME type (400):**
Upload file `.txt`:
```json
{ "success": false, "error": { "code": "VALIDATION_ERROR", "fields": { "cover_image": ["Chi chap nhan JPG, PNG, WEBP"] } } }
```

**Test lỗi — chưa tạo hồ sơ (404):**
> Dùng tài khoản artist MỚI chưa từng gọi `GET /me/` hay `POST /me/`:
```json
{ "success": false, "error": { "code": "NOT_FOUND", "message": "Ho so nghe si khong ton tai" } }
```

---

## 6. Test Artist Stats

> Đây là phần quan trọng nhất cần test kỹ — số liệu phải khớp đúng với dữ liệu thật trong DB.

### Chuẩn bị dữ liệu mẫu để test stats có ý nghĩa

```bash
python manage.py shell -c "
from accounts.models import User
from music.models import Genre, Song, Like, Rating, Comment, ListenHistory
from django.core.files.uploadedfile import SimpleUploadedFile

artist = User.objects.get(username='testartist')
listener1 = User.objects.create_user(username='listener1', email='listener1@example.com', password='Test1234')
listener2 = User.objects.create_user(username='listener2', email='listener2@example.com', password='Test1234')

genre, _ = Genre.objects.get_or_create(name='EDM')

song1 = Song.objects.create(
    title='Track One', artist=artist, genre=genre, duration=200,
    status=Song.STATUS_PUBLISHED, play_count=150,
    audio_file=SimpleUploadedFile('t1.mp3', b'\x00'*1024, content_type='audio/mpeg'),
)
song2 = Song.objects.create(
    title='Track Two', artist=artist, genre=genre, duration=180,
    status=Song.STATUS_PUBLISHED, play_count=300,
    audio_file=SimpleUploadedFile('t2.mp3', b'\x00'*1024, content_type='audio/mpeg'),
)
# Bai draft - KHONG duoc tinh vao stats
Song.objects.create(
    title='Draft Track', artist=artist, genre=genre, duration=150,
    status=Song.STATUS_DRAFT, play_count=999,
    audio_file=SimpleUploadedFile('t3.mp3', b'\x00'*1024, content_type='audio/mpeg'),
)

Like.objects.create(user=listener1, song=song1)
Like.objects.create(user=listener2, song=song1)
Like.objects.create(user=listener1, song=song2)

Rating.objects.create(user=listener1, song=song1, score=5)
Rating.objects.create(user=listener2, song=song2, score=3)

Comment.objects.create(user=listener1, song=song1, content='Bai nay hay qua!')
Comment.objects.create(user=listener2, song=song2, content='Thich phong cach nay')

ListenHistory.objects.create(user=listener1, song=song1)
ListenHistory.objects.create(user=listener1, song=song2)
ListenHistory.objects.create(user=listener2, song=song1)

print('Du lieu mau da tao xong. song1.id =', song1.id, '| song2.id =', song2.id)
"
```

---

### 6. GET /api/v1/artists/me/stats/ — Thống kê của chính mình

```
Method:  GET
URL:     {{base_url}}/api/v1/artists/me/stats/
Headers: (dang dang nhap bang artist)
Body:    (khong co)
```

**Response mong đợi (200) với dữ liệu mẫu vừa tạo:**
```json
{
    "success": true,
    "data": {
        "total_songs": 2,
        "total_play_count": 450,
        "total_likes": 3,
        "total_comments": 2,
        "total_listeners": 2,
        "avg_rating": 4.0,
        "rating_count": 2,
        "top_songs": [
            { "id": "uuid-song2", "title": "Track Two", "play_count": 300, "like_count": 1, "cover_image": null },
            { "id": "uuid-song1", "title": "Track One", "play_count": 150, "like_count": 2, "cover_image": null }
        ]
    }
}
```

**Đối chiếu từng số liệu:**

| Field | Giá trị mong đợi | Giải thích |
|-------|------------------|------------|
| `total_songs` | 2 | Chỉ 2 bài published (bài draft 999 play_count KHÔNG tính) |
| `total_play_count` | 450 | 150 + 300 = 450 (Sum, không phải Count số bài) |
| `total_likes` | 3 | 2 like trên song1 + 1 like trên song2 |
| `total_comments` | 2 | 1 comment mỗi bài |
| `total_listeners` | 2 | Chỉ có 2 NGƯỜI duy nhất (listener1, listener2), kể cả khi listener1 nghe 2 bài |
| `avg_rating` | 4.0 | (5 + 3) / 2 = 4.0 |
| `rating_count` | 2 | 2 lượt đánh giá |
| `top_songs[0]` | Track Two (300) | Sắp xếp giảm dần theo play_count |

**Test lỗi — đăng nhập bằng user thường (403):**
```json
{ "success": false, "error": { "code": "ARTIST_ONLY" } }
```

**Test lỗi — chưa đăng nhập (401):**
```json
{ "success": false, "error": { "code": "AUTH_REQUIRED" } }
```

---

### 7. GET /api/v1/artists/\<user_id\>/stats/ — Thống kê công khai

```
Method:  GET
URL:     {{base_url}}/api/v1/artists/{{artist_user_id}}/stats/
Headers: (khong can auth)
Body:    (khong co)
```

**Response mong đợi (200):** Giống cấu trúc ở bước 6 — số liệu công khai, ai xem cũng giống nhau.

**Test lỗi — nghệ sĩ không tồn tại (404):**
```
URL: {{base_url}}/api/v1/artists/00000000-0000-0000-0000-000000000000/stats/
```
```json
{ "success": false, "error": { "code": "NOT_FOUND", "message": "Ho so nghe si khong ton tai" } }
```

---

### 8. GET /api/v1/artists/\<user_id\>/ — Xem hồ sơ công khai

```
Method:  GET
URL:     {{base_url}}/api/v1/artists/{{artist_user_id}}/
Headers: (khong can auth)
```

**Response mong đợi (200):** Giống cấu trúc hồ sơ ở Mục 4, với `is_owner: false` nếu xem bằng người khác.

**Test playlist riêng tư bị block (404):**
> Đăng nhập artist -> block user khác qua `POST /api/v1/accounts/users/<other_id>/block/` (đã có từ Tuần 1)
> -> đăng nhập user bị block -> gọi lại endpoint này -> phải trả 404.

---

## 7. Test Scenarios — Luồng Kết Hợp

### Scenario A — Luồng đầy đủ từ đầu đến cuối

```
1.  GET  /api/v1/auth/csrf/                          -> lay CSRF token
2.  POST /api/v1/auth/login/  (artist)                -> dang nhap artist
3.  GET  /api/v1/artists/me/                          -> tu tao ho so rong
4.  PATCH /api/v1/artists/me/                         -> dien stage_name, bio
5.  POST /api/v1/artists/me/cover/                    -> upload anh bia
6.  (tao du lieu mau qua Django shell - xem Muc 6)
7.  GET  /api/v1/artists/me/stats/                    -> xem thong ke chinh xac
8.  POST /api/v1/auth/logout/                         -> dang xuat
9.  GET  /api/v1/artists/                             -> nguoi khac thay nghe si trong danh sach
10. GET  /api/v1/artists/{{artist_user_id}}/          -> xem trang ca nhan cong khai
11. GET  /api/v1/artists/{{artist_user_id}}/stats/    -> xem thong ke cong khai
```

---

### Scenario B — Test Phân Quyền Role Artist Đầy Đủ

| Action | Anonymous | User thường | Artist (không phải owner) | Artist (owner) |
|--------|-----------|-------------|---------------------------|-----------------|
| GET /artists/ | 200 | 200 | 200 | 200 |
| GET /artists/me/ | 401 | 403 ARTIST_ONLY | 200 (tạo profile riêng) | 200 |
| POST /artists/me/ | 401 | 403 | 201 (tạo profile riêng) | 409 nếu đã có |
| PATCH /artists/me/ | 401 | 403 | 200 (sửa profile riêng) | 200 |
| POST /artists/me/cover/ | 401 | 403 | 200 (cover riêng) | 200 |
| GET /artists/me/stats/ | 401 | 403 | 200 (stats riêng) | 200 |
| GET /artists/\<id\>/ | 200 | 200 | 200 | 200 |
| GET /artists/\<id\>/stats/ | 200 | 200 | 200 | 200 |

> Lưu ý quan trọng: `/me/...` luôn tác động lên **chính người gọi request**, không có khái niệm "sửa hồ sơ artist khác qua /me/" — vì vậy không có test case "Artist B sửa hồ sơ Artist A qua /me/". Thay vào đó, "không phải owner" chỉ xảy ra nếu cố tình gọi trực tiếp `update_artist_profile()` ở tầng service với `profile` không khớp `user` — đã test ở `tests.py::test_update_profile_not_owner_raises`.

---

### Scenario C — Test Toàn Vẹn Số Liệu Stats

```
1. Tao artist + 2 bai hat published (play_count: 100, 200) + 1 bai draft (play_count: 999)
   -> GET /me/stats/  =>  total_songs=2, total_play_count=300 (KHONG cong 999)

2. 1 user like ca 2 bai
   -> GET /me/stats/  =>  total_likes=2

3. Cung 1 user nghe ca 2 bai (2 ListenHistory record)
   -> GET /me/stats/  =>  total_listeners=1 (KHONG phai 2, vi la 1 NGUOI)

4. 2 user khac nhau rate 1 bai diem 5 va 1 bai diem 1
   -> GET /me/stats/  =>  avg_rating = 3.0, rating_count = 2
```

---

## 8. Bảng Tổng Hợp Checklist

| # | Method | Endpoint | Test Status |
|---|--------|----------|--------------|
| 1 | GET | /api/v1/artists/ | [ ] |
| 2 | GET | /api/v1/artists/me/ | [ ] |
| 3 | POST | /api/v1/artists/me/ | [ ] |
| 4 | PATCH | /api/v1/artists/me/ | [ ] |
| 5 | POST | /api/v1/artists/me/cover/ | [ ] |
| 6 | GET | /api/v1/artists/me/stats/ | [ ] |
| 7 | GET | /api/v1/artists/<user_id>/ | [ ] |
| 8 | GET | /api/v1/artists/<user_id>/stats/ | [ ] |

> Tick [ ] -> [x] khi đã test thành công từng endpoint, bao gồm cả test case lỗi và đối chiếu số liệu stats.

---

## Lưu Ý Quan Trọng

### Tạo dữ liệu mẫu là bước bắt buộc để test Stats có ý nghĩa

Không như các app trước, stats sẽ luôn trả về `0`/`null` nếu chưa có `Song`/`Like`/`Rating`/`Comment`/`ListenHistory` nào liên kết với artist. Luôn chạy đoạn script ở Mục 6 trước khi test phần Stats.

### Session khác nhau khi test artist vs user thường

Postman dùng cookie jar chung theo domain. Để test Scenario B (artist vs user thường) cùng lúc:
- Dùng nhiều Environment Postman khác nhau
- Hoặc test tuần tự: login artist -> test xong -> logout -> login user thường -> test tiếp

### Kiểm tra nhanh qua Django Admin

Truy cập `http://localhost:8000/admin/` -> **Nghe si** -> xem trực tiếp `ArtistProfile` đã tạo, đối chiếu với response API.
