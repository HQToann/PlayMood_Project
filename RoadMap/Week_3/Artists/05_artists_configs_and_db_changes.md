# 05 — Cấu Hình & Thay Đổi Database App `artists`

**Settings, URLs, Migration, CLI Commands — Đã verify chạy thành công**

---

## Mục Lục

1. [Thay đổi settings.py](#1-thay-đổi-settingspy)
2. [Thay đổi urls.py gốc](#2-thay-đổi-urlspy-gốc)
3. [Thay đổi Database — Model mới](#3-thay-đổi-database--model-mới)
4. [CLI Commands — Thứ tự thực hiện](#4-cli-commands--thứ-tự-thực-hiện)
5. [Kiểm tra sau khi apply](#5-kiểm-tra-sau-khi-apply)
6. [Lưu ý quan trọng](#6-lưu-ý-quan-trọng)

---

## 1. Thay Đổi settings.py

M�� file `music_platform/settings.py`, tìm phần `INSTALLED_APPS` và thêm `'artists'`:

```python
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Third-party
    'corsheaders',
    'cloudinary',
    'cloudinary_storage',

    # Noi bo - Tuan 1, 2, 3
    'accounts',
    'music',
    'playlists',

    # Noi bo - Tuan 4 (THEM MOI)
    'artists',

    # Cac app sau se them dan theo tuan:
    # 'social',
    # 'notifications',
    # 'search',
]
```

> Không cần thêm config Cloudinary mới — app `artists` dùng lại `CLOUDINARY_STORAGE` và `DEFAULT_FILE_STORAGE` đã cấu hình sẵn từ Tuần 1/2/3. Ảnh bìa nghệ sĩ tự động lưu theo path `covers/artists/<uuid>.<ext>` nhờ `upload_to` đã khai báo trong `models.py`.

---

## 2. Thay Đổi urls.py Gốc

M�� file `music_platform/urls.py`, thêm route cho app `artists`:

```python
urlpatterns = [
    path('admin/', admin.site.urls),

    # Tuan 1
    path('api/v1/auth/',      include('accounts.auth_urls')),
    path('api/v1/accounts/',  include('accounts.urls')),

    # Tuan 2
    path('api/v1/music/',     include('music.urls')),

    # Tuan 3
    path('api/v1/playlists/', include('playlists.urls')),

    # Tuan 4 - THEM MOI
    path('api/v1/artists/',   include('artists.urls')),

    # Cac tuan sau (mo dan):
    # path('api/v1/social/',        include('social.urls')),
    # path('api/v1/notifications/', include('notifications.urls')),
    # path('api/v1/search/',        include('search.urls')),
]
```

---

## 3. Thay Đổi Database — Model Mới

### 3.1 Bảng sẽ được tạo

| Tên bảng | Model | Mô tả |
|----------|-------|-------|
| `artists_artist_profile` | `ArtistProfile` | Hồ sơ nghệ sĩ mở rộng — 1-1 với `accounts_user` |

**Tổng: 1 bảng mới**

> Lưu ý: app `artists` **không tạo thêm bảng nào khác** vì toàn bộ thống kê được tính trực tiếp từ các bảng đã có ở app `music` (`music_song`, `music_like`, `music_rating`, `music_comment`, `music_listen_history`) — không lưu cache số liệu riêng.

---

### 3.2 Schema chi tiết (PostgreSQL — Production)

#### `artists_artist_profile`

```sql
CREATE TABLE "artists_artist_profile" (
    "id"           uuid NOT NULL PRIMARY KEY,
    "user_id"      uuid NOT NULL UNIQUE REFERENCES "accounts_user"("id") ON DELETE CASCADE,
    "stage_name"   varchar(100) NOT NULL DEFAULT '',
    "bio"          text NOT NULL DEFAULT '',
    "cover_image"  varchar(100) NULL,
    "website_url"  varchar(255) NOT NULL DEFAULT '',
    "facebook_url" varchar(255) NOT NULL DEFAULT '',
    "youtube_url"  varchar(255) NOT NULL DEFAULT '',
    "created_at"   timestamp with time zone NOT NULL,
    "updated_at"   timestamp with time zone NOT NULL
);
-- Indexes:
CREATE UNIQUE INDEX ON "artists_artist_profile" ("user_id");   -- tu dong tu OneToOneField
```

> **Lưu ý:** `user_id` có `UNIQUE` constraint vì `ArtistProfile.user` là `OneToOneField` — mỗi `User` chỉ có tối đa 1 `ArtistProfile`. `ON DELETE CASCADE` đảm bảo xóa `User` sẽ tự xóa `ArtistProfile` liên quan.

---

### 3.3 Constraints quan trọng

| Bảng | Constraint | Mô tả |
|------|-----------|-------|
| `artists_artist_profile` | `UNIQUE(user_id)` | Mỗi user chỉ có 1 hồ sơ nghệ sĩ (OneToOneField) |

---

## 4. CLI Commands — Thứ Tự Thực Hiện

Thực hiện theo đúng thứ tự sau trong terminal tại thư mục gốc project:

### Bước 1 — Tạo thư mục app `artists`

```bash
# Windows PowerShell
mkdir artists
mkdir artists\migrations
New-Item artists\__init__.py -ItemType File
New-Item artists\migrations\__init__.py -ItemType File
New-Item artists\apps.py -ItemType File
New-Item artists\models.py -ItemType File
New-Item artists\exceptions.py -ItemType File
New-Item artists\validators.py -ItemType File
New-Item artists\selectors.py -ItemType File
New-Item artists\services.py -ItemType File
New-Item artists\views.py -ItemType File
New-Item artists\urls.py -ItemType File
New-Item artists\admin.py -ItemType File
New-Item artists\tests.py -ItemType File
```

```bash
# Linux / macOS
mkdir -p artists/migrations
touch artists/__init__.py
touch artists/migrations/__init__.py
touch artists/apps.py artists/models.py artists/exceptions.py
touch artists/validators.py artists/selectors.py artists/services.py
touch artists/views.py artists/urls.py artists/admin.py artists/tests.py
```

### Bước 2 — Copy source code

Copy nội dung từng file trong `03_artists_source_code.md` vào file tương ứng.

### Bước 3 — Thêm 'artists' vào INSTALLED_APPS

Sửa `music_platform/settings.py` như hướng dẫn ở Mục 1.

### Bước 4 — Thêm route vào urls.py gốc

Sửa `music_platform/urls.py` như hướng dẫn ở Mục 2.

### Bước 5 — Kiểm tra cấu hình

```bash
python manage.py check
```

Kết quả mong đợi:
```
System check identified no issues (0 silenced).
```

### Bước 6 — Tạo migration

```bash
python manage.py makemigrations artists
```

Kết quả mong đợi:
```
Migrations for 'artists':
  artists/migrations/0001_initial.py
    + Create model ArtistProfile
```

### Bước 7 — Xem trước SQL (tùy chọn, để kiểm tra)

```bash
python manage.py sqlmigrate artists 0001
```

### Bước 8 — Áp dụng migration

```bash
python manage.py migrate
```

Kết quả mong đợi:
```
Operations to perform:
  Apply all migrations: accounts, admin, artists, auth, contenttypes, music, playlists, sessions

Running migrations:
  Applying artists.0001_initial... OK
```

### Bước 9 — Chạy tests

```bash
# Chỉ test app artists
python manage.py test artists --verbosity=2

# Chạy toàn bộ (Tuần 1+2+3+4) để đảm bảo không phá vỡ gì
python manage.py test accounts music playlists artists --verbosity=2
```

**Kết quả đã verify thực tế khi xây dựng:**
```
Ran 73 tests in 80.417s
OK
```
```
Ran 92 tests in 100.419s   (accounts + music + playlists + artists, baseline rút gọn)
OK
```

### Bước 10 — Khởi động server và kiểm tra

```bash
python manage.py runserver 8000
```

Test nhanh bằng curl:
```bash
# Kiểm tra route đã đăng ký (200, list rỗng nếu chưa có nghệ sĩ)
curl http://localhost:8000/api/v1/artists/
```

---

## 5. Kiểm Tra Sau Khi Apply

### 5.1 Kiểm tra bảng trong Database

```bash
python manage.py dbshell
```

```sql
-- Xem bảng artists
\dt artists_*

-- Ket qua mong doi:
--  artists_artist_profile

-- Kiem tra cau truc bang
\d artists_artist_profile

-- Thoat
\q
```

### 5.2 Kiểm tra URLs đã đăng ký

```bash
python manage.py shell -c "
from django.urls import reverse
import uuid
fake_id = uuid.uuid4()
tests = [
    ('artist-list',       {}),
    ('artist-me',         {}),
    ('artist-me-cover',   {}),
    ('artist-me-stats',   {}),
    ('artist-detail',     {'user_id': fake_id}),
    ('artist-stats',      {'user_id': fake_id}),
]
for name, kwargs in tests:
    try:
        url = reverse(name, kwargs=kwargs)
        print(f'OK: {name} -> {url}')
    except Exception as e:
        print(f'FAIL: {name} -> {e}')
"
```

### 5.3 Checklist cuối Tuần 4

```
[ ] artists/ thu muc da tao du 11 file
[ ] 'artists' da co trong INSTALLED_APPS
[ ] path('api/v1/artists/', ...) da co trong urls.py goc
[ ] python manage.py check -> 0 issues
[ ] python manage.py makemigrations artists -> 0001_initial.py
[ ] python manage.py migrate -> OK
[ ] \dt artists_* -> 1 bang
[ ] curl /api/v1/artists/ -> 200 (list rong)
[ ] python manage.py test artists -> 73 tests PASS
[ ] python manage.py test accounts music playlists artists -> tat ca PASS
[ ] Django Admin: /admin/ -> thay "Nghe si" (ArtistProfile)
```

---

## 6. Lưu Ý Quan Trọng

### 6.1 Dependency vào app music và accounts

`artists/selectors.py` có dòng import:
```python
from music.models import Song, Like, Rating, Comment, ListenHistory
```

Điều này **bắt buộc** app `music` phải nằm **trước** `artists` trong `INSTALLED_APPS`, và migration của `music` phải apply **trước** migration của `artists`. Vì thứ tự triển khai đã tuần tự theo tuần (music ở Tuần 2, artists ở Tuần 4), Django tự xử lý đúng dependency này.

### 6.2 ArtistProfile KHÔNG lưu cache thống kê

Khác với cách một số hệ thống lưu sẵn các trường như `total_likes`, `total_plays` ngay trong bảng profile rồi update dần, app này **chủ động không làm vậy**. Mọi số liệu trong `GET /me/stats/` và `GET /<id>/stats/` được tính **trực tiếp** từ dữ liệu thật tại thời điểm gọi API. Lý do:
- Tránh rủi ro số liệu lệch (out-of-sync) khi quên cập nhật cache ở một luồng nghiệp vụ nào đó
- Đơn giản hóa logic — không cần signal/celery task để đồng bộ cache
- Đánh đổi: tốn thêm vài query mỗi lần gọi `/stats/` — chấp nhận được ở quy mô hiện tại, có thể tối ưu bằng cache tầng ứng dụng (Redis) ở Tuần 8 nếu cần.

### 6.3 Tự động tạo ArtistProfile khi truy cập lần đầu

`GET /api/v1/artists/me/` gọi `get_or_create_my_profile()` — nếu user có `role='artist'` nhưng chưa từng tạo `ArtistProfile`, hệ thống tự tạo một bản ghi rỗng. Điều này khác với `POST /me/` (raise lỗi 409 nếu đã tồn tại). Hai luồng này được thiết kế để frontend có thể gọi `GET /me/` ngay sau khi user được duyệt thành artist (qua `ArtistVerification` ở Tuần 1) mà không cần thêm bước "khởi tạo hồ sơ" riêng.

### 6.4 Avatar/Bio cơ bản vẫn dùng chung User, không trùng lặp

`ArtistProfile` **không** có trường `avatar` hay `display_name` riêng — các trường này vẫn lấy từ `accounts.User` (Tuần 1) qua `self.user.avatar`, `self.user.get_display_name()`. `ArtistProfile` chỉ thêm các trường **đặc thù cho trang nghệ sĩ công khai**: `stage_name`, `cover_image` riêng, và social links. Điều này tránh trùng lặp dữ liệu giữa 2 bảng.

### 6.5 Test dùng SQLite, Production dùng PostgreSQL

Schema SQL ở Mục 3.2 là cú pháp **PostgreSQL** (dùng cho production thật theo `.env` đã cấu hình `DB_*`). Khi chạy `python manage.py test`, Django tự dùng SQLite in-memory — đây là hành vi bình thường, không phải lỗi.
