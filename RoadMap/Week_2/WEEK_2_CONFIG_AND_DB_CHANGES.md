# 04 — Cấu Hình & Thay Đổi Database Tuần 2

**App `music` — Settings, URLs, Migration, CLI Commands**

---

## Mục Lục

1. [Thay đổi `settings.py`](#1-thay-đổi-settingspy)
2. [Thay đổi `urls.py` gốc](#2-thay-đổi-urlspy-gốc)
3. [Thay đổi Database — Models mới](#3-thay-đổi-database--models-mới)
4. [CLI Commands — Thứ tự thực hiện](#4-cli-commands--thứ-tự-thực-hiện)
5. [Kiểm tra sau khi apply](#5-kiểm-tra-sau-khi-apply)

---

## 1. Thay Đổi `settings.py`

Mở file `music_platform/settings.py`, tìm phần `INSTALLED_APPS` và thêm `'music'`:

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

    # Nội bộ — Tuần 1
    'accounts',

    # Nội bộ — Tuần 2 (THÊM MỚI)
    'music',
]
```

### Cấu hình Cloudinary upload path (tùy chọn — tốt hơn cho production)

Nếu muốn kiểm soát path upload lên Cloudinary theo đúng pattern trong §12.3, thêm vào cuối `settings.py`:

```python
# ── Cloudinary upload presets (tùy chọn) ─────────────────────────────────────
# Mặc định Django Cloudinary Storage sẽ upload vào thư mục gốc.
# Để override path, dùng upload_to trong FileField (đã set sẵn trong models.py):
#   audio_file  = models.FileField(upload_to='audio/')
#   cover_image = models.ImageField(upload_to='covers/songs/')
# Cloudinary storage tự thêm PREFIX từ CLOUDINARY_STORAGE['PREFIX']
# Kết quả: music_platform/audio/<filename>

# Không cần thêm gì nếu đã cấu hình CLOUDINARY_STORAGE ở Tuần 1.
```

### Đảm bảo `mutagen` để đọc metadata audio (tùy chọn)

Nếu muốn tự động đọc duration từ file audio thay vì yêu cầu client gửi lên:

```bash
pip install mutagen==1.47.0
```

Thêm vào `requirements.txt`:
```
mutagen==1.47.0
```

Dùng trong `services.py` khi tạo bài hát:
```python
# Trong create_song(), sau khi nhận audio_file:
try:
    from mutagen import File as MutagenFile
    audio = MutagenFile(files['audio_file'])
    if audio and audio.info:
        data['duration'] = int(audio.info.length)
except Exception:
    pass  # fallback về duration từ client
```

> **Lưu ý:** Nếu không muốn dùng mutagen, giữ nguyên — client sẽ phải gửi `duration` lên khi upload.

---

## 2. Thay Đổi `urls.py` Gốc

Mở file `music_platform/urls.py`, thêm route cho app `music`:

```python
"""
music_platform/urls.py
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse


def handler404(request, exception):
    return JsonResponse(
        {'success': False, 'error': {'code': 'NOT_FOUND', 'message': 'Endpoint không tồn tại'}},
        status=404,
    )


def handler500(request):
    return JsonResponse(
        {'success': False, 'error': {'code': 'SERVER_ERROR', 'message': 'Lỗi server'}},
        status=500,
    )


def handler429(request, exception):
    return JsonResponse(
        {'success': False, 'error': {'code': 'RATE_LIMITED', 'message': 'Quá nhiều yêu cầu, vui lòng thử lại sau'}},
        status=429,
    )


urlpatterns = [
    path('admin/', admin.site.urls),

    # Tuần 1
    path('api/v1/auth/',     include('accounts.auth_urls')),
    path('api/v1/accounts/', include('accounts.urls')),

    # Tuần 2 — THÊM MỚI
    path('api/v1/music/',    include('music.urls')),

    # Các tuần sau (comment lại, mở dần):
    # path('api/v1/artists/',       include('artists.urls')),
    # path('api/v1/playlists/',     include('playlists.urls')),
    # path('api/v1/social/',        include('social.urls')),
    # path('api/v1/notifications/', include('notifications.urls')),
    # path('api/v1/search/',        include('search.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
```

---

## 3. Thay Đổi Database — Models Mới

### 3.1 Các bảng sẽ được tạo

| Tên bảng | Model | Mô tả |
|----------|-------|-------|
| `music_genre` | `Genre` | Thể loại nhạc |
| `music_song` | `Song` | Bài hát (audio + cover) |
| `music_like` | `Like` | Yêu thích bài hát |
| `music_rating` | `Rating` | Đánh giá sao |
| `music_comment` | `Comment` | Bình luận (threaded) |
| `music_comment_like` | `CommentLike` | Yêu thích bình luận |
| `music_listen_history` | `ListenHistory` | Lịch sử nghe |
| `music_report` | `Report` | Báo cáo vi phạm |

**Tổng: 8 bảng mới**

---

### 3.2 Schema chi tiết các bảng quan trọng

#### `music_song`

```sql
CREATE TABLE "music_song" (
    "id"             uuid NOT NULL PRIMARY KEY,
    "title"          varchar(200) NOT NULL,
    "artist_id"      uuid NOT NULL REFERENCES "accounts_user"("id"),
    "genre_id"       uuid NULL REFERENCES "music_genre"("id"),
    "audio_file"     varchar(100) NOT NULL,
    "cover_image"    varchar(100) NULL,
    "lyrics"         text NOT NULL DEFAULT '',
    "duration"       integer NOT NULL DEFAULT 0,
    "status"         varchar(15) NOT NULL DEFAULT 'draft',
    "allow_download" boolean NOT NULL DEFAULT false,
    "is_trending"    boolean NOT NULL DEFAULT false,
    "play_count"     integer NOT NULL DEFAULT 0,
    "released_at"    timestamp with time zone NULL,
    "created_at"     timestamp with time zone NOT NULL,
    "updated_at"     timestamp with time zone NOT NULL
);
-- Indexes:
CREATE INDEX ON "music_song" ("artist_id");
CREATE INDEX ON "music_song" ("status");
CREATE INDEX ON "music_song" ("is_trending");
CREATE INDEX ON "music_song" ("play_count");
CREATE INDEX ON "music_song" ("created_at");
```

#### `music_listen_history`

```sql
CREATE TABLE "music_listen_history" (
    "id"          uuid NOT NULL PRIMARY KEY,
    "user_id"     uuid NOT NULL REFERENCES "accounts_user"("id"),
    "song_id"     uuid NOT NULL REFERENCES "music_song"("id"),
    "listened_at" timestamp with time zone NOT NULL
);
-- Composite index cho dedup query (Fix R8):
CREATE INDEX "history_user_song_time_idx"
    ON "music_listen_history" ("user_id", "song_id", "listened_at");
```

#### `music_comment`

```sql
CREATE TABLE "music_comment" (
    "id"        uuid NOT NULL PRIMARY KEY,
    "user_id"   uuid NOT NULL REFERENCES "accounts_user"("id"),
    "song_id"   uuid NOT NULL REFERENCES "music_song"("id"),
    "parent_id" uuid NULL REFERENCES "music_comment"("id"),
    "content"   text NOT NULL,
    "is_hidden" boolean NOT NULL DEFAULT false,
    "created_at" timestamp with time zone NOT NULL
);
```

---

### 3.3 Constraints quan trọng

| Bảng | Constraint | Mô tả |
|------|-----------|-------|
| `music_like` | `UNIQUE(user_id, song_id)` | Mỗi user like 1 bài 1 lần |
| `music_rating` | `UNIQUE(user_id, song_id)` | Mỗi user 1 rating/bài |
| `music_comment_like` | `UNIQUE(user_id, comment_id)` | Mỗi user like 1 comment 1 lần |
| `music_genre` | `UNIQUE(name)` | Tên thể loại không trùng |
| `music_genre` | `UNIQUE(slug)` | Slug không trùng |

---

## 4. CLI Commands — Thứ Tự Thực Hiện

Thực hiện **theo đúng thứ tự** sau trong terminal tại thư mục gốc project:

### Bước 1 — Tạo thư mục app `music`

```bash
# Windows PowerShell
mkdir music
mkdir music\migrations
New-Item music\__init__.py -ItemType File
New-Item music\migrations\__init__.py -ItemType File
New-Item music\apps.py -ItemType File
New-Item music\models.py -ItemType File
New-Item music\exceptions.py -ItemType File
New-Item music\validators.py -ItemType File
New-Item music\selectors.py -ItemType File
New-Item music\services.py -ItemType File
New-Item music\views.py -ItemType File
New-Item music\urls.py -ItemType File
New-Item music\admin.py -ItemType File
```

```bash
# Linux / macOS
mkdir -p music/migrations
touch music/__init__.py
touch music/migrations/__init__.py
touch music/apps.py music/models.py music/exceptions.py
touch music/validators.py music/selectors.py music/services.py
touch music/views.py music/urls.py music/admin.py
```

### Bước 2 — Copy source code

Copy nội dung từng file trong `03_week2_source_code.md` vào file tương ứng.

### Bước 3 — Thêm `'music'` vào `INSTALLED_APPS`

Sửa `music_platform/settings.py` như hướng dẫn ở [Mục 1](#1-thay-đổi-settingspy).

### Bước 4 — Thêm route vào `urls.py` gốc

Sửa `music_platform/urls.py` như hướng dẫn ở [Mục 2](#2-thay-đổi-urlspy-gốc).

### Bước 5 — Kiểm tra cấu hình

```bash
python manage.py check
```

Kết quả mong đợi:
```
System check identified no issues (0 silenced).
```

Nếu có lỗi `ImportError` hay `ModuleNotFoundError`, kiểm tra lại import trong các file vừa tạo.

### Bước 6 — Tạo migration

```bash
python manage.py makemigrations music
```

Kết quả mong đợi:
```
Migrations for 'music':
  music/migrations/0001_initial.py
    + Create model Genre
    + Create model Song
    + Create model Like
    + Create model Rating
    + Create model Comment
    + Create model CommentLike
    + Create model ListenHistory
    + Create model Report
```

### Bước 7 — Xem trước SQL (tùy chọn, để kiểm tra)

```bash
python manage.py sqlmigrate music 0001
```

### Bước 8 — Áp dụng migration

```bash
python manage.py migrate
```

Kết quả mong đợi — tất cả phải `OK`:
```
Operations to perform:
  Apply all migrations: accounts, admin, auth, contenttypes, music, sessions

Running migrations:
  Applying music.0001_initial... OK
```

### Bước 9 — Chạy tests

```bash
# Chạy toàn bộ tests (bao gồm Tuần 1 + Tuần 2)
python manage.py test accounts music --verbosity=2
```

### Bước 10 — Khởi động server và kiểm tra

```bash
python manage.py runserver 8000
```

Test nhanh bằng browser hoặc curl:
```bash
# Kiểm tra genre list (không cần auth)
curl http://localhost:8000/api/v1/music/genres/

# Kiểm tra song list (không cần auth)
curl http://localhost:8000/api/v1/music/songs/
```

---

## 5. Kiểm Tra Sau Khi Apply

### 5.1 Kiểm tra bảng trong Database

```bash
python manage.py dbshell
```

```sql
-- Xem tất cả bảng music
\dt music_*

-- Kết quả mong đợi:
--  music_comment
--  music_comment_like
--  music_genre
--  music_like
--  music_listen_history
--  music_rating
--  music_report
--  music_song

-- Kiểm tra cấu trúc bảng song
\d music_song

-- Thoát
\q
```

### 5.2 Kiểm tra URLs đã đăng ký

```bash
python manage.py shell -c "
from django.urls import reverse
tests = [
    ('music-genre-list',    {}),
    ('music-song-list',     {}),
    ('music-song-trending', {}),
]
for name, kwargs in tests:
    try:
        url = reverse(name, kwargs=kwargs)
        print(f'OK: {name} → {url}')
    except Exception as e:
        print(f'FAIL: {name} → {e}')
"
```

### 5.3 Checklist cuối Tuần 2

```
□ music/ thư mục đã tạo đủ 10 file
□ 'music' đã có trong INSTALLED_APPS
□ path('api/v1/music/', ...) đã có trong urls.py gốc
□ python manage.py check → 0 issues
□ python manage.py makemigrations music → 0001_initial.py
□ python manage.py migrate → OK
□ \dt music_* → 8 bảng
□ curl /api/v1/music/genres/ → 200 (list rỗng)
□ curl /api/v1/music/songs/ → 200 (list rỗng)
□ python manage.py test accounts music → tất cả PASS
□ Django Admin: /admin/ → thấy Genre, Song, Comment, Report
```

---

## 6. Tạo Dữ Liệu Mẫu Để Test (Tùy Chọn)

Chạy trong Django shell để tạo dữ liệu test nhanh:

```bash
python manage.py shell
```

```python
from accounts.models import User
from music.models import Genre, Song

# Tạo thể loại
pop  = Genre.objects.create(name='Pop', description='Nhạc Pop')
rock = Genre.objects.create(name='Rock', description='Nhạc Rock')
vpop = Genre.objects.create(name='V-Pop', description='Nhạc Pop Việt Nam')
print('Genres created:', Genre.objects.count())

# Tạo artist user để test
artist = User.objects.filter(role='artist').first()
if not artist:
    artist = User.objects.create_user(
        username='testartist',
        email='artist@example.com',
        password='Artist1234',
        role='artist',
    )
    print('Artist created:', artist.username)

# Kiểm tra Genre API
print('\nTất cả genres:')
for g in Genre.objects.all():
    print(f'  - {g.name} (slug: {g.slug})')

exit()
```

---

## 7. Lưu Ý Quan Trọng

### 7.1 Social app chưa có — `create_friend_activity` sẽ được bỏ qua

Trong `services.py/record_play()`, có đoạn gọi:
```python
from social.services import create_friend_activity
```

Đoạn này được bọc trong `try/except` nên sẽ **không gây lỗi** khi app `social` chưa tồn tại (Tuần 6). Khi Tuần 6 hoàn thành và app `social` được thêm vào, đoạn code này sẽ tự hoạt động.

### 7.2 Cloudinary `audio_file` dùng `resource_type='video'`

Cloudinary xử lý audio dưới `resource_type='video'` (không phải `'raw'` hay `'image'`). Django Cloudinary Storage tự xử lý điều này khi bạn dùng `FileField`. Nếu thấy lỗi upload audio, kiểm tra trong `CLOUDINARY_STORAGE`:

```python
# settings.py
CLOUDINARY_STORAGE = {
    'CLOUD_NAME':  config('CLOUDINARY_CLOUD_NAME'),
    'API_KEY':     config('CLOUDINARY_API_KEY'),
    'API_SECRET':  config('CLOUDINARY_API_SECRET'),
    'PREFIX':      'music_platform',
}
```

Để force resource_type cho audio, có thể dùng `CloudinaryField` thay vì `FileField` trong `models.py`:

```python
# Thay thế nếu cần kiểm soát resource_type:
from cloudinary.models import CloudinaryField

class Song(models.Model):
    audio_file = CloudinaryField(
        'audio',
        resource_type='video',   # Cloudinary dùng 'video' cho audio
        folder='audio/',
    )
    cover_image = CloudinaryField(
        'image',
        resource_type='image',
        folder='covers/songs/',
        blank=True,
        null=True,
    )
```

> **Khuyến nghị:** Dùng `CloudinaryField` để kiểm soát tốt hơn. Nếu dùng `FileField` với `DEFAULT_FILE_STORAGE`, Cloudinary storage sẽ tự detect resource_type nhưng có thể sai với audio.

### 7.3 `play_count` — Không bao giờ gán trực tiếp

```python
# ❌ TUYỆT ĐỐI KHÔNG làm thế này (race condition):
song.play_count += 1
song.save()

# ✅ LUÔN dùng F() expression (Fix R1):
Song.objects.filter(id=song.id).update(play_count=F('play_count') + 1)
```

### 7.4 `status=hidden` là soft delete

Bài hát bị ẩn (`status=hidden`) **không bị xóa khỏi DB**. Tất cả selectors đều filter `status != hidden` trước khi trả kết quả. Admin có thể restore bằng cách đổi `status=published` qua Django Admin.
