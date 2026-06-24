# 02 — Features & API Chi Tiết App `playlists`

**7 endpoints | Session + CSRF Authentication | Phân quyền Owner nghiêm ngặt**

---

## Mục Lục

1. [Playlist CRUD](#1-playlist-crud)
2. [Playlist Visibility](#2-playlist-visibility)
3. [Playlist Cover Upload](#3-playlist-cover-upload)
4. [Playlist Songs Management](#4-playlist-songs-management)
5. [Bảng tổng hợp tất cả endpoints](#5-bảng-tổng-hợp-tất-cả-endpoints)

---

## 1. Playlist CRUD

### GET /api/v1/playlists/ — Danh sách playlist của tôi

| Thuộc tính | Giá trị |
|---|---|
| **Method** | `GET` |
| **Quyền** | `Auth` |
| **Query params** | `q` (tìm theo title), `page`, `page_size` (max 100) |

**Luồng logic:**
```
PlaylistListView.get
  → validate_list_playlists_params(request.GET)     [validators.py]
  → list_my_playlists(request.user, filters)         [selectors.py]
  → trả JSON
```

> Trả về **cả playlist công khai và riêng tư** của chính user đang đăng nhập — vì đây là trang quản lý cá nhân, không phải trang khám phá công khai.

**Response 200:**
```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": "uuid",
        "title": "Chill Vibes",
        "description": "Nhạc nhẹ nhàng buổi tối",
        "cover_image": "https://res.cloudinary.com/.../covers/playlists/uuid.jpg",
        "is_public": true,
        "owner": { "id": "uuid", "username": "user1", "display_name": "User 1", "avatar": null },
        "song_count": 12,
        "is_owner": true,
        "created_at": "2026-06-20T08:00:00+07:00",
        "updated_at": "2026-06-20T08:00:00+07:00"
      }
    ],
    "pagination": { "page": 1, "page_size": 20, "total": 1, "total_pages": 1 }
  }
}
```

---

### POST /api/v1/playlists/ — Tạo playlist mới

| Thuộc tính | Giá trị |
|---|---|
| **Method** | `POST` |
| **Quyền** | `Auth+CSRF` |
| **Request Body** | JSON |

**Request Body:**
```json
{
  "title": "My Chill Playlist",
  "description": "Nhạc thư giãn cuối tuần",
  "is_public": true
}
```

| Field | Kiểu | Bắt buộc | Mô tả |
|-------|------|----------|-------|
| `title` | string | ✅ | Tên playlist (max 200 ký tự) |
| `description` | string | ❌ | Mô tả (max 1000 ký tự, sanitized XSS) |
| `is_public` | boolean | ❌ | Mặc định `true` |

**Luồng logic:**
```
PlaylistListView.post
  → parse_json_body(request)
  → validate_playlist_create(data)        [validators.py — sanitize title/description]
  → create_playlist(request.user, validated)  [services.py]
  → trả JSON 201
```

**Response 201:**
```json
{
  "success": true,
  "data": {
    "id": "uuid",
    "title": "My Chill Playlist",
    "description": "Nhạc thư giãn cuối tuần",
    "cover_image": null,
    "is_public": true,
    "owner": { "id": "uuid", "username": "currentuser", ... },
    "song_count": 0,
    "is_owner": true,
    "created_at": "...",
    "updated_at": "..."
  }
}
```

**Lỗi 400** nếu thiếu `title`:
```json
{
  "success": false,
  "error": { "code": "VALIDATION_ERROR", "message": "Dữ liệu playlist không hợp lệ",
             "fields": { "title": ["Tên playlist là bắt buộc"] } }
}
```

---

### GET /api/v1/playlists/\<id\>/ — Chi tiết playlist

| Thuộc tính | Giá trị |
|---|---|
| **Method** | `GET` |
| **Quyền** | `Public` (nếu `is_public=True`) hoặc `Owner` (nếu `is_public=False`) |

**Luồng logic:**
```
PlaylistDetailView.get
  → get_playlist_detail(playlist_id, viewer=request.user)   [selectors.py]
    → nếu is_public=False và viewer không phải owner: raise PlaylistNotFound
  → trả JSON
```

> **Quan trọng:** Playlist riêng tư bị người khác truy cập sẽ nhận **404**, không phải 403 — để không tiết lộ rằng playlist này có tồn tại.

**Response 200:** (giống cấu trúc ở trên)

**Response 404** (playlist không tồn tại hoặc bạn không có quyền xem):
```json
{ "success": false, "error": { "code": "NOT_FOUND", "message": "Playlist không tồn tại" } }
```

---

### PATCH /api/v1/playlists/\<id\>/ — Cập nhật playlist

| Thuộc tính | Giá trị |
|---|---|
| **Method** | `PATCH` |
| **Quyền** | `Auth+Owner+CSRF` |
| **Request Body** | JSON, partial update |

**Request Body:**
```json
{ "title": "Tên mới", "description": "Mô tả mới" }
```

**Luồng logic:**
```
PlaylistDetailView.patch
  → get_playlist_by_id(playlist_id)             [selectors.py — KHÔNG check quyền xem]
  → validate_playlist_update(data)                [validators.py]
  → update_playlist(playlist, request.user, validated)  [services.py]
    → nếu request.user không phải owner: raise NotPlaylistOwner (403)
  → trả JSON
```

**Response 200:** trả playlist đã cập nhật.

**Response 403** (không phải owner):
```json
{ "success": false, "error": { "code": "PERMISSION_DENIED",
  "message": "Bạn không có quyền thực hiện hành động này với playlist này" } }
```

---

### DELETE /api/v1/playlists/\<id\>/ — Xóa playlist

| Thuộc tính | Giá trị |
|---|---|
| **Method** | `DELETE` |
| **Quyền** | `Auth+Owner+CSRF` |

**Luồng logic:**
```
PlaylistDetailView.delete
  → get_playlist_by_id(playlist_id)
  → delete_playlist(playlist, request.user)     [services.py]
    → check owner → raise NotPlaylistOwner nếu không phải
    → playlist.delete() → cascade xóa hết PlaylistSong liên quan
  → trả 204 (No Content)
```

**Response 204:** Không có body.

---

## 2. Playlist Visibility

### PATCH /api/v1/playlists/\<id\>/visibility/ — Đặt công khai / riêng tư

| Thuộc tính | Giá trị |
|---|---|
| **Method** | `PATCH` |
| **Quyền** | `Auth+Owner+CSRF` |

**Request Body:**
```json
{ "is_public": false }
```

**Luồng logic:**
```
PlaylistVisibilityView.patch
  → validate_visibility(data)                    [validators.py — bắt buộc đúng kiểu bool]
  → get_playlist_by_id(playlist_id)
  → update_visibility(playlist, request.user, is_public)  [services.py]
  → trả JSON
```

**Response 200:**
```json
{ "success": true, "data": { "is_public": false } }
```

---

## 3. Playlist Cover Upload

### POST /api/v1/playlists/\<id\>/cover/ — Upload ảnh bìa

| Thuộc tính | Giá trị |
|---|---|
| **Method** | `POST` |
| **Quyền** | `Auth+Owner+CSRF` |
| **Request Body** | `multipart/form-data` |

| Field | Kiểu | Bắt buộc | Ràng buộc |
|-------|------|----------|-----------|
| `cover_image` | file | ✅ | JPG/PNG/WEBP, max 5MB |

**Luồng logic:**
```
PlaylistCoverUploadView.post
  → validate_cover_image(request.FILES)          [validators.py — check MIME + size]
  → get_playlist_by_id(playlist_id)
  → update_cover_image(playlist, request.user, file)  [services.py]
    → xóa ảnh cũ trên Cloudinary nếu có (tránh file mồ côi)
    → check owner → raise NotPlaylistOwner nếu không phải
  → trả JSON
```

**Response 200:**
```json
{ "success": true, "data": { "cover_image": "https://res.cloudinary.com/.../covers/playlists/uuid.jpg" } }
```

---

## 4. Playlist Songs Management

### GET /api/v1/playlists/\<id\>/songs/ — Danh sách bài hát trong playlist

| Thuộc tính | Giá trị |
|---|---|
| **Method** | `GET` |
| **Quyền** | `Public` (nếu playlist public) hoặc `Owner` (nếu private) |
| **Query params** | `page`, `page_size` (max 100, default 50) |

**Luồng logic:**
```
PlaylistSongListView.get
  → get_playlist_detail(playlist_id, viewer=request.user)   [check quyền xem playlist]
  → list_playlist_songs(playlist_id, viewer, page, page_size)  [selectors.py]
  → trả JSON
```

**Response 200:**
```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": "uuid",
        "song": {
          "id": "uuid", "title": "Shape of You",
          "artist": { "id": "uuid", "username": "edsheeran", "display_name": "Ed Sheeran" },
          "cover_image": "https://...", "duration": 234, "status": "published"
        },
        "order": 1,
        "added_at": "2026-06-20T08:10:00+07:00"
      }
    ],
    "pagination": { "page": 1, "page_size": 50, "total": 1, "total_pages": 1 }
  }
}
```

---

### POST /api/v1/playlists/\<id\>/songs/ — Thêm bài hát vào playlist

| Thuộc tính | Giá trị |
|---|---|
| **Method** | `POST` |
| **Quyền** | `Auth+Owner+CSRF` |

**Request Body:**
```json
{ "song_id": "uuid-cua-bai-hat" }
```

**Luồng logic:**
```
PlaylistSongListView.post
  → validate_add_song(data)                       [validators.py]
  → get_playlist_by_id(playlist_id)
  → add_song_to_playlist(playlist, request.user, song_id)  [services.py]
    → check owner → raise NotPlaylistOwner nếu không phải   (403)
    → get_song_by_id(song_id) từ music.selectors  → raise SongNotFound nếu không tồn tại  (404)
    → check_song_in_playlist() → raise SongAlreadyInPlaylist nếu đã có  (409)
    → order = get_max_order(playlist_id) + 1       → bài mới luôn vào CUỐI
  → trả JSON 201
```

**Response 201:**
```json
{
  "success": true,
  "data": {
    "id": "uuid",
    "song": { "id": "uuid", "title": "Perfect", "artist": {...}, "duration": 263, "status": "published" },
    "order": 5,
    "added_at": "..."
  }
}
```

**Response 409** (đã có trong playlist):
```json
{ "success": false, "error": { "code": "ALREADY_EXISTS", "message": "Bài hát này đã có trong playlist" } }
```

---

### DELETE /api/v1/playlists/\<id\>/songs/\<song_id\>/ — Xóa bài hát khỏi playlist

| Thuộc tính | Giá trị |
|---|---|
| **Method** | `DELETE` |
| **Quyền** | `Auth+Owner+CSRF` |

**Luồng logic:**
```
PlaylistSongDetailView.delete
  → get_playlist_by_id(playlist_id)
  → remove_song_from_playlist(playlist, request.user, song_id)  [services.py]
    → check owner → raise NotPlaylistOwner nếu không phải   (403)
    → get_playlist_song(playlist_id, song_id) → raise SongNotInPlaylist nếu không có  (404)
    → playlist_song.delete()
  → trả 204 (No Content)
```

**Response 204:** Không có body.

**Response 404** (bài hát không có trong playlist):
```json
{ "success": false, "error": { "code": "NOT_FOUND", "message": "Bài hát không có trong playlist này" } }
```

---

### PATCH /api/v1/playlists/\<id\>/songs/reorder/ — Sắp xếp lại thứ tự

| Thuộc tính | Giá trị |
|---|---|
| **Method** | `PATCH` |
| **Quyền** | `Auth+Owner+CSRF` |

**Request Body:**
```json
{ "song_ids": ["uuid1", "uuid2", "uuid3"] }
```

> `song_ids` phải chứa **chính xác** toàn bộ bài hát hiện có trong playlist theo thứ tự mới mong muốn — không thiếu, không dư.

**Luồng logic:**
```
PlaylistSongReorderView.patch
  → validate_reorder(data)                        [validators.py — kiểm tra format UUID, không trùng]
  → get_playlist_by_id(playlist_id)
  → reorder_playlist_songs(playlist, request.user, song_ids)   [services.py — @transaction.atomic]
    → check owner → raise NotPlaylistOwner nếu không phải   (403)
    → so sánh set(song_ids hiện có) == set(song_ids gửi lên)
      → nếu KHÔNG khớp: raise InvalidReorderData   (400)
    → cập nhật order theo vị trí mới, bulk_update toàn bộ trong 1 transaction
  → trả JSON
```

**Response 200:**
```json
{ "success": true, "message": "Đã cập nhật thứ tự" }
```

**Response 400** (thiếu hoặc dư bài hát so với playlist hiện tại):
```json
{ "success": false, "error": { "code": "VALIDATION_ERROR",
  "message": "Danh sách song_ids phải khớp chính xác với các bài hát hiện có trong playlist" } }
```

---

## 5. Bảng Tổng Hợp Tất Cả Endpoints

| # | Method | Endpoint | Quyền | Mô tả |
|---|--------|----------|-------|-------|
| 1 | GET | `/api/v1/playlists/` | Auth | Danh sách playlist của tôi |
| 2 | POST | `/api/v1/playlists/` | Auth+CSRF | Tạo playlist mới |
| 3 | GET | `/api/v1/playlists/<id>/` | Public/Owner | Chi tiết playlist |
| 4 | PATCH | `/api/v1/playlists/<id>/` | Auth+Owner+CSRF | Cập nhật title/description |
| 5 | DELETE | `/api/v1/playlists/<id>/` | Auth+Owner+CSRF | Xóa playlist |
| 6 | POST | `/api/v1/playlists/<id>/cover/` | Auth+Owner+CSRF | Upload ảnh bìa |
| 7 | PATCH | `/api/v1/playlists/<id>/visibility/` | Auth+Owner+CSRF | Đặt public/private |
| 8 | GET | `/api/v1/playlists/<id>/songs/` | Public/Owner | Danh sách bài hát |
| 9 | POST | `/api/v1/playlists/<id>/songs/` | Auth+Owner+CSRF | Thêm bài hát |
| 10 | DELETE | `/api/v1/playlists/<id>/songs/<song_id>/` | Auth+Owner+CSRF | Xóa bài hát |
| 11 | PATCH | `/api/v1/playlists/<id>/songs/reorder/` | Auth+Owner+CSRF | Sắp xếp lại thứ tự |
