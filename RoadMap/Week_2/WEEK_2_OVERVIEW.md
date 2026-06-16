# 01 — Tổng Quan Tuần 2

**Hệ thống Âm nhạc Django | Tuần 2: App `music` — Toàn bộ**

---

## 1. Phạm Vi Công Việc

Tuần 2 tập trung hoàn thiện **toàn bộ app `music`** — xương sống nghiệp vụ của hệ thống. Đây là app phức tạp nhất, chứa nhiều quy tắc nghiệp vụ quan trọng được định nghĩa trong tài liệu kiến trúc.

### Apps được phát triển

| App | Trạng thái | Ghi chú |
|-----|-----------|---------|
| `accounts` | ✅ Hoàn thành (Tuần 1) | Không thay đổi |
| `music` | 🔨 **Tuần này** | Toàn bộ từ models đến views |

---

## 2. Các Module Trong App `music`

### 2.1 Genre — Thể loại nhạc
- CRUD thể loại (Admin quản lý, Public xem)
- Slug tự động từ tên thể loại

### 2.2 Song — Bài hát
- Upload audio (mp3/flac/wav/ogg) + ảnh bìa lên Cloudinary
- Workflow trạng thái: `draft` → `published` → `hidden`
- Filter đa chiều: genre, artist, status, ordering
- Phân trang chuẩn

### 2.3 Play / ListenHistory — Lượt nghe
- Atomic increment `play_count` bằng `F()` expression **(Fix R1)**
- Chống spam dedup 5 phút **(Fix R8)**
- Log `FriendActivity` khi nghe nhạc

### 2.4 Download — Tải nhạc **(Fix R2)**
- Chỉ cho phép khi `allow_download=True` và `status=published`
- Trả redirect signed URL (Cloudinary) hoặc FileResponse (dev)

### 2.5 Like — Yêu thích bài hát
- Toggle like/unlike (idempotent)
- Đếm số lượt thích real-time

### 2.6 Rating — Đánh giá
- Upsert rating 1–5 sao (mỗi user 1 rating/bài)
- Tính điểm trung bình

### 2.7 Comment — Bình luận
- Bình luận gốc + trả lời (threaded, max 1 cấp)
- Block check trước khi comment **(Fix R10)**
- Xóa bình luận của mình
- Toggle like bình luận

### 2.8 Report — Báo cáo vi phạm
- Báo cáo song / comment / user
- Admin xem và xử lý báo cáo

### 2.9 Admin endpoints
- Ẩn/hiện bài hát
- Bật/tắt trending
- Ẩn bình luận vi phạm
- Xử lý báo cáo

---

## 3. Mục Tiêu Kỹ Thuật Cần Đạt

| # | Mục tiêu | Fix tương ứng |
|---|----------|--------------|
| 1 | `play_count` dùng `F()` expression — không race condition | Fix R1 |
| 2 | Endpoint download với signed URL Cloudinary | Fix R2 |
| 3 | MIME validation audio trước khi upload | Fix R5 |
| 4 | dedup 5 phút cho ListenHistory | Fix R8 |
| 5 | Endpoint publish bài hát (draft→published) | Fix R9 |
| 6 | Block check: ẩn bài hát của người đã block | Fix R10 |
| 7 | XSS sanitize cho lyrics, title, description | Fix R12 |
| 8 | Tuân thủ phân tầng: views không gọi model trực tiếp | §1.2 |
| 9 | Tất cả file upload lên Cloudinary, không lưu local | §12.3 |
| 10 | Phân trang chuẩn cho mọi list API | §3.5 |

---

## 4. Cấu Trúc Thư Mục App `music`

```
music/
├── __init__.py
├── apps.py
├── models.py          ← Genre, Song, Like, Rating, Comment,
│                         CommentLike, ListenHistory, Report
├── exceptions.py      ← MusicException, SongNotPublished, DownloadNotAllowed...
├── validators.py      ← validate_song_create, validate_comment, validate_report...
├── selectors.py       ← list_songs, get_song_by_id, list_comments...
├── services.py        ← create_song, record_play (F()), toggle_like...
├── views.py           ← GenreView, SongView, PlayView, LikeView...
├── urls.py            ← tất cả routes /api/v1/music/
├── admin.py
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
```

**Quy tắc bất di bất dịch:**
- `views.py` **KHÔNG** import `Song`, `Comment`, `Genre`... trực tiếp để query
- `views.py` chỉ import từ `selectors.py`, `services.py`, `validators.py`, `exceptions.py`
- `selectors.py` chỉ đọc (SELECT), không ghi
- `services.py` chỉ ghi (INSERT/UPDATE/DELETE), có thể gọi selectors

---

## 6. Điểm Khác Biệt So Với Tuần 1

| Tuần 1 (`accounts`) | Tuần 2 (`music`) |
|---------------------|-----------------|
| Auth/Session flow | File upload (audio + ảnh) |
| Không có file upload | Cloudinary upload bắt buộc |
| Counter đơn giản | Atomic F() counter |
| Không có threading | Comment threaded (parent/reply) |
| Block policy cơ bản | Block policy áp dụng vào content |

---

## 7. Kế Hoạch Thực Thi

```
Ngày 1–2:  models.py, exceptions.py, migrations
Ngày 3:    validators.py (bao gồm MIME validation audio)
Ngày 4:    selectors.py (queries, pagination, filter)
Ngày 5:    services.py (upload Cloudinary, F() counter, dedup)
Ngày 6:    views.py + urls.py (tất cả endpoints)
Ngày 7:    tests.py + WEEK_2_GUIDE.md
```
