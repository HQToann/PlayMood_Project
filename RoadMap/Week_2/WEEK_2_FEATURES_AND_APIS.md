# 02 — Features & API Chi Tiết Tuần 2

**App `music` — Toàn bộ endpoints, request/response, luồng logic**

---

## Mục Lục

1. [Genre — Thể loại nhạc](#1-genre--thể-loại-nhạc)
2. [Song — Bài hát](#2-song--bài-hát)
3. [Play & Download](#3-play--download)
4. [Like — Yêu thích](#4-like--yêu-thích)
5. [Rating — Đánh giá](#5-rating--đánh-giá)
6. [Comment — Bình luận](#6-comment--bình-luận)
7. [ListenHistory — Lịch sử nghe](#7-listenhistory--lịch-sử-nghe)
8. [Report — Báo cáo vi phạm](#8-report--báo-cáo-vi-phạm)
9. [Admin Endpoints](#9-admin-endpoints)

---

## 1. Genre — Thể Loại Nhạc

### Danh sách endpoints

| Method | Endpoint | Quyền | Mô tả |
|--------|----------|-------|-------|
| `GET` | `/api/v1/music/genres/` | Public | Danh sách tất cả thể loại |
| `POST` | `/api/v1/music/genres/` | Admin+CSRF | Tạo thể loại mới |
| `PUT` | `/api/v1/music/genres/<id>/` | Admin+CSRF | Cập nhật thể loại |
| `DELETE` | `/api/v1/music/genres/<id>/` | Admin+CSRF | Xóa thể loại |

---

### GET /api/v1/music/genres/

**Luồng:** `GenreListView.get` → `list_genres()` selector

**Response 200:**
```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": "uuid",
        "name": "Pop",
        "slug": "pop",
        "description": "Nhạc pop",
        "song_count": 42
      }
    ],
    "total": 10
  }
}
```

---

### POST /api/v1/music/genres/

**Luồng:** `GenreListView.post` → `validate_genre(data)` → `create_genre(data)` service

**Request Body (JSON):**
```json
{
  "name": "R&B",
  "description": "Rhythm and Blues"
}
```

**Response 201:**
```json
{
  "success": true,
  "data": { "id": "uuid", "name": "R&B", "slug": "r-b", "description": "..." }
}
```

**Lỗi 409** nếu tên đã tồn tại.

---

### PUT /api/v1/music/genres/<id>/

**Luồng:** `GenreDetailView.put` → `validate_genre(data)` → `update_genre(genre, data)` service

**Request Body (JSON):**
```json
{ "name": "R&B Soul", "description": "Cập nhật mô tả" }
```

---

### DELETE /api/v1/music/genres/<id>/

**Luồng:** `GenreDetailView.delete` → `get_genre_by_id(id)` → `delete_genre(genre)` service

**Response 204:** (no content)

**Lỗi 400** nếu genre đang có bài hát liên kết.

---

## 2. Song — Bài Hát

### Danh sách endpoints

| Method | Endpoint | Quyền | Mô tả |
|--------|----------|-------|-------|
| `GET` | `/api/v1/music/songs/` | Public | Danh sách bài hát (filter + phân trang) |
| `POST` | `/api/v1/music/songs/` | Artist+CSRF | Upload bài hát mới |
| `GET` | `/api/v1/music/songs/trending/` | Public | Danh sách bài hát trending |
| `GET` | `/api/v1/music/songs/<id>/` | Public | Chi tiết bài hát |
| `PATCH` | `/api/v1/music/songs/<id>/` | Artist+Owner+CSRF | Cập nhật thông tin |
| `DELETE` | `/api/v1/music/songs/<id>/` | Artist+Owner+CSRF | Xóa bài hát |
| `POST` | `/api/v1/music/songs/<id>/publish/` | Artist+Owner+CSRF | Phát hành (draft→published) |
| `POST` | `/api/v1/music/songs/<id>/hide/` | Artist+Owner+CSRF | Ẩn bài hát |

---

### GET /api/v1/music/songs/

**Luồng:** `SongListView.get` → `list_songs(filters, viewer)` selector

**Query params:**

| Param | Mô tả | Ví dụ |
|-------|-------|-------|
| `q` | Tìm theo tên | `q=shape` |
| `genre` | Lọc theo slug thể loại | `genre=pop` |
| `artist_id` | Lọc theo nghệ sĩ | `artist_id=uuid` |
| `ordering` | Sắp xếp | `ordering=-play_count` |
| `page` | Trang | `page=2` |
| `page_size` | Kích thước trang (max 100) | `page_size=20` |

**Lưu ý:** `list_songs` tự động:
- Chỉ trả `status=published` cho người dùng thường/anonymous
- Ẩn bài hát của người đã block viewer **(Fix R10)**
- Artist xem được `draft` bài của chính mình

**Response 200:**
```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": "uuid",
        "title": "Shape of You",
        "artist": { "id": "uuid", "username": "edsheeran", "display_name": "Ed Sheeran" },
        "genre": { "id": "uuid", "name": "Pop", "slug": "pop" },
        "cover_image": "https://res.cloudinary.com/...",
        "duration": 234,
        "play_count": 15420,
        "like_count": 320,
        "avg_rating": 4.3,
        "status": "published",
        "is_trending": true,
        "allow_download": false,
        "released_at": "2024-01-15T00:00:00+07:00",
        "created_at": "2024-01-10T08:00:00+07:00"
      }
    ],
    "pagination": {
      "page": 1,
      "page_size": 20,
      "total": 150,
      "total_pages": 8
    }
  }
}
```

---

### POST /api/v1/music/songs/ — Upload bài hát

**Luồng:**
`SongListView.post`
→ `validate_song_create(data, files)` validator (MIME check audio *Fix R5*)
→ `create_song(artist, validated)` service (upload Cloudinary)
→ trả `201`

**Request:** `multipart/form-data`

| Field | Kiểu | Bắt buộc | Mô tả |
|-------|------|----------|-------|
| `title` | string | ✅ | Tên bài hát (max 200 ký tự) |
| `genre_id` | UUID | ✅ | ID thể loại |
| `audio_file` | file | ✅ | mp3/flac/wav/ogg/mp4, max 50MB |
| `cover_image` | file | ❌ | jpg/png/webp, max 5MB |
| `lyrics` | string | ❌ | Lời bài hát (sanitized XSS) |
| `duration` | integer | ✅ | Thời lượng (giây) |
| `allow_download` | boolean | ❌ | Cho phép tải (default: false) |
| `released_at` | datetime | ❌ | Ngày phát hành dự kiến |

**Response 201:**
```json
{
  "success": true,
  "data": {
    "id": "uuid",
    "title": "My Song",
    "status": "draft",
    "audio_file": "https://res.cloudinary.com/.../audio/uuid.mp3",
    "cover_image": "https://res.cloudinary.com/.../covers/uuid.jpg",
    "artist": { "id": "uuid", "display_name": "Artist Name" },
    "genre": { "id": "uuid", "name": "Pop" },
    "duration": 234,
    "allow_download": false,
    "created_at": "2024-06-11T08:00:00+07:00"
  }
}
```

**Lỗi 400** nếu MIME audio sai hoặc quá 50MB:
```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Dữ liệu không hợp lệ",
    "fields": {
      "audio_file": ["Chỉ chấp nhận: audio/mpeg, audio/flac, audio/wav, audio/ogg, audio/mp4"]
    }
  }
}
```

---

### GET /api/v1/music/songs/<id>/ — Chi tiết bài hát

**Luồng:** `SongDetailView.get` → `get_song_detail(song_id, viewer)` selector

Selector tự động:
- Raise `NotFound` nếu song không tồn tại hoặc `hidden`
- Raise `NotFound` nếu viewer bị artist block **(Fix R10)**
- Kèm `like_count`, `avg_rating`, `is_liked` (nếu đã đăng nhập)

**Response 200:**
```json
{
  "success": true,
  "data": {
    "id": "uuid",
    "title": "Shape of You",
    "artist": { "id": "uuid", "username": "edsheeran", "display_name": "Ed Sheeran" },
    "genre": { "id": "uuid", "name": "Pop", "slug": "pop" },
    "audio_file": "https://res.cloudinary.com/...",
    "cover_image": "https://res.cloudinary.com/...",
    "lyrics": "The club isn't the best place...",
    "duration": 234,
    "play_count": 15420,
    "like_count": 320,
    "avg_rating": 4.3,
    "rating_count": 89,
    "is_liked": true,
    "my_rating": 5,
    "status": "published",
    "is_trending": true,
    "allow_download": true,
    "released_at": "2024-01-15T00:00:00+07:00",
    "created_at": "2024-01-10T08:00:00+07:00"
  }
}
```

---

### POST /api/v1/music/songs/<id>/publish/ *(Fix R9)*

**Luồng:** `SongPublishView.post` → `get_song_by_id(id)` → `publish_song(song, artist)` service

Business rules:
- Chỉ owner (artist của bài) mới publish được
- Bài phải ở trạng thái `draft`
- Sau publish: `status=published`, `released_at=now()` nếu chưa có

**Response 200:**
```json
{
  "success": true,
  "data": {
    "id": "uuid",
    "status": "published",
    "released_at": "2024-06-11T10:30:00+07:00"
  }
}
```

**Lỗi 403** nếu không phải owner.
**Lỗi 400** nếu bài không ở trạng thái `draft`.

---

### POST /api/v1/music/songs/<id>/hide/

**Luồng:** `SongHideView.post` → `hide_song(song, artist)` service

Chỉ owner mới ẩn được. Đổi `status=hidden`.

---

### PATCH /api/v1/music/songs/<id>/

**Luồng:** `SongDetailView.patch` → `validate_song_update(data, files)` → `update_song(song, artist, data)` service

**Request Body (JSON hoặc multipart nếu có file):**
```json
{
  "title": "New Title",
  "lyrics": "Updated lyrics",
  "allow_download": true
}
```

---

### DELETE /api/v1/music/songs/<id>/

Xóa bài hát và file trên Cloudinary. Chỉ owner mới xóa được.

**Response 204** (no content)

---

## 3. Play & Download

### POST /api/v1/music/songs/<id>/play/

**Luồng:** `SongPlayView.post` → `record_play(user, song)` service

Service `record_play` thực hiện:
1. Kiểm tra `ListenHistory` trong 5 phút gần nhất — nếu đã có: return (không làm gì)
2. `Song.objects.filter(id=song.id).update(play_count=F('play_count') + 1)` **(Fix R1)**
3. `ListenHistory.objects.create(user=user, song=song)`
4. Gọi `create_friend_activity(...)` (wrapped trong try/except)

**Request Body:** (không cần body)

**Response 200:**
```json
{
  "success": true,
  "data": { "play_count": 15421 }
}
```

---

### GET /api/v1/music/songs/<id>/download/ *(Fix R2)*

**Luồng:** `SongDownloadView.get` → `get_song_by_id(id)` selector → trả file/URL

Business rules:
- Song phải `status=published`
- Song phải `allow_download=True`
- User phải đăng nhập (Auth)
- Trả Cloudinary signed URL (redirect) hoặc FileResponse (dev)

**Response 200:**
```json
{
  "success": true,
  "data": {
    "download_url": "https://res.cloudinary.com/signed_url...",
    "filename": "Shape-of-You.mp3",
    "expires_in": 300
  }
}
```

**Lỗi 403:**
```json
{
  "success": false,
  "error": { "code": "DOWNLOAD_NOT_ALLOWED", "message": "Bài hát này không cho phép tải về" }
}
```

---

## 4. Like — Yêu Thích

| Method | Endpoint | Quyền | Mô tả |
|--------|----------|-------|-------|
| `POST` | `/api/v1/music/songs/<id>/like/` | Auth+CSRF | Toggle like/unlike |
| `GET` | `/api/v1/music/songs/<id>/likes/` | Public | Số lượt thích |

---

### POST /api/v1/music/songs/<id>/like/ — Toggle

**Luồng:** `SongLikeView.post` → `toggle_like(user, song)` service

Service dùng `get_or_create` + delete:
- Nếu chưa like → tạo `Like` record → trả `{'action': 'liked'}`
- Nếu đã like → xóa `Like` record → trả `{'action': 'unliked'}`

**Response 200:**
```json
{
  "success": true,
  "data": {
    "action": "liked",
    "like_count": 321
  }
}
```

---

### GET /api/v1/music/songs/<id>/likes/

**Luồng:** `SongLikeView.get` → `get_song_like_count(song_id)` selector

**Response 200:**
```json
{
  "success": true,
  "data": { "like_count": 321, "is_liked": true }
}
```

---

## 5. Rating — Đánh Giá

| Method | Endpoint | Quyền | Mô tả |
|--------|----------|-------|-------|
| `POST` | `/api/v1/music/songs/<id>/rate/` | Auth+CSRF | Đánh giá (upsert) |
| `GET` | `/api/v1/music/songs/<id>/rating/` | Public | Điểm trung bình |

---

### POST /api/v1/music/songs/<id>/rate/

**Luồng:** `SongRatingView.post` → `validate_rating(data)` → `upsert_rating(user, song, score)` service

Dùng `update_or_create` — mỗi user chỉ có 1 rating/bài, gửi lại sẽ cập nhật.

**Request Body (JSON):**
```json
{ "score": 5 }
```

**Response 200:**
```json
{
  "success": true,
  "data": {
    "score": 5,
    "avg_rating": 4.4,
    "rating_count": 90
  }
}
```

**Lỗi 400** nếu score không phải 1–5.

---

### GET /api/v1/music/songs/<id>/rating/

**Luồng:** `SongRatingView.get` → `get_song_rating_stats(song_id)` selector

**Response 200:**
```json
{
  "success": true,
  "data": {
    "avg_rating": 4.4,
    "rating_count": 90,
    "my_rating": 5
  }
}
```

---

## 6. Comment — Bình Luận

| Method | Endpoint | Quyền | Mô tả |
|--------|----------|-------|-------|
| `GET` | `/api/v1/music/songs/<id>/comments/` | Public | Danh sách bình luận |
| `POST` | `/api/v1/music/songs/<id>/comments/` | Auth+CSRF | Thêm bình luận / trả lời |
| `DELETE` | `/api/v1/music/comments/<id>/` | Auth+Owner+CSRF | Xóa bình luận của mình |
| `POST` | `/api/v1/music/comments/<id>/like/` | Auth+CSRF | Toggle like bình luận |

---

### GET /api/v1/music/songs/<id>/comments/

**Luồng:** `SongCommentListView.get` → `list_comments(song_id, viewer, page)` selector

Selector chỉ trả:
- `is_hidden=False`
- Comment gốc (`parent=None`) kèm replies

**Query params:** `page`, `page_size`

**Response 200:**
```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": "uuid",
        "user": { "id": "uuid", "username": "user1", "display_name": "User 1", "avatar": null },
        "content": "Bài hát hay quá!",
        "like_count": 5,
        "is_liked": false,
        "parent_id": null,
        "replies": [
          {
            "id": "uuid",
            "user": { "id": "uuid", "username": "user2", "display_name": "User 2", "avatar": null },
            "content": "Đồng ý!",
            "like_count": 1,
            "is_liked": false,
            "created_at": "2024-06-11T09:00:00+07:00"
          }
        ],
        "created_at": "2024-06-11T08:00:00+07:00"
      }
    ],
    "pagination": { "page": 1, "page_size": 20, "total": 45, "total_pages": 3 }
  }
}
```

---

### POST /api/v1/music/songs/<id>/comments/

**Luồng:**
`SongCommentListView.post`
→ `validate_comment(data)` validator
→ block check: `is_blocked(viewer_id, song.artist_id)` **(Fix R10)**
→ `create_comment(user, song, data)` service

Business rules:
- Nếu viewer bị artist block → `403 BLOCKED`
- `parent_id` phải là comment của cùng bài hát (nếu có)
- Max 1 cấp reply (không reply của reply)
- Content sanitized XSS **(Fix R12)**

**Request Body (JSON):**
```json
{
  "content": "Bài hát hay quá!",
  "parent_id": null
}
```

**Trả lời bình luận:**
```json
{
  "content": "Đồng ý với bạn!",
  "parent_id": "uuid-của-comment-gốc"
}
```

**Response 201:**
```json
{
  "success": true,
  "data": {
    "id": "uuid",
    "content": "Bài hát hay quá!",
    "user": { "id": "uuid", "username": "user1" },
    "parent_id": null,
    "created_at": "2024-06-11T08:00:00+07:00"
  }
}
```

---

### DELETE /api/v1/music/comments/<id>/

**Luồng:** `CommentDetailView.delete` → `get_comment_by_id(id)` → `delete_comment(comment, user)` service

Chỉ owner mới xóa được bình luận của mình. Admin dùng endpoint riêng để hide.

**Response 204** (no content)

---

### POST /api/v1/music/comments/<id>/like/

**Luồng:** `CommentLikeView.post` → `toggle_comment_like(user, comment)` service

Toggle: đã like → unlike, chưa like → like.

**Response 200:**
```json
{
  "success": true,
  "data": { "action": "liked", "like_count": 6 }
}
```

---

## 7. ListenHistory — Lịch Sử Nghe

| Method | Endpoint | Quyền | Mô tả |
|--------|----------|-------|-------|
| `GET` | `/api/v1/music/me/history/` | Auth | Lịch sử nghe của tôi |
| `DELETE` | `/api/v1/music/me/history/` | Auth+CSRF | Xóa toàn bộ lịch sử |

---

### GET /api/v1/music/me/history/

**Luồng:** `ListenHistoryView.get` → `list_listen_history(user, page)` selector

**Query params:** `page`, `page_size`

**Response 200:**
```json
{
  "success": true,
  "data": {
    "items": [
      {
        "song": {
          "id": "uuid",
          "title": "Shape of You",
          "artist": { "display_name": "Ed Sheeran" },
          "cover_image": "https://...",
          "duration": 234
        },
        "listened_at": "2024-06-11T10:00:00+07:00"
      }
    ],
    "pagination": { "page": 1, "page_size": 20, "total": 100, "total_pages": 5 }
  }
}
```

---

### DELETE /api/v1/music/me/history/

Xóa toàn bộ lịch sử nghe của user đang đăng nhập.

**Response 204** (no content)

---

## 8. Report — Báo Cáo Vi Phạm

| Method | Endpoint | Quyền | Mô tả |
|--------|----------|-------|-------|
| `POST` | `/api/v1/music/reports/` | Auth+CSRF | Gửi báo cáo |
| `GET` | `/api/v1/music/admin/reports/` | Admin | Danh sách báo cáo |
| `POST` | `/api/v1/music/admin/reports/<id>/resolve/` | Admin+CSRF | Xử lý báo cáo |

---

### POST /api/v1/music/reports/

**Luồng:** `ReportCreateView.post` → `validate_report(data)` → `create_report(reporter, data)` service

**Request Body (JSON):**

| Field | Giá trị | Mô tả |
|-------|---------|-------|
| `target_type` | `"song"` / `"comment"` / `"user"` | Loại đối tượng |
| `target_id` | UUID | ID đối tượng bị báo cáo |
| `reason` | string | Lý do (copyright, spam, offensive, other) |
| `description` | string (optional) | Mô tả chi tiết |

```json
{
  "target_type": "song",
  "target_id": "uuid",
  "reason": "copyright",
  "description": "Bài hát vi phạm bản quyền của..."
}
```

**Response 201:**
```json
{
  "success": true,
  "data": { "id": "uuid", "status": "pending", "created_at": "..." }
}
```

---

### GET /api/v1/music/admin/reports/

**Luồng:** `AdminReportListView.get` → `list_reports(filters)` selector

**Query params:** `status` (pending/resolved/dismissed), `target_type`, `page`

**Response 200:**
```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": "uuid",
        "reporter": { "id": "uuid", "username": "user1" },
        "target_type": "song",
        "target_id": "uuid",
        "reason": "copyright",
        "description": "...",
        "status": "pending",
        "created_at": "..."
      }
    ],
    "pagination": { "page": 1, "page_size": 20, "total": 5, "total_pages": 1 }
  }
}
```

---

### POST /api/v1/music/admin/reports/<id>/resolve/

**Luồng:** `AdminReportResolveView.post` → `resolve_report(report, admin, action)` service

**Request Body (JSON):**
```json
{
  "action": "resolved",
  "note": "Đã xử lý - xóa bài hát vi phạm"
}
```

`action`: `"resolved"` hoặc `"dismissed"`

**Response 200:**
```json
{
  "success": true,
  "data": { "id": "uuid", "status": "resolved", "resolved_by": "admin_uuid" }
}
```

---

## 9. Admin Endpoints

| Method | Endpoint | Quyền | Mô tả |
|--------|----------|-------|-------|
| `POST` | `/api/v1/music/admin/songs/<id>/trending/` | Admin+CSRF | Bật/tắt trending |
| `POST` | `/api/v1/music/admin/songs/<id>/hide/` | Admin+CSRF | Admin ẩn bài hát vi phạm |
| `POST` | `/api/v1/music/admin/comments/<id>/hide/` | Admin+CSRF | Admin ẩn bình luận vi phạm |

---

### POST /api/v1/music/admin/songs/<id>/trending/

Toggle `is_trending` flag.

**Response 200:**
```json
{
  "success": true,
  "data": { "id": "uuid", "is_trending": true }
}
```

---

### POST /api/v1/music/admin/songs/<id>/hide/

Admin ẩn bài hát vi phạm. Đổi `status=hidden`.

**Response 200:**
```json
{
  "success": true,
  "data": { "id": "uuid", "status": "hidden" }
}
```

---

### POST /api/v1/music/admin/comments/<id>/hide/

Admin ẩn bình luận vi phạm. Đổi `is_hidden=True`.

**Response 200:**
```json
{
  "success": true,
  "data": { "id": "uuid", "is_hidden": true }
}
```

---

## 10. Bảng Tóm Tắt Tất Cả Endpoints

| Method | Endpoint | Quyền |
|--------|----------|-------|
| GET | `/api/v1/music/genres/` | Public |
| POST | `/api/v1/music/genres/` | Admin |
| PUT | `/api/v1/music/genres/<id>/` | Admin |
| DELETE | `/api/v1/music/genres/<id>/` | Admin |
| GET | `/api/v1/music/songs/` | Public |
| POST | `/api/v1/music/songs/` | Artist |
| GET | `/api/v1/music/songs/trending/` | Public |
| GET | `/api/v1/music/songs/<id>/` | Public |
| PATCH | `/api/v1/music/songs/<id>/` | Artist+Owner |
| DELETE | `/api/v1/music/songs/<id>/` | Artist+Owner |
| POST | `/api/v1/music/songs/<id>/publish/` | Artist+Owner |
| POST | `/api/v1/music/songs/<id>/hide/` | Artist+Owner |
| POST | `/api/v1/music/songs/<id>/play/` | Auth |
| GET | `/api/v1/music/songs/<id>/download/` | Auth |
| POST | `/api/v1/music/songs/<id>/like/` | Auth |
| GET | `/api/v1/music/songs/<id>/likes/` | Public |
| POST | `/api/v1/music/songs/<id>/rate/` | Auth |
| GET | `/api/v1/music/songs/<id>/rating/` | Public |
| GET | `/api/v1/music/songs/<id>/comments/` | Public |
| POST | `/api/v1/music/songs/<id>/comments/` | Auth |
| DELETE | `/api/v1/music/comments/<id>/` | Auth+Owner |
| POST | `/api/v1/music/comments/<id>/like/` | Auth |
| GET | `/api/v1/music/me/history/` | Auth |
| DELETE | `/api/v1/music/me/history/` | Auth |
| POST | `/api/v1/music/reports/` | Auth |
| GET | `/api/v1/music/admin/reports/` | Admin |
| POST | `/api/v1/music/admin/reports/<id>/resolve/` | Admin |
| POST | `/api/v1/music/admin/songs/<id>/trending/` | Admin |
| POST | `/api/v1/music/admin/songs/<id>/hide/` | Admin |
| POST | `/api/v1/music/admin/comments/<id>/hide/` | Admin |
