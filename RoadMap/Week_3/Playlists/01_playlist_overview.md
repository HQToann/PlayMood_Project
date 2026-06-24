# 01 — Tổng Quan App `playlists`

**Hệ thống Âm nhạc Django | Tuần 3: App `playlists` — Toàn bộ**

---

## 1. Phạm Vi Công Việc

Tuần 3 tập trung xây dựng hoàn chỉnh app `playlists` — cho phép người dùng tạo và quản lý danh sách phát cá nhân, liên kết với `Song` đã có từ app `music` (Tuần 2).

### Vị trí trong tổng thể dự án

| App | Trạng thái |
|-----|-----------|
| `accounts` (Tuần 1) | ✅ Hoàn thành — 79 tests |
| `music` (Tuần 2) | ✅ Hoàn thành — 164 tests |
| **`playlists` (Tuần 3)** | 🔨 **Tuần này** — 118 tests |
| `artists`, `social`, `notifications`, `search` | ⏳ Chưa làm |

`playlists` chỉ phụ thuộc vào `Song` (đã có sẵn) và `User` (đã có sẵn) → không bị block bởi bất kỳ app nào khác, có thể triển khai ngay và hoàn chỉnh 100% trong tuần này.

---

## 2. Các Module Trong App `playlists`

### 2.1 Playlist — Danh sách phát
- CRUD đầy đủ: tạo, xem, sửa (title/description), xóa
- Upload ảnh bìa riêng lên Cloudinary
- Cơ chế công khai / riêng tư (`is_public`)
- Danh sách playlist của tôi (bao gồm cả private) — tách biệt với danh sách playlist công khai

### 2.2 PlaylistSong — Quản lý bài hát trong Playlist
- Thêm bài hát vào playlist (tự động xếp vào cuối danh sách)
- Xóa bài hát khỏi playlist
- Sắp xếp lại thứ tự bài hát (reorder) — atomic, kiểm tra toàn vẹn dữ liệu
- Xem danh sách bài hát theo đúng thứ tự, có phân trang

---

## 3. Mục Tiêu Nghiệp Vụ Cần Đạt

| # | Mục tiêu | Mô tả |
|---|----------|-------|
| 1 | Tạo playlist | User đăng nhập tạo playlist mới với title, description, is_public |
| 2 | Quản lý bài hát | Thêm/xóa bài hát vào/khỏi playlist, không cho trùng lặp |
| 3 | Sắp xếp thứ tự | Cho phép kéo-thả đổi vị trí bài hát, đảm bảo toàn vẹn (không thiếu/dư bài) |
| 4 | Quyền truy cập | `is_public=True` → ai cũng xem được; `is_public=False` → chỉ owner xem |
| 5 | Phân quyền Owner | Chỉ chủ sở hữu playlist mới được sửa/xóa/thêm bài/sắp xếp lại |
| 6 | Upload ảnh bìa | Owner upload ảnh bìa riêng cho playlist, lưu trên Cloudinary |
| 7 | Bảo mật thông tin | Playlist riêng tư trả về **404** (không phải 403) cho người không có quyền — tránh để lộ sự tồn tại của playlist |

---

## 4. Cấu Trúc Thư Mục App `playlists`

```
playlists/
├── __init__.py
├── apps.py
├── models.py          ← Playlist, PlaylistSong
├── exceptions.py      ← PlaylistNotFound, NotPlaylistOwner,
│                         SongAlreadyInPlaylist, SongNotInPlaylist,
│                         InvalidReorderData
├── validators.py      ← validate_playlist_create, validate_playlist_update,
│                         validate_visibility, validate_add_song,
│                         validate_reorder, validate_cover_image
├── selectors.py       ← get_playlist_by_id, get_playlist_detail,
│                         list_my_playlists, list_public_playlists,
│                         list_playlist_songs, check_song_in_playlist...
├── services.py        ← create_playlist, update_playlist, delete_playlist,
│                         add_song_to_playlist, remove_song_from_playlist,
│                         reorder_playlist_songs (atomic)
├── views.py           ← PlaylistListView, PlaylistDetailView,
│                         PlaylistSongListView, PlaylistSongReorderView...
├── urls.py            ← routes /api/v1/playlists/
├── admin.py
├── tests.py           ← 118 unit tests
└── migrations/
    └── 0001_initial.py
```

---

## 5. Dependency Giữa Các Tầng

```
HTTP Request
    ↓
views.py          ← nhận request, gọi validator, gọi service/selector, trả JSON
    ↓         ↓
validators.py   selectors.py / services.py
                    ↓
                 models.py  ←  DB
                    ↓
              music.models.Song (FK — đã có từ Tuần 2)
              accounts.models.User (FK — đã có từ Tuần 1)
```

**Quy tắc bất di bất dịch (giữ nguyên từ Tuần 1, 2):**
- `views.py` **KHÔNG** import `Playlist`, `PlaylistSong` trực tiếp để query
- `views.py` chỉ import từ `selectors.py`, `services.py`, `validators.py`, `exceptions.py`
- `selectors.py` chỉ đọc (SELECT), không ghi
- `services.py` chỉ ghi (INSERT/UPDATE/DELETE), có thể gọi `selectors.py` và `music.selectors.get_song_by_id()` để xác nhận bài hát tồn tại

---

## 6. Điểm Kỹ Thuật Quan Trọng Cần Lưu Ý

| Vấn đề | Cách giải quyết |
|--------|-----------------|
| **Quyền xem playlist riêng tư** | `get_playlist_detail()` raise `PlaylistNotFound` (404) cho người không phải owner khi `is_public=False` — không dùng 403 để tránh lộ thông tin "playlist này tồn tại nhưng bạn không có quyền" |
| **Thêm bài hát trùng** | `unique_together = [('playlist', 'song')]` ở DB level + check tường minh ở `services.py` → trả `409 ALREADY_EXISTS` |
| **Thứ tự bài hát khi thêm mới** | Luôn lấy `max(order) + 1` — bài mới luôn vào cuối, không cần client tự tính toán thứ tự |
| **Reorder toàn vẹn dữ liệu** | `reorder_playlist_songs()` bắt buộc `song_ids` gửi lên phải khớp **chính xác** (không thiếu, không dư, không ID lạ) với danh sách hiện có trong playlist — nếu không khớp, raise `InvalidReorderData` (400). Dùng `@transaction.atomic` để đảm bảo cập nhật order là toàn-hoặc-không |
| **Xóa playlist** | Cascade tự động xóa toàn bộ `PlaylistSong` liên quan (FK `on_delete=CASCADE`) |
| **Ảnh bìa Playlist** | Lưu trên Cloudinary theo path `covers/playlists/<uuid>.<ext>` (đúng quy ước §12.3), tự xóa file cũ khi upload ảnh mới |

---

## 7. Kế Hoạch Thực Thi (Đã Hoàn Thành & Verify)

```
✅ models.py        — Playlist, PlaylistSong với to_dict()
✅ exceptions.py     — 5 custom exception
✅ validators.py     — 6 validator functions
✅ selectors.py      — 10 selector functions
✅ services.py       — 8 service functions (bao gồm reorder atomic)
✅ views.py          — 7 View classes, 10 HTTP methods
✅ urls.py           — 7 endpoints
✅ admin.py          — Django Admin với inline PlaylistSong
✅ migrations        — 0001_initial.py đã apply thành công
✅ tests.py          — 118 test cases, 100% PASS
✅ Full regression   — 361/361 tests pass (accounts + music + playlists)
```
