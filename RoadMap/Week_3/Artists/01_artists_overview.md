# 01 — Tổng Quan App `artists`

**Hệ thống Âm nhạc Django | Tuần 4: App `artists` — Toàn bộ**

---

## 1. Phạm Vi Công Việc

Tuần 4 tập trung xây dựng hoàn chỉnh app `artists` — quản lý hồ sơ nghệ sĩ mở rộng và tính toán thống kê tổng hợp từ dữ liệu đã có ở app `music` (Tuần 2).

### Vị trí trong tổng thể dự án

| App | Trạng thái |
|-----|-----------|
| `accounts` (Tuần 1) | Hoàn thành |
| `music` (Tuần 2) | Hoàn thành |
| `playlists` (Tuần 3) | Hoàn thành |
| **`artists` (Tuần 4)** | **Tuần này — 73 tests** |
| `social`, `notifications`, `search` | Chưa làm |

`artists` phụ thuộc vào `User` (đã có) và đọc dữ liệu tổng hợp từ `Song`, `Like`, `Rating`, `Comment`, `ListenHistory` (tất cả đã có từ Tuần 2) — không bị block bởi bất kỳ app nào khác.

---

## 2. Các Module Trong App `artists`

### 2.1 ArtistProfile — Hồ sơ nghệ sĩ mở rộng
- Hồ sơ riêng cho user có `role='artist'`, tách biệt với `User` cơ bản (Tuần 1)
- Các trường riêng: `stage_name` (tên nghệ danh), `bio` riêng, `cover_image` riêng, social links
- Tự động tạo hồ sơ rỗng khi artist truy cập lần đầu (không bắt buộc phải POST trước)
- Upload ảnh bìa lên Cloudinary

### 2.2 Artist Stats — Thống kê tổng hợp
- Tính toán **real-time** từ các bảng đã có, không lưu cache riêng
- 7 chỉ số: tổng số bài hát, tổng lượt nghe, tổng lượt thích, tổng bình luận, số người nghe duy nhất, điểm đánh giá trung bình, số lượt đánh giá
- Top 10 bài hát theo lượt nghe

### 2.3 Artist Discovery — Khám phá nghệ sĩ
- Danh sách nghệ sĩ công khai, tìm kiếm theo tên nghệ danh/username
- Trang cá nhân nghệ sĩ công khai (Public)

---

## 3. Mục Tiêu Nghiệp Vụ Cần Đạt

| # | Mục tiêu | Mô tả |
|---|----------|-------|
| 1 | Tạo/lấy hồ sơ nghệ sĩ | Artist tạo `ArtistProfile` hoặc tự động có hồ sơ rỗng khi truy cập lần đầu |
| 2 | Cập nhật hồ sơ | Artist sửa `stage_name`, `bio`, social links — chỉ owner |
| 3 | Upload ảnh bìa | Artist upload `cover_image` riêng lên Cloudinary — chỉ owner |
| 4 | Tính thống kê chính xác | Stats tính từ dữ liệu thật của `music`, không lệch, không cache lỗi thời |
| 5 | Phân quyền role Artist | Mọi action ghi đều yêu cầu `role='artist'` qua `@require_artist` |
| 6 | Phân quyền Owner | Chỉ chính nghệ sĩ đó mới sửa được hồ sơ/ảnh bìa của mình |
| 7 | Bảo mật thông tin | Hồ sơ nghệ sĩ bị block trả về **404** — áp dụng đúng Fix R10 nhất quán với Tuần 1-3 |
| 8 | Stats chỉ tính trên nội dung published | Bài `draft`/`hidden` không được tính vào thống kê công khai |

---

## 4. Cấu Trúc Thư Mục App `artists`

```
artists/
├── __init__.py
├── apps.py
├── models.py          <- ArtistProfile
├── exceptions.py      <- ArtistProfileNotFound, ArtistProfileAlreadyExists,
│                          NotArtistProfileOwner, UserNotArtist
├── validators.py      <- validate_artist_profile_create/update,
│                          validate_cover_image, validate_list_artists_params
├── selectors.py        <- get_artist_profile_detail, list_artists,
│                          get_artist_stats (trong tam), list_artist_top_songs
├── services.py         <- create_artist_profile, update_artist_profile,
│                          update_cover_image, get_or_create_my_profile
├── views.py            <- ArtistListView, MyArtistProfileView,
│                          MyArtistStatsView, ArtistDetailView, ArtistStatsView
├── urls.py             <- routes /api/v1/artists/
├── admin.py
├── tests.py            <- 73 unit tests
└── migrations/
    └── 0001_initial.py
```

---

## 5. Dependency Giữa Các Tầng

```
HTTP Request
    |
views.py          <- nhan request, goi validator, goi service/selector, tra JSON
    |         |
validators.py   selectors.py / services.py
                    |
                 models.py  <-  DB (ArtistProfile)
                    |
              music.models (Song, Like, Rating, Comment, ListenHistory)
              -- artists/selectors.py DOC tu cac bang nay de tinh stats,
                 KHONG ghi/sua doi du lieu cua app music
              accounts.models.User (1-1 voi ArtistProfile)
```

**Quy tắc bất di bất dịch (giữ nguyên từ Tuần 1-3):**
- `views.py` **KHÔNG** import `ArtistProfile`, `Song`, `Like`... trực tiếp để query
- `views.py` chỉ import từ `selectors.py`, `services.py`, `validators.py`, `exceptions.py`
- `selectors.py` chỉ đọc (SELECT), không ghi — bao gồm cả khi đọc xuyên app (`music.models`)
- `services.py` chỉ ghi (INSERT/UPDATE) lên `ArtistProfile`, **không bao giờ ghi** lên bảng của app `music`

---

## 6. Điểm Kỹ Thuật Quan Trọng Cần Lưu Ý

| Vấn đề | Cách giải quyết |
|--------|-----------------|
| **Stats tính real-time, không cache** | `get_artist_stats()` query trực tiếp `Sum`, `Count`, `Avg` từ `Song`/`Like`/`Rating`/`Comment`/`ListenHistory` mỗi lần gọi — đảm bảo số liệu luôn đúng 100% với dữ liệu hiện tại, đánh đổi một chút hiệu năng cho sự đơn giản và đúng đắn ở giai đoạn này |
| **total_play_count dùng Sum không phải Count** | Đây là tổng `play_count` của tất cả bài hát (cộng dồn), không phải số lượng bài hát — dễ nhầm nên có test case riêng phân biệt 2 khái niệm |
| **total_listeners đếm unique** | Dùng `.values('user_id').distinct().count()` trên `ListenHistory` — một người nghe nhiều bài/nhiều lần chỉ tính 1 lần |
| **Stats chỉ tính trên bài `published`** | Mọi query trong `get_artist_stats()` đều filter `song__status=Song.STATUS_PUBLISHED` — bài `draft`/`hidden` không lộ vào thống kê công khai dù `play_count` > 0 |
| **Tự động tạo hồ sơ rỗng** | `get_or_create_my_profile()` trong services.py — artist không bị bắt phải gọi `POST` trước khi xem được `GET /me/` của chính họ |
| **Quyền xem hồ sơ bị block** | `get_artist_profile_detail()` raise `ArtistProfileNotFound` (404) cho viewer bị nghệ sĩ block — nhất quán với cách `accounts` và `music` đã làm ở Tuần 1, 2 (Fix R10) |
| **ArtistProfile là OneToOneField** | Đảm bảo mỗi `User` chỉ có tối đa 1 `ArtistProfile`, DB tự chặn tạo trùng ở constraint level |
| **Sanitize URL cho social links** | `website_url`, `facebook_url`, `youtube_url` đều qua `sanitize_url()` — chỉ chấp nhận `http://`/`https://`, raise lỗi nếu sai |

---

## 7. Kế Hoạch Thực Thi (Đã Hoàn Thành & Verify)

```
[x] models.py        - ArtistProfile voi to_dict()
[x] exceptions.py     - 4 custom exception
[x] validators.py     - 4 validator functions
[x] selectors.py      - 7 selector functions (trong tam: get_artist_stats)
[x] services.py       - 4 service functions
[x] views.py          - 6 View classes, 8 HTTP methods
[x] urls.py           - 6 endpoints
[x] admin.py          - Django Admin
[x] migrations        - 0001_initial.py da apply thanh cong
[x] tests.py          - 73 test cases, 100% PASS
[x] Full regression   - 92/92 tests pass (accounts + music + playlists + artists)
```
