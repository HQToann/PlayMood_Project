# 04 — Hướng Dẫn Test API `social` Trên Postman

**10 endpoints | Session + CSRF Authentication | Trọng tâm: Follow, Mood, Feed**

---

## Mục Lục

1. [Thiết lập Postman trước khi test](#1-thiết-lập-postman-trước-khi-test)
2. [Quy trình xác thực bắt buộc](#2-quy-trình-xác-thực-bắt-buộc)
3. [Test Follow](#3-test-follow)
4. [Test Mood](#4-test-mood)
5. [Test Feed](#5-test-feed)
6. [Test Scenarios — Luồng kết hợp](#6-test-scenarios--luồng-kết-hợp)
7. [Bảng tổng hợp checklist](#7-bảng-tổng-hợp-checklist)

---

## 1. Thiết Lập Postman Trước Khi Test

### 1.1 Tạo Environment

Vào **Environments** -> **New** -> đặt tên `Music Platform - Social`

| Variable | Initial Value | Mô tả |
|----------|--------------|-------|
| `base_url` | `http://localhost:8000` | URL server |
| `csrftoken` | *(để trống)* | Tự cập nhật sau khi gọi `/csrf/` |
| `sessionid` | *(để trống)* | Tự cập nhật sau khi login |
| `alice_id` | *(để trống)* | ID user Alice |
| `bob_id` | *(để trống)* | ID user Bob |
| `song_id` | *(để trống)* | ID bài hát dùng để test Mood |

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

> App `social` cần test với **2 tài khoản khác nhau** (Alice và Bob) để kiểm tra luồng Follow → Feed đầy đủ.

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

### Bước 2 — Tạo 2 tài khoản test: Alice và Bob

```bash
python manage.py shell -c "
from accounts.models import User
alice = User.objects.create_user(username='alice', email='alice@example.com', password='Test1234')
bob = User.objects.create_user(username='bob', email='bob@example.com', password='Test1234')
print('Alice ID:', alice.id)
print('Bob ID:', bob.id)
"
```

Copy `Alice ID` -> paste vào Environment variable `alice_id`.
Copy `Bob ID` -> paste vào Environment variable `bob_id`.

---

### Bước 3 — Tạo nghệ sĩ và bài hát mẫu (dùng cho Mood)

```bash
python manage.py shell -c "
from accounts.models import User
from music.models import Genre, Song
from django.core.files.uploadedfile import SimpleUploadedFile

artist = User.objects.create_user(username='socialartist', email='socialartist@example.com', password='Artist1234', role='artist')
genre, _ = Genre.objects.get_or_create(name='Chill')
song = Song.objects.create(
    title='Chill Vibes Track', artist=artist, genre=genre, duration=200,
    status=Song.STATUS_PUBLISHED,
    audio_file=SimpleUploadedFile('chill.mp3', b'\x00'*1024, content_type='audio/mpeg'),
)
print('Song ID:', song.id)
"
```

Copy `Song ID` -> paste vào Environment variable `song_id`.

---

### Bước 4 — Đăng nhập bằng Alice

```
Method:  POST
URL:     {{base_url}}/api/v1/auth/login/
Headers:
    Content-Type: application/json
    X-CSRFToken:  {{csrftoken}}
Body (raw JSON):
```
```json
{ "email": "alice@example.com", "password": "Test1234" }
```

**Response mong đợi (200):**
```json
{ "success": true, "data": { "id": "{{alice_id}}", "username": "alice" } }
```

> Để test với Bob, lặp lại Bước 1 + đăng nhập bằng `bob@example.com` — khuyến nghị dùng **Environment riêng** hoặc test tuần tự (login Alice → test xong → logout → login Bob).

---

## 3. Test Follow

### 1. POST /api/v1/social/users/\<user_id\>/follow/ — Alice follow Bob

```
Method:  POST
URL:     {{base_url}}/api/v1/social/users/{{bob_id}}/follow/
Headers:
    X-CSRFToken: {{csrftoken}}
Body:    (không có)
```

**Response mong đợi lần đầu (200) — followed:**
```json
{
    "success": true,
    "data": { "action": "followed", "followers_count": 1, "target_user_id": "{{bob_id}}" }
}
```

**Test toggle — gọi lại lần thứ 2 (200) — unfollowed:**
```json
{
    "success": true,
    "data": { "action": "unfollowed", "followers_count": 0, "target_user_id": "{{bob_id}}" }
}
```

> **Để tiếp tục các bước test sau, gọi lại endpoint này 1 lần nữa để Alice follow Bob (action="followed").**

**Test lỗi — tự follow bản thân (400):**
```
URL: {{base_url}}/api/v1/social/users/{{alice_id}}/follow/
```
```json
{ "success": false, "error": { "code": "VALIDATION_ERROR", "message": "Ban khong the tu theo doi ban than" } }
```

**Test lỗi — user không tồn tại (404):**
```
URL: {{base_url}}/api/v1/social/users/00000000-0000-0000-0000-000000000000/follow/
```

**Test lỗi — bị block (403):**
> Đăng nhập Bob -> block Alice qua `POST /api/v1/accounts/users/{{alice_id}}/block/` (đã có từ Tuần 1)
> -> đăng nhập lại Alice -> gọi follow Bob:
```json
{ "success": false, "error": { "code": "BLOCKED", "message": "Ban khong the thuc hien hanh dong nay" } }
```

---

### 2. GET /api/v1/social/users/\<user_id\>/follow-status/ — Xem trạng thái follow

```
Method:  GET
URL:     {{base_url}}/api/v1/social/users/{{bob_id}}/follow-status/
Headers: (đang đăng nhập bằng Alice)
```

**Response mong đợi (200):**
```json
{ "success": true, "data": { "followers_count": 1, "following_count": 0, "is_following": true } }
```

> Gọi lại endpoint này KHÔNG đăng nhập (anonymous) — `is_following` sẽ luôn là `false`.

---

### 3. GET /api/v1/social/users/\<user_id\>/followers/ — Danh sách followers của Bob

```
Method:  GET
URL:     {{base_url}}/api/v1/social/users/{{bob_id}}/followers/?page=1&page_size=20
Headers: (không cần auth)
```

**Response mong đợi (200):**
```json
{
    "success": true,
    "data": {
        "items": [
            { "id": "{{alice_id}}", "username": "alice", "display_name": "alice", "avatar": null, "followed_at": "2026-06-29T08:00:00+07:00" }
        ],
        "pagination": { "page": 1, "page_size": 20, "total": 1, "total_pages": 1 }
    }
}
```

---

### 4. GET /api/v1/social/users/\<user_id\>/following/ — Danh sách following của Alice

```
Method:  GET
URL:     {{base_url}}/api/v1/social/users/{{alice_id}}/following/?page=1&page_size=20
Headers: (không cần auth)
```

**Response mong đợi (200):**
```json
{
    "success": true,
    "data": {
        "items": [
            { "id": "{{bob_id}}", "username": "bob", "display_name": "bob", "avatar": null, "followed_at": "2026-06-29T08:00:00+07:00" }
        ],
        "pagination": { "page": 1, "page_size": 20, "total": 1, "total_pages": 1 }
    }
}
```

---

## 4. Test Mood

> Đăng nhập bằng **Bob** cho phần này — vì ở Mục 6 (Test Scenarios), Mood của Bob sẽ xuất hiện trên Feed của Alice.

### 5. POST /api/v1/social/me/mood/ — Bob đặt Mood (có đính kèm bài hát)

```
Method:  POST
URL:     {{base_url}}/api/v1/social/me/mood/
Headers:
    Content-Type: application/json
    X-CSRFToken:  {{csrftoken}}
Body (raw JSON):
```
```json
{
    "status_text": "Dang nghe nhac chill cuoi tuan",
    "song_id": "{{song_id}}",
    "duration_hours": 24
}
```

**Response mong đợi (201):**
```json
{
    "success": true,
    "data": {
        "id": "uuid",
        "user": { "id": "{{bob_id}}", "username": "bob", "display_name": "bob", "avatar": null },
        "status_text": "Dang nghe nhac chill cuoi tuan",
        "song": { "id": "{{song_id}}", "title": "Chill Vibes Track", "artist_display_name": "socialartist", "cover_image": null },
        "expires_at": "2026-06-30T08:00:00+07:00",
        "is_expired": false,
        "created_at": "2026-06-29T08:00:00+07:00",
        "updated_at": "2026-06-29T08:00:00+07:00"
    }
}
```

**Test Mood không kèm bài hát (chỉ status_text):**
```json
{ "status_text": "Hom nay vui qua!" }
```
> `duration_hours` không gửi -> mặc định 24 giờ. `song_id` không gửi -> `song: null`.

**Test upsert — gọi lại với nội dung khác:**
```json
{ "status_text": "Da doi mood roi" }
```
> Mood cũ sẽ bị **thay thế** hoàn toàn, không tạo bản ghi mới. Gọi `GET /me/mood/` lại để xác nhận chỉ còn 1 Mood với nội dung mới nhất.

**Test lỗi XSS sanitize (Fix R12):**
```json
{ "status_text": "<script>alert(1)</script>Happy mood" }
```
Response — `status_text` đã bị strip script:
```json
{ "data": { "status_text": "Happy mood" } }
```

**Test lỗi — status_text rỗng (400):**
```json
{ "status_text": "" }
```
```json
{ "success": false, "error": { "fields": { "status_text": ["Trang thai la bat buoc"] } } }
```

**Test lỗi — duration_hours ngoài khoảng (400):**
```json
{ "status_text": "X", "duration_hours": 9999 }
```
```json
{ "success": false, "error": { "fields": { "duration_hours": ["Thoi gian hien thi phai tu 1 den 168 gio"] } } }
```

**Test lỗi — song_id không tồn tại (404):**
```json
{ "status_text": "X", "song_id": "00000000-0000-0000-0000-000000000000" }
```
```json
{ "success": false, "error": { "code": "NOT_FOUND", "message": "Bai hat khong ton tai" } }
```

---

### 6. GET /api/v1/social/me/mood/ — Xem Mood hiện tại của tôi

```
Method:  GET
URL:     {{base_url}}/api/v1/social/me/mood/
Headers: (đang đăng nhập)
```

**Response mong đợi (200):** giống cấu trúc ở Mục 5.

**Test lỗi — chưa từng đặt Mood (404):**
> Đăng nhập bằng tài khoản mới chưa từng gọi `POST /me/mood/`:
```json
{ "success": false, "error": { "code": "NOT_FOUND", "message": "Ban chua co tam trang nao duoc thiet lap" } }
```

---

### 7. GET /api/v1/social/users/\<user_id\>/mood/ — Xem Mood công khai của Bob

```
Method:  GET
URL:     {{base_url}}/api/v1/social/users/{{bob_id}}/mood/
Headers: (không cần auth)
```

**Response mong đợi (200) — có Mood đang hiển thị:**
```json
{ "success": true, "data": { "status_text": "Da doi mood roi", "song": null, ... } }
```

**Response mong đợi (200) — chưa có/đã hết hạn/bị block (trả `null`, không lỗi):**
```json
{ "success": true, "data": null }
```

---

### 8. DELETE /api/v1/social/me/mood/ — Xóa Mood hiện tại

```
Method:  DELETE
URL:     {{base_url}}/api/v1/social/me/mood/
Headers:
    X-CSRFToken: {{csrftoken}}
Body:    (không có)
```

**Response mong đợi (204):** Không có body.

Gọi lại `GET /me/mood/` -> phải trả `404`.

---

## 5. Test Feed

> **Trước khi test phần này**, đảm bảo: Alice đã follow Bob (Mục 3 bước 1), và Bob đã đặt ít nhất 1 Mood (Mục 4 bước 5) hoặc đã nghe 1 bài hát (xem hướng dẫn dưới).

### Bob nghe nhạc để sinh thêm hoạt động "playing"

```
Method:  POST
URL:     {{base_url}}/api/v1/music/songs/{{song_id}}/play/
Headers:
    X-CSRFToken: {{csrftoken}}
    (đang đăng nhập Bob)
Body:    (không có)
```

> Endpoint này thuộc app `music` (Tuần 2) — gọi nó sẽ **tự động** sinh `FriendActivity` loại `playing` nhờ tích hợp đã chuẩn bị sẵn, không cần gọi API nào ở `social`.

---

### 9. GET /api/v1/social/feed/ — Alice xem Bảng tin

```
Method:  GET
URL:     {{base_url}}/api/v1/social/feed/?page=1&page_size=20
Headers: (đang đăng nhập Alice)
```

**Response mong đợi (200) — thấy hoạt động của Bob:**
```json
{
    "success": true,
    "data": {
        "items": [
            {
                "id": "uuid",
                "user": { "id": "{{bob_id}}", "username": "bob", "display_name": "bob", "avatar": null },
                "activity_type": "playing",
                "extra_text": "",
                "song": { "id": "{{song_id}}", "title": "Chill Vibes Track", "artist_display_name": "socialartist", "cover_image": null },
                "created_at": "2026-06-29T08:35:00+07:00"
            },
            {
                "id": "uuid",
                "user": { "id": "{{bob_id}}", "username": "bob", "display_name": "bob", "avatar": null },
                "activity_type": "mood",
                "extra_text": "Da doi mood roi",
                "song": null,
                "created_at": "2026-06-29T08:00:00+07:00"
            }
        ],
        "pagination": { "page": 1, "page_size": 20, "total": 2, "total_pages": 1 }
    }
}
```

> Hoạt động **mới nhất nằm trên đầu** (sắp xếp `-created_at`).

**Test Feed rỗng — chưa follow ai:**
> Đăng nhập tài khoản mới chưa follow ai:
```json
{ "success": true, "data": { "items": [], "pagination": { "page": 1, "page_size": 20, "total": 0, "total_pages": 1 } } }
```

**Test Feed không chứa hoạt động của chính mình:**
> Alice tự đặt Mood cho chính mình -> gọi `GET /feed/` -> Mood của Alice **KHÔNG** xuất hiện (Feed chỉ chứa hoạt động của người mình follow, không phải của bản thân).

---

### 10. GET /api/v1/social/me/activities/ — Lịch sử hoạt động của chính tôi

```
Method:  GET
URL:     {{base_url}}/api/v1/social/me/activities/?page=1&page_size=20
Headers: (đang đăng nhập Bob)
```

**Response mong đợi (200):** chỉ chứa hoạt động của **Bob** (người gọi request), khác với `feed/` là hoạt động của người Bob follow.

---

## 6. Test Scenarios — Luồng Kết Hợp

### Scenario A — Luồng đầy đủ theo đúng yêu cầu đề bài: A follow B → B có hoạt động → A thấy trong Feed

```
1.  GET  /api/v1/auth/csrf/                                  -> lay CSRF token
2.  POST /api/v1/auth/login/  (Alice)                         -> dang nhap Alice
3.  POST /api/v1/social/users/{{bob_id}}/follow/               -> Alice follow Bob
4.  GET  /api/v1/social/feed/                                  -> rong, Bob chua co hoat dong
5.  POST /api/v1/auth/login/  (Bob)                            -> dang nhap Bob
6.  POST /api/v1/social/me/mood/                               -> Bob dat Mood
7.  POST /api/v1/music/songs/{{song_id}}/play/                 -> Bob nghe nhac
8.  POST /api/v1/auth/login/  (Alice)                          -> dang nhap lai Alice
9.  GET  /api/v1/social/feed/                                  -> thay CA 2 hoat dong cua Bob
                                                                   (mood + playing), moi nhat truoc
10. POST /api/v1/social/users/{{bob_id}}/follow/               -> Alice unfollow Bob
11. GET  /api/v1/social/feed/                                  -> tro lai rong
```

---

### Scenario B — Test Block Policy ảnh hưởng đến Follow và Feed

```
1.  Dang nhap Bob -> block Alice
2.  Dang nhap Alice -> POST follow Bob -> 403 BLOCKED (khong follow duoc)
3.  (Gia su Alice da follow Bob TRUOC khi bi block)
4.  Bob dang nhap -> block Alice
5.  Alice dang nhap -> GET /feed/ -> hoat dong cua Bob KHONG con xuat hien
    (du Alice van dang "follow" Bob ve mat du lieu - Block Policy uu tien hon)
```

---

### Scenario C — Test Mood Hết Hạn

```
1.  Dat Mood voi duration_hours=1
2.  GET /me/mood/ ngay sau do -> is_expired: false
3.  (Doi 1 gio hoac dung Django shell de sua expires_at ve qua khu)
4.  GET /users/<id>/mood/ -> tra null (Mood het han khong con hien thi cong khai)
5.  GET /me/mood/ (chinh chu) -> van tra du lieu nhung is_expired: true
    (chu so huu van xem duoc Mood cu cua chinh minh, chi an khoi nguoi khac)
```

---

## 7. Bảng Tổng Hợp Checklist

| # | Method | Endpoint | Test Status |
|---|--------|----------|--------------|
| 1 | POST | /api/v1/social/users/<user_id>/follow/ | [ ] |
| 2 | GET | /api/v1/social/users/<user_id>/follow-status/ | [ ] |
| 3 | GET | /api/v1/social/users/<user_id>/followers/ | [ ] |
| 4 | GET | /api/v1/social/users/<user_id>/following/ | [ ] |
| 5 | POST | /api/v1/social/me/mood/ | [ ] |
| 6 | GET | /api/v1/social/me/mood/ | [ ] |
| 7 | GET | /api/v1/social/users/<user_id>/mood/ | [ ] |
| 8 | DELETE | /api/v1/social/me/mood/ | [ ] |
| 9 | GET | /api/v1/social/feed/ | [ ] |
| 10 | GET | /api/v1/social/me/activities/ | [ ] |

> Tick [ ] -> [x] khi đã test thành công từng endpoint, đặc biệt là **Scenario A** (luồng A-follow-B-thấy-Feed) — đây là yêu cầu trọng tâm của Tuần 5.

---

## Lưu Ý Quan Trọng

### Cần 2 tài khoản để test Follow/Feed có ý nghĩa

Khác với các app trước, `social` cần tối thiểu **2 user** tương tác với nhau. Luôn chuẩn bị Alice và Bob (Bước 2-3 ở Mục 2) trước khi bắt đầu test.

### Feed của Tuần 5 đã tự động kết nối với Music của Tuần 2

Gọi `POST /api/v1/music/songs/<id>/play/` (Tuần 2) sẽ **tự động** sinh hoạt động trên Feed mà không cần gọi thêm API nào của `social`. Đây là điểm tích hợp xuyên app quan trọng nhất của Tuần 5 — hãy tận dụng để test Feed có dữ liệu thực tế.

### Session khác nhau khi test 2 tài khoản

Postman dùng cookie jar chung theo domain. Khi đăng nhập Bob, session của Alice bị ghi đè. Test tuần tự theo đúng thứ tự trong Scenario A để tránh nhầm lẫn ai đang "đang đăng nhập" tại mỗi bước.

### Kiểm tra nhanh qua Django Admin

Truy cập `http://localhost:8000/admin/` -> **Xa hoi** -> xem trực tiếp `Follow`, `Mood`, `Hoat dong ban be` để đối chiếu với response API.
