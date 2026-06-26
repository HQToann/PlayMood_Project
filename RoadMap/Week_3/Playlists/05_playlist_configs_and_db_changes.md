# 05 — Cấu Hình & Thay Đổi Database App `playlists`

**Settings, URLs, Migration, CLI Commands — Đã verify chạy thành công**

---

## Mục Lục

1. [Thay đổi settings.py](#1-thay-đổi-settingspy)
2. [Thay đổi urls.py gốc](#2-thay-đổi-urlspy-gốc)
3. [Thay đổi Database — Models mới](#3-thay-đổi-database--models-mới)
4. [CLI Commands — Thứ tự thực hiện](#4-cli-commands--thứ-tự-thực-hiện)
5. [Kiểm tra sau khi apply](#5-kiểm-tra-sau-khi-apply)
6. [Lưu ý quan trọng](#6-lưu-ý-quan-trọng)

---

## 1. Thay Đổi settings.py

M�� file `music_platform/settings.py`, tìm phần `INSTALLED_APPS` và thêm `'playlists'`:

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

    # Noi bo - Tuan 1, 2
    'accounts',
    'music',

    # Noi bo - Tuan 3 (THEM MOI)
    'playlists',

    # Cac app sau se them dan theo tuan:
    # 'artists',
    # 'social',
    # 'notifications',
    # 'search',
]
```

> Không cần thêm config Cloudinary mới — app `playlists` dùng lại `CLOUDINARY_STORAGE` và `DEFAULT_FILE_STORAGE` đã cấu hình sẵn từ Tuần 1/2. Ảnh bìa playlist tự động lưu theo path `covers/playlists/<uuid>.<ext>` nhờ `upload_to` đã khai báo trong `models.py`.

---

## 2. Thay Đổi urls.py Gốc

M�� file `music_platform/urls.py`, thêm route cho app `playlists`:

```python
urlpatterns = [
    path('admin/', admin.site.urls),

    # Tuan 1
    path('api/v1/auth/',      include('accounts.auth_urls')),
    path('api/v1/accounts/',  include('accounts.urls')),

    # Tuan 2
    path('api/v1/music/',     include('music.urls')),

    # Tuan 3 - THEM MOI
    path('api/v1/playlists/', include('playlists.urls')),

    # Cac tuan sau (mo dan):
    # path('api/v1/artists/',       include('artists.urls')),
    # path('api/v1/social/',        include('social.urls')),
    # path('api/v1/notifications/', include('notifications.urls')),
    # path('api/v1/search/',        include('search.urls')),
]
```

---

## 3. Thay Đổi Database — Models Mới

### 3.1 Các bảng sẽ được tạo

| Tên bảng | Model | Mô tả |
|----------|-------|-------|
| `playlists_playlist` | `Playlist` | Danh sách phát do người dùng tạo |
| `playlists_playlist_song` | `PlaylistSong` | Bảng trung gian Playlist <-> Song, có thứ tự |

**Tổng: 2 bảng mới**

---

### 3.2 Schema chi tiết (PostgreSQL — Production)

#### `playlists_playlist`

```sql
CREATE TABLE "playlists_playlist" (
    "id"          uuid NOT NULL PRIMARY KEY,
    "owner_id"    uuid NOT NULL REFERENCES "accounts_user"("id"),
    "title"       varchar(200) NOT NULL,
    "description" text NOT NULL DEFAULT '',
    "cover_image" varchar(100) NULL,
    "is_public"   boolean NOT NULL DEFAULT true,
    "created_at"  timestamp with time zone NOT NULL,
    "updated_at"  timestamp with time zone NOT NULL
);
-- Indexes:
CREATE INDEX ON "playlists_playlist" ("owner_id");
CREATE INDEX ON "playlists_playlist" ("is_public");
```

#### `playlists_playlist_song`

```sql
CREATE TABLE "playlists_playlist_song" (
    "id"          uuid NOT NULL PRIMARY KEY,
    "playlist_id" uuid NOT NULL REFERENCES "playlists_playlist"("id") ON DELETE CASCADE,
    "song_id"     uuid NOT NULL REFERENCES "music_song"("id") ON DELETE CASCADE,
    "order"       integer NOT NULL DEFAULT 0 CHECK ("order" >= 0),
    "added_at"    timestamp with time zone NOT NULL
);
-- Indexes:
CREATE INDEX ON "playlists_playlist_song" ("playlist_id");
CREATE INDEX ON "playlists_playlist_song" ("song_id");
CREATE UNIQUE INDEX "playlists_playlist_song_playlist_id_song_id_uniq"
    ON "playlists_playlist_song" ("playlist_id", "song_id");
```

> **Lưu ý:** `ON DELETE CASCADE` trên cả `playlist_id` và `song_id` đảm bảo:
> - Xóa Playlist -> tự xóa toàn bộ PlaylistSong liên quan
> - Xóa Song (từ app music) -> tự xóa khỏi mọi playlist đang chứa bài đó

---

### 3.3 Constraints quan trọng

| Bảng | Constraint | Mô tả |
|------|-----------|-------|
| `playlists_playlist_song` | `UNIQUE(playlist_id, song_id)` | Mỗi bài hát chỉ xuất hiện 1 lần trong 1 playlist |
| `playlists_playlist_song` | `CHECK(order >= 0)` | Order không được âm |

---

## 4. CLI Commands — Thứ Tự Thực Hiện

Thực hiện theo đúng thứ tự sau trong terminal tại thư mục gốc project:

### Bước 1 — Tạo thư mục app `playlists`

```bash
# Windows PowerShell
mkdir playlists
mkdir playlists\migrations
New-Item playlists\__init__.py -ItemType File
New-Item playlists\migrations\__init__.py -ItemType File
New-Item playlists\apps.py -ItemType File
New-Item playlists\models.py -ItemType File
New-Item playlists\exceptions.py -ItemType File
New-Item playlists\validators.py -ItemType File
New-Item playlists\selectors.py -ItemType File
New-Item playlists\services.py -ItemType File
New-Item playlists\views.py -ItemType File
New-Item playlists\urls.py -ItemType File
New-Item playlists\admin.py -ItemType File
New-Item playlists\tests.py -ItemType File
```

```bash
# Linux / macOS
mkdir -p playlists/migrations
touch playlists/__init__.py
touch playlists/migrations/__init__.py
touch playlists/apps.py playlists/models.py playlists/exceptions.py
touch playlists/validators.py playlists/selectors.py playlists/services.py
touch playlists/views.py playlists/urls.py playlists/admin.py playlists/tests.py
```

### Bước 2 — Copy source code

Copy nội dung từng file trong `03_playlist_source_code.md` vào file tương ứng.

### Bước 3 — Thêm 'playlists' vào INSTALLED_APPS

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
python manage.py makemigrations playlists
```

Kết quả mong đợi:
```
Migrations for 'playlists':
  playlists/migrations/0001_initial.py
    + Create model Playlist
    + Create model PlaylistSong
```

### Bước 7 — Xem trước SQL (tùy chọn, để kiểm tra)

```bash
python manage.py sqlmigrate playlists 0001
```

### Bước 8 — Áp dụng migration

```bash
python manage.py migrate
```

Kết quả mong đợi:
```
Operations to perform:
  Apply all migrations: accounts, admin, auth, contenttypes, music, playlists, sessions

Running migrations:
  Applying playlists.0001_initial... OK
```

### Bước 9 — Chạy tests

```bash
# Chỉ test app playlists
python manage.py test playlists --verbosity=2

# Chạy toàn bộ (Tuần 1 + 2 + 3) để đảm bảo không phá vỡ gì
python manage.py test accounts music playlists --verbosity=2
```

**Kết quả đã verify thực tế khi xây dựng:**
```
Ran 118 tests in 63.733s
OK
```
```
Ran 361 tests in 155.388s   (accounts + music + playlists)
OK
```

### Bước 10 — Khởi động server và kiểm tra

```bash
python manage.py runserver 8000
```

Test nhanh bằng curl:
```bash
# Kiểm tra route đã đăng ký (sẽ trả 401 vì cần auth - đúng behavior)
curl http://localhost:8000/api/v1/playlists/
```

---

## 5. Kiểm Tra Sau Khi Apply

### 5.1 Kiểm tra bảng trong Database

```bash
python manage.py dbshell
```

```sql
-- Xem tất cả bảng playlists
\dt playlists_*

-- Kết quả mong đợi:
--  playlists_playlist
--  playlists_playlist_song

-- Kiểm tra cấu trúc bảng playlist
\d playlists_playlist

-- Kiểm tra cấu trúc bảng playlist_song
\d playlists_playlist_song

-- Thoát
\q
```

### 5.2 Kiểm tra URLs đã đăng ký

```bash
python manage.py shell -c "
from django.urls import reverse
import uuid
fake_id = uuid.uuid4()
tests = [
    ('playlist-list',         {}),
    ('playlist-detail',       {'playlist_id': fake_id}),
    ('playlist-cover',        {'playlist_id': fake_id}),
    ('playlist-visibility',   {'playlist_id': fake_id}),
    ('playlist-song-list',    {'playlist_id': fake_id}),
    ('playlist-song-reorder', {'playlist_id': fake_id}),
    ('playlist-song-detail',  {'playlist_id': fake_id, 'song_id': fake_id}),
]
for name, kwargs in tests:
    try:
        url = reverse(name, kwargs=kwargs)
        print(f'OK: {name} -> {url}')
    except Exception as e:
        print(f'FAIL: {name} -> {e}')
"
```

### 5.3 Checklist cuối Tuần 3

```
[ ] playlists/ thu muc da tao du 12 file
[ ] 'playlists' da co trong INSTALLED_APPS
[ ] path('api/v1/playlists/', ...) da co trong urls.py goc
[ ] python manage.py check -> 0 issues
[ ] python manage.py makemigrations playlists -> 0001_initial.py
[ ] python manage.py migrate -> OK
[ ] \dt playlists_* -> 2 bang
[ ] curl /api/v1/playlists/ -> 401 (dung, vi can auth)
[ ] python manage.py test playlists -> 118 tests PASS
[ ] python manage.py test accounts music playlists -> 361 tests PASS
[ ] Django Admin: /admin/ -> thay Playlist (voi inline PlaylistSong)
```

---

## 6. Lưu Ý Quan Trọng

### 6.1 Dependency vào app music

`playlists/models.py` có dòng:
```python
song = models.ForeignKey('music.Song', on_delete=models.CASCADE, related_name='in_playlists')
```

Điều này **bắt buộc** app `music` phải nằm **trước** `playlists` trong thứ tự `INSTALLED_APPS`, và migration của `music` phải được apply **trước** migration của `playlists`. Vì cả hai điều kiện này đã đúng theo lộ trình triển khai tuần tự (Tuần 2 trước Tuần 3), Django tự xử lý đúng dependency này — không cần thêm `dependencies` thủ công trong migration.

### 6.2 Order tính từ 1, không từ 0

Khi thêm bài hát mới (`add_song_to_playlist`), order được tính bằng `get_max_order(playlist_id) + 1`. Playlist rỗng có `max_order = 0`, nên bài hát đầu tiên luôn có `order = 1` (không phải 0). Điều này được giữ nhất quán trong toàn bộ test suite.

### 6.3 Reorder dùng transaction.atomic

Hàm `reorder_playlist_songs()` trong `services.py` được decorate bằng `@transaction.atomic`. Nếu có lỗi xảy ra giữa lúc cập nhật (ví dụ mất kết nối DB), toàn bộ thay đổi order sẽ **rollback hoàn toàn** — playlist không bao giờ rơi vào trạng thái thứ tự nửa cũ nửa mới.

### 6.4 Ảnh bìa Playlist dùng đúng storage Cloudinary đã có

Không cần thêm biến môi trường mới trong `.env`. App `playlists` tái sử dụng 100% cấu hình `CLOUDINARY_STORAGE` đã khai báo từ Tuần 1, chỉ khác `upload_to` path (`covers/playlists/` thay vì `covers/songs/` hay `avatars/users/`).

### 6.5 Test dùng SQLite, Production dùng PostgreSQL

Schema SQL ở Mục 3.2 là cú pháp **PostgreSQL** (dùng cho production thật theo `.env` đã cấu hình `DB_*`). Khi chạy `python manage.py test`, Django tự dùng SQLite in-memory nên cú pháp UUID/CASCADE hiển thị khác đôi chút khi gọi `sqlmigrate` — đây là hành vi bình thường, không phải lỗi.
