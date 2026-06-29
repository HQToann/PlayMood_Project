# 05 — Cấu Hình & Thay Đổi Database App `social`

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

M�� file `music_platform/settings.py`, tìm phần `INSTALLED_APPS` và thêm `'social'`:

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

    # Noi bo - Tuan 1, 2, 3, 4
    'accounts',
    'music',
    'playlists',
    'artists',

    # Noi bo - Tuan 5 (THEM MOI)
    'social',

    # Cac app sau se them dan theo tuan:
    # 'notifications',
    # 'search',
]
```

> Không cần thêm config Cloudinary mới — app `social` không có file upload riêng (Mood/Follow/FriendActivity chỉ là dữ liệu text + FK).

---

## 2. Thay Đổi urls.py Gốc

M�� file `music_platform/urls.py`, thêm route cho app `social`:

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

    # Tuan 4
    path('api/v1/artists/',   include('artists.urls')),

    # Tuan 5 - THEM MOI
    path('api/v1/social/',    include('social.urls')),

    # Cac tuan sau (mo dan):
    # path('api/v1/notifications/', include('notifications.urls')),
    # path('api/v1/search/',        include('search.urls')),
]
```

---

## 3. Thay Đổi Database — Models Mới

### 3.1 Các bảng sẽ được tạo

| Tên bảng | Model | Mô tả |
|----------|-------|-------|
| `social_follow` | `Follow` | Quan hệ theo dõi giữa 2 User |
| `social_mood` | `Mood` | Trạng thái tâm trạng hiện tại — 1-1 với User |
| `social_friend_activity` | `FriendActivity` | Log hoạt động dùng cho Feed |

**Tổng: 3 bảng mới**

---

### 3.2 Schema chi tiết (PostgreSQL — Production)

#### `social_follow`

```sql
CREATE TABLE "social_follow" (
    "id"          uuid NOT NULL PRIMARY KEY,
    "follower_id" uuid NOT NULL REFERENCES "accounts_user"("id") ON DELETE CASCADE,
    "following_id" uuid NOT NULL REFERENCES "accounts_user"("id") ON DELETE CASCADE,
    "created_at"  timestamp with time zone NOT NULL
);
-- Indexes:
CREATE INDEX ON "social_follow" ("follower_id");
CREATE INDEX ON "social_follow" ("following_id");
CREATE UNIQUE INDEX "social_follow_follower_id_following_id_uniq"
    ON "social_follow" ("follower_id", "following_id");
```

#### `social_mood`

```sql
CREATE TABLE "social_mood" (
    "id"          uuid NOT NULL PRIMARY KEY,
    "user_id"     uuid NOT NULL UNIQUE REFERENCES "accounts_user"("id") ON DELETE CASCADE,
    "status_text" varchar(200) NOT NULL DEFAULT '',
    "song_id"     uuid NULL REFERENCES "music_song"("id") ON DELETE SET NULL,
    "expires_at"  timestamp with time zone NOT NULL,
    "created_at"  timestamp with time zone NOT NULL,
    "updated_at"  timestamp with time zone NOT NULL
);
-- Indexes:
CREATE UNIQUE INDEX ON "social_mood" ("user_id");   -- tu dong tu OneToOneField
```

#### `social_friend_activity`

```sql
CREATE TABLE "social_friend_activity" (
    "id"            uuid NOT NULL PRIMARY KEY,
    "user_id"       uuid NOT NULL REFERENCES "accounts_user"("id") ON DELETE CASCADE,
    "activity_type" varchar(10) NOT NULL,
    "song_id"       uuid NULL REFERENCES "music_song"("id") ON DELETE CASCADE,
    "extra_text"    varchar(200) NOT NULL DEFAULT '',
    "created_at"    timestamp with time zone NOT NULL
);
-- Indexes:
CREATE INDEX ON "social_friend_activity" ("user_id");
CREATE INDEX ON "social_friend_activity" ("activity_type");
CREATE INDEX ON "social_friend_activity" ("created_at");
CREATE INDEX "activity_user_time_idx" ON "social_friend_activity" ("user_id", "created_at");
```

> **Lưu ý:** `activity_user_time_idx` là composite index thêm thủ công trong `Meta.indexes`, hỗ trợ trực tiếp truy vấn Feed (`filter(user_id__in=...).order_by('-created_at')`) chạy nhanh hơn khi dữ liệu lớn.

---

### 3.3 Constraints quan trọng

| Bảng | Constraint | Mô tả |
|------|-----------|-------|
| `social_follow` | `UNIQUE(follower_id, following_id)` | Mỗi cặp follower-following chỉ có 1 bản ghi |
| `social_mood` | `UNIQUE(user_id)` | Mỗi user chỉ có 1 Mood đang hiển thị (OneToOneField) |

---

## 4. CLI Commands — Thứ Tự Thực Hiện

Thực hiện theo đúng thứ tự sau trong terminal tại thư mục gốc project:

### Bước 1 — Tạo thư mục app `social`

```bash
# Windows PowerShell
mkdir social
mkdir social\migrations
New-Item social\__init__.py -ItemType File
New-Item social\migrations\__init__.py -ItemType File
New-Item social\apps.py -ItemType File
New-Item social\models.py -ItemType File
New-Item social\exceptions.py -ItemType File
New-Item social\validators.py -ItemType File
New-Item social\selectors.py -ItemType File
New-Item social\services.py -ItemType File
New-Item social\views.py -ItemType File
New-Item social\urls.py -ItemType File
New-Item social\admin.py -ItemType File
New-Item social\tests.py -ItemType File
```

```bash
# Linux / macOS
mkdir -p social/migrations
touch social/__init__.py
touch social/migrations/__init__.py
touch social/apps.py social/models.py social/exceptions.py
touch social/validators.py social/selectors.py social/services.py
touch social/views.py social/urls.py social/admin.py social/tests.py
```

### Bước 2 — Copy source code

Copy nội dung từng file trong `03_social_source_code.md` vào file tương ứng.

### Bước 3 — Thêm 'social' vào INSTALLED_APPS

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
python manage.py makemigrations social
```

Kết quả mong đợi:
```
Migrations for 'social':
  social/migrations/0001_initial.py
    + Create model Mood
    + Create model Follow
    + Create model FriendActivity
```

### Bước 7 — Xem trước SQL (tùy chọn, để kiểm tra)

```bash
python manage.py sqlmigrate social 0001
```

### Bước 8 — Áp dụng migration

```bash
python manage.py migrate
```

Kết quả mong đợi:
```
Operations to perform:
  Apply all migrations: accounts, admin, artists, auth, contenttypes, music, playlists, sessions, social

Running migrations:
  Applying social.0001_initial... OK
```

### Bước 9 — Chạy tests

```bash
# Chỉ test app social
python manage.py test social --verbosity=2

# Chạy toàn bộ (Tuần 1+2+3+4+5) để đảm bảo không phá vỡ gì
python manage.py test accounts music playlists artists social --verbosity=2
```

**Kết quả đã verify thực tế khi xây dựng:**
```
Ran 79 tests in 109.383s
OK
```
```
Ran 171 tests in 224.810s   (accounts + music + playlists + artists + social)
OK
```

### Bước 10 — Khởi động server và kiểm tra

```bash
python manage.py runserver 8000
```

Test nhanh bằng curl:
```bash
# Kiểm tra route đã đăng ký (401 vì cần auth — đúng behavior)
curl http://localhost:8000/api/v1/social/feed/
```

---

## 5. Kiểm Tra Sau Khi Apply

### 5.1 Kiểm tra bảng trong Database

```bash
python manage.py dbshell
```

```sql
-- Xem tat ca bang social
\dt social_*

-- Ket qua mong doi:
--  social_follow
--  social_friend_activity
--  social_mood

-- Kiem tra cau truc bang Feed
\d social_friend_activity

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
    ('social-follow-toggle',  {'user_id': fake_id}),
    ('social-follow-status',  {'user_id': fake_id}),
    ('social-followers',      {'user_id': fake_id}),
    ('social-following',     {'user_id': fake_id}),
    ('social-my-mood',       {}),
    ('social-user-mood',     {'user_id': fake_id}),
    ('social-feed',          {}),
    ('social-my-activities', {}),
]
for name, kwargs in tests:
    try:
        url = reverse(name, kwargs=kwargs)
        print(f'OK: {name} -> {url}')
    except Exception as e:
        print(f'FAIL: {name} -> {e}')
"
```

### 5.3 Kiểm tra tích hợp với app music (Tuần 2) — bước quan trọng nhất

```bash
python manage.py shell -c "
from accounts.models import User
from music.models import Genre, Song
from music.services import record_play
from social.models import FriendActivity
from django.core.files.uploadedfile import SimpleUploadedFile

artist = User.objects.create_user(username='checkartist', email='checkartist@x.com', password='Test1234', role='artist')
user = User.objects.create_user(username='checkuser', email='checkuser@x.com', password='Test1234')
genre, _ = Genre.objects.get_or_create(name='CheckGenre')
song = Song.objects.create(
    title='Check Song', artist=artist, genre=genre, duration=200, status=Song.STATUS_PUBLISHED,
    audio_file=SimpleUploadedFile('c.mp3', b'\x00'*1024, content_type='audio/mpeg'),
)
before = FriendActivity.objects.filter(user=user).count()
record_play(user, song)
after = FriendActivity.objects.filter(user=user).count()
print('Truoc:', before, '| Sau:', after)
print('TICH HOP OK' if after > before else 'TICH HOP LOI - kiem tra lai create_friend_activity signature')
"
```

### 5.4 Checklist cuối Tuần 5

```
[ ] social/ thu muc da tao du 11 file
[ ] 'social' da co trong INSTALLED_APPS
[ ] path('api/v1/social/', ...) da co trong urls.py goc
[ ] python manage.py check -> 0 issues
[ ] python manage.py makemigrations social -> 0001_initial.py
[ ] python manage.py migrate -> OK
[ ] \dt social_* -> 3 bang
[ ] curl /api/v1/social/feed/ -> 401 (dung, vi can auth)
[ ] python manage.py test social -> 79 tests PASS
[ ] python manage.py test accounts music playlists artists social -> tat ca PASS
[ ] Script kiem tra tich hop record_play() -> "TICH HOP OK"
[ ] Django Admin: /admin/ -> thay "Xa hoi" (Follow, Mood, Hoat dong ban be)
```

---

## 6. Lưu Ý Quan Trọng

### 6.1 Dependency ngược — music (Tuần 2) gọi vào social (Tuần 5)

Đây là điểm khác biệt lớn nhất so với 4 app trước: thay vì `social` phụ thuộc vào `music`, **`music/services.py::record_play()` đã viết sẵn lời gọi vào `social.services.create_friend_activity()` từ Tuần 2** (bọc trong `try/except ImportError`-an toàn). Khi app `social` chưa tồn tại, lời gọi này bị bắt lỗi và bỏ qua âm thầm — không làm hỏng luồng nghe nhạc. Khi app `social` được thêm vào đúng theo hướng dẫn này, cơ chế tự động kích hoạt **mà không cần sửa lại bất kỳ dòng nào trong `music/services.py`**.

**Vì vậy, signature của `create_friend_activity()` là một hợp đồng (contract) bắt buộc phải giữ đúng:**
```python
def create_friend_activity(user, activity_type: str, song=None, extra_text: str = '') -> FriendActivity:
```

Nếu cần đổi tên tham số trong tương lai, phải đồng thời sửa lại lời gọi trong `music/services.py`.

### 6.2 Mood không cần cronjob xóa ngay ở Tuần 5

`Mood.is_expired()` được tính **tại thời điểm đọc** dữ liệu (so sánh `expires_at` với `timezone.now()`), không xóa bản ghi vật lý ngay khi hết hạn. Việc dọn dẹp định kỳ các Mood đã hết hạn lâu (để tránh phình bảng) sẽ được xử lý bằng management command ở **Tuần 7** (`cleanup_expired_moods`), đúng theo lộ trình ban đầu.

### 6.3 FriendActivity không bị giới hạn kích thước nghiêm ngặt ở giai đoạn này

M��i lượt nghe nhạc, follow, hay cập nhật Mood đều sinh 1 `FriendActivity` mới — bảng này sẽ tăng trưởng nhanh theo thời gian sử dụng. Việc dọn dẹp `FriendActivity` cũ (ví dụ giữ tối đa 90 ngày) cũng nằm trong phạm vi cleanup jobs của **Tuần 7**, không xử lý ở Tuần 5 để giữ phạm vi công việc tập trung.

### 6.4 Test dùng SQLite, Production dùng PostgreSQL

Schema SQL ở Mục 3.2 là cú pháp **PostgreSQL** (dùng cho production thật theo `.env` đã cấu hình `DB_*`). Khi chạy `python manage.py test`, Django tự dùng SQLite in-memory — đây là hành vi bình thường, không phải lỗi.
