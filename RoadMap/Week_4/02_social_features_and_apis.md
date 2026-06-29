# 02 — Features & API Chi Tiết App `social`

**8 endpoints | Session + CSRF Authentication | Trọng tâm: Feed tối ưu N+1**

---

## Mục Lục

1. [Follow](#1-follow)
2. [Mood](#2-mood)
3. [Feed](#3-feed)
4. [Bảng tổng hợp tất cả endpoints](#4-bảng-tổng-hợp-tất-cả-endpoints)

---

## 1. Follow

### POST /api/v1/social/users/\<user_id\>/follow/ — Toggle Follow/Unfollow

| Thuộc tính | Giá trị |
|---|---|
| **Method** | `POST` |
| **Quyền** | `Auth+CSRF` |

**Luồng logic:**
```
FollowToggleView.post
  -> toggle_follow(request.user, user_id)     [services.py]
     -> neu user_id == request.user.id: raise CannotFollowSelf (400)
     -> neu user_id khong ton tai: raise FollowTargetNotFound (404)
     -> neu bi target block: raise BlockedFollowError (403) - Fix R10
     -> get_or_create Follow:
        - chua co -> tao moi, ghi FriendActivity, tra action='followed'
        - da co    -> xoa, tra action='unfollowed'
  -> tra JSON
```

**Response 200 (lần đầu — followed):**
```json
{ "success": true, "data": { "action": "followed", "followers_count": 5, "target_user_id": "uuid" } }
```

**Response 200 (lần thứ 2 — unfollowed):**
```json
{ "success": true, "data": { "action": "unfollowed", "followers_count": 4, "target_user_id": "uuid" } }
```

**Response 400** (tự follow bản thân):
```json
{ "success": false, "error": { "code": "VALIDATION_ERROR", "message": "Ban khong the tu theo doi ban than" } }
```

**Response 403** (bị target block):
```json
{ "success": false, "error": { "code": "BLOCKED", "message": "Ban khong the thuc hien hanh dong nay" } }
```

---

### GET /api/v1/social/users/\<user_id\>/follow-status/ — Trạng thái Follow + Số lượng

| Thuộc tính | Giá trị |
|---|---|
| **Method** | `GET` |
| **Quyền** | `Public` |

**Luồng logic:**
```
FollowStatusView.get
  -> get_follow_counts(user_id)               [selectors.py]
  -> is_following(viewer.id, user_id)          [selectors.py - chi tinh neu da dang nhap]
  -> tra JSON gop ca 2 ket qua
```

**Response 200:**
```json
{ "success": true, "data": { "followers_count": 120, "following_count": 45, "is_following": true } }
```

> `is_following` luôn `false` nếu chưa đăng nhập (không raise lỗi, vì endpoint này là Public).

---

### GET /api/v1/social/users/\<user_id\>/followers/ — Danh sách Followers

| Thuộc tính | Giá trị |
|---|---|
| **Method** | `GET` |
| **Quyền** | `Public` |
| **Query params** | `page`, `page_size` (max 100) |

**Luồng logic:**
```
FollowersListView.get
  -> validate_list_follow_params(request.GET)   [validators.py]
  -> list_followers(user_id, viewer, page, page_size)   [selectors.py]
     -> an nguoi da block viewer (Fix R10)
  -> tra JSON
```

**Response 200:**
```json
{
  "success": true,
  "data": {
    "items": [
      { "id": "uuid", "username": "user1", "display_name": "User 1", "avatar": null, "followed_at": "2026-06-29T08:00:00+07:00" }
    ],
    "pagination": { "page": 1, "page_size": 20, "total": 1, "total_pages": 1 }
  }
}
```

---

### GET /api/v1/social/users/\<user_id\>/following/ — Danh sách Following

| Thuộc tính | Giá trị |
|---|---|
| **Method** | `GET` |
| **Quyền** | `Public` |
| **Query params** | `page`, `page_size` (max 100) |

**Luồng logic:** giống `followers/` nhưng đảo hướng — lấy danh sách người `user_id` đang theo dõi.

**Response 200:** cấu trúc giống `followers/`.

---

## 2. Mood

### GET /api/v1/social/me/mood/ — Xem Mood hiện tại của tôi

| Thuộc tính | Giá trị |
|---|---|
| **Method** | `GET` |
| **Quyền** | `Auth` |

**Luồng logic:**
```
MyMoodView.get
  -> get_my_mood(request.user)     [selectors.py]
     -> raise MoodNotFound neu chua tung thiet lap (404)
  -> tra JSON
```

**Response 200:**
```json
{
  "success": true,
  "data": {
    "id": "uuid",
    "user": { "id": "uuid", "username": "myuser", "display_name": "My User", "avatar": null },
    "status_text": "Dang nghe nhac chill cuoi tuan",
    "song": { "id": "uuid", "title": "Track One", "artist_display_name": "DJ Cool", "cover_image": null },
    "expires_at": "2026-06-30T08:00:00+07:00",
    "is_expired": false,
    "created_at": "2026-06-29T08:00:00+07:00",
    "updated_at": "2026-06-29T08:00:00+07:00"
  }
}
```

---

### POST /api/v1/social/me/mood/ — Thiết lập/Cập nhật Mood

| Thuộc tính | Giá trị |
|---|---|
| **Method** | `POST` |
| **Quyền** | `Auth+CSRF` |
| **Request Body** | JSON |

**Request Body:**
```json
{
  "status_text": "Dang nghe nhac chill cuoi tuan",
  "song_id": "uuid-cua-bai-hat",
  "duration_hours": 24
}
```

| Field | Kiểu | Bắt buộc | Ràng buộc |
|-------|------|----------|-----------|
| `status_text` | string | Có | max 200 ký tự, sanitized XSS |
| `song_id` | string (UUID) | Không | bài hát đính kèm, nếu có phải tồn tại |
| `duration_hours` | integer | Không | 1–168 giờ (mặc định 24) |

**Luồng logic:**
```
MyMoodView.post
  -> parse_json_body(request)
  -> validate_set_mood(data)        [validators.py - TINH expires_at tu duration_hours,
                                      KHONG nhan truc tiep tu client]
  -> set_mood(request.user, validated)   [services.py]
     -> kiem tra song_id ton tai neu co -> raise NotFound (404) neu khong
     -> update_or_create Mood (UPSERT - thay the Mood cu, khong tao moi)
     -> ghi 1 FriendActivity loai 'mood'
  -> tra JSON 201
```

**Response 201:** giống cấu trúc GET ở trên với data mới.

**Response 400** (status_text rỗng):
```json
{ "success": false, "error": { "code": "VALIDATION_ERROR", "fields": { "status_text": ["Trang thai la bat buoc"] } } }
```

**Response 400** (duration_hours ngoài khoảng 1–168):
```json
{ "success": false, "error": { "fields": { "duration_hours": ["Thoi gian hien thi phai tu 1 den 168 gio"] } } }
```

---

### DELETE /api/v1/social/me/mood/ — Xóa Mood hiện tại

| Thuộc tính | Giá trị |
|---|---|
| **Method** | `DELETE` |
| **Quyền** | `Auth+CSRF` |

**Luồng logic:**
```
MyMoodView.delete
  -> delete_mood(request.user)     [services.py]
  -> tra 204 (No Content)
```

---

### GET /api/v1/social/users/\<user_id\>/mood/ — Xem Mood công khai

| Thuộc tính | Giá trị |
|---|---|
| **Method** | `GET` |
| **Quyền** | `Public` |

**Luồng logic:**
```
UserMoodView.get
  -> get_user_mood(user_id, viewer=request.user)   [selectors.py]
     -> tra None neu: chua co Mood / da het han / viewer bi user block (Fix R10)
     -> KHONG raise exception - Mood la thong tin phu
  -> tra JSON (data co the la null)
```

**Response 200 (có Mood):** giống cấu trúc Mood object ở Mục 2.

**Response 200 (không có Mood/đã hết hạn/bị block):**
```json
{ "success": true, "data": null }
```

---

## 3. Feed

### GET /api/v1/social/feed/ — Bảng tin hoạt động

| Thuộc tính | Giá trị |
|---|---|
| **Method** | `GET` |
| **Quyền** | `Auth` |
| **Query params** | `page`, `page_size` (max 100) |

**Luồng logic:**
```
FeedView.get
  -> validate_list_feed_params(request.GET)    [validators.py]
  -> list_feed(request.user, page, page_size)   [selectors.py]
  -> tra JSON
```

**Logic gom nhóm/sắp xếp của `list_feed()` (chi tiết):**

```
Buoc 1: Lay danh sach user_id ma request.user dang FOLLOW
        (following_ids = Follow.objects.filter(follower=user).values_list('following_id'))

Buoc 2: Lay danh sach user_id da BLOCK request.user (Fix R10)
        (blocked_ids = BlockList.objects.filter(blocked_id=user.id).values_list('blocker_id'))

Buoc 3: Query FriendActivity:
        - filter(user_id__in=following_ids)   -- CHI hoat dong cua nguoi dang follow
        - exclude(user_id__in=blocked_ids)     -- LOAI TRU hoat dong cua nguoi da block minh
        - select_related('user', 'song', 'song__artist')  -- TOI UU N+1 (xem Muc 6 file 01)
        - order_by('-created_at')              -- KHONG gom nhom theo loai/user, hien thi
                                                   dang timeline don gian, moi nhat len dau

Buoc 4: Phan trang chuan (page, page_size), serialize tung activity qua to_dict()
```

> **Không gom nhóm theo người dùng hay theo loại hoạt động** ở phiên bản này — Feed hiển thị dạng timeline tuyến tính đơn giản (giống Twitter/X feed cơ bản), mỗi `FriendActivity` là 1 item độc lập. Việc gom nhóm "Bob đã nghe 5 bài hát" thành 1 dòng duy nhất có thể bổ sung ở giai đoạn tối ưu UX sau.

**Response 200:**
```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": "uuid",
        "user": { "id": "uuid", "username": "bob", "display_name": "Bob", "avatar": null },
        "activity_type": "playing",
        "extra_text": "",
        "song": { "id": "uuid", "title": "Shape of You", "artist_display_name": "Ed Sheeran", "cover_image": null },
        "created_at": "2026-06-29T08:30:00+07:00"
      },
      {
        "id": "uuid",
        "user": { "id": "uuid", "username": "bob", "display_name": "Bob", "avatar": null },
        "activity_type": "mood",
        "extra_text": "Dang nghe nhac chill",
        "song": null,
        "created_at": "2026-06-29T08:00:00+07:00"
      }
    ],
    "pagination": { "page": 1, "page_size": 20, "total": 2, "total_pages": 1 }
  }
}
```

---

### GET /api/v1/social/me/activities/ — Lịch sử hoạt động của chính tôi

| Thuộc tính | Giá trị |
|---|---|
| **Method** | `GET` |
| **Quyền** | `Auth` |
| **Query params** | `page`, `page_size` (max 100) |

**Luồng logic:**
```
MyActivitiesView.get
  -> validate_list_feed_params(request.GET)
  -> list_my_activities(request.user, page, page_size)   [selectors.py]
     -> filter(user=request.user) - CHI hoat dong cua chinh nguoi goi,
        khac voi list_feed() la lay hoat dong cua nguoi MINH FOLLOW
  -> tra JSON
```

**Response 200:** cấu trúc giống `feed/` nhưng chỉ chứa hoạt động của chính `request.user`.

---

## 4. Bảng Tổng Hợp Tất Cả Endpoints

| # | Method | Endpoint | Quyền |
|---|--------|----------|-------|
| 1 | POST | `/api/v1/social/users/<user_id>/follow/` | Auth+CSRF |
| 2 | GET | `/api/v1/social/users/<user_id>/follow-status/` | Public |
| 3 | GET | `/api/v1/social/users/<user_id>/followers/` | Public |
| 4 | GET | `/api/v1/social/users/<user_id>/following/` | Public |
| 5 | GET | `/api/v1/social/me/mood/` | Auth |
| 6 | POST | `/api/v1/social/me/mood/` | Auth+CSRF |
| 7 | DELETE | `/api/v1/social/me/mood/` | Auth+CSRF |
| 8 | GET | `/api/v1/social/users/<user_id>/mood/` | Public |
| 9 | GET | `/api/v1/social/feed/` | Auth |
| 10 | GET | `/api/v1/social/me/activities/` | Auth |
