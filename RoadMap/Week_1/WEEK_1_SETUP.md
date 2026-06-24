# WEEK 1 — Hướng Dẫn Cài Đặt Môi Trường

**Hệ thống Âm nhạc Django | Tuần 1: Nền tảng + App `accounts` + Authentication**

> Tài liệu này hướng dẫn từng bước cài đặt từ đầu trên máy tính mới.
> Tuân theo đúng thứ tự để tránh lỗi phụ thuộc.

---

## Mục Lục

1. [Yêu cầu hệ thống](#1-yêu-cầu-hệ-thống)
2. [Cài đặt Python](#2-cài-đặt-python)
3. [Cài đặt PostgreSQL](#3-cài-đặt-postgresql)
4. [Tạo Virtual Environment](#4-tạo-virtual-environment)
5. [Cài đặt thư viện Python](#5-cài-đặt-thư-viện-python)
6. [Tạo cấu trúc thư mục & file](#6-tạo-cấu-trúc-thư-mục--file)
7. [Cấu hình biến môi trường (.env)](#7-cấu-hình-biến-môi-trường-env)
8. [Cài đặt Cloudinary](#8-cài-đặt-cloudinary)
9. [Khởi tạo Database & Migration](#9-khởi-tạo-database--migration)
10. [Tạo tài khoản Admin](#10-tạo-tài-khoản-admin)
11. [Chạy server & kiểm tra](#11-chạy-server--kiểm-tra)
12. [Chạy Tests](#12-chạy-tests)
13. [Cấu trúc thư mục hoàn chỉnh](#13-cấu-trúc-thư-mục-hoàn-chỉnh)
14. [Ghi chú cho các tuần tiếp theo](#14-ghi-chú-cho-các-tuần-tiếp-theo)

---

## 1. Yêu Cầu Hệ Thống

| Thành phần | Phiên bản tối thiểu | Phiên bản khuyến nghị | Ghi chú |
|---|---|---|---|
| **Python** | 3.11 | 3.12.x | Bắt buộc — dùng `python3` |
| **pip** | 23.0+ | 24.x | Đi kèm Python |
| **PostgreSQL** | 14 | 16.x | Dùng cho production; test dùng SQLite |
| **Git** | 2.x | mới nhất | Quản lý source code |
| **Hệ điều hành** | Ubuntu 20.04 / macOS 12 / Windows 10 | — | Hướng dẫn bên dưới cho cả 3 |

---

## 2. Cài Đặt Python

### Ubuntu / Debian

```bash
sudo apt update
sudo apt install -y python3.12 python3.12-venv python3.12-dev python3-pip
# Kiểm tra
python3 --version
# → Python 3.12.x
```

### macOS (dùng Homebrew)

```bash
brew install python@3.12
# Kiểm tra
python3 --version
# → Python 3.12.x
```

### Windows

1. Tải installer tại https://www.python.org/downloads/
2. Chọn **Python 3.12.x** → **Download**
3. Chạy installer → **Tick "Add python.exe to PATH"** → Install Now
4. Mở PowerShell, kiểm tra:
```powershell
python --version
# → Python 3.12.x
```

---

## 3. Cài Đặt PostgreSQL

> Tuần 1 dùng SQLite để chạy test offline. PostgreSQL cần thiết khi chạy server thật.

### Ubuntu / Debian

```bash
sudo apt install -y postgresql postgresql-contrib libpq-dev
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Tạo database và user
sudo -u postgres psql << 'SQL'
CREATE DATABASE music_platform;
CREATE USER music_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE music_platform TO music_user;
ALTER DATABASE music_platform OWNER TO music_user;
\q
SQL

# Kiểm tra
psql -U music_user -d music_platform -c "SELECT version();"
```

### macOS (dùng Homebrew)

```bash
brew install postgresql@16
brew services start postgresql@16
echo 'export PATH="/opt/homebrew/opt/postgresql@16/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc

# Tạo database
createdb music_platform
psql music_platform -c "CREATE USER music_user WITH PASSWORD 'your_password';"
psql music_platform -c "GRANT ALL PRIVILEGES ON DATABASE music_platform TO music_user;"
```

### Windows

1. Tải tại https://www.postgresql.org/download/windows/
2. Cài đặt, ghi nhớ **password của user `postgres`**
3. Mở **pgAdmin** hoặc **SQL Shell (psql)**:
```sql
CREATE DATABASE music_platform;
CREATE USER music_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE music_platform TO music_user;
```

---

## 4. Tạo Virtual Environment

> Virtual environment cô lập thư viện Python của project khỏi hệ thống.
> **Bắt buộc** — không cài thư viện trực tiếp vào Python system.

```bash
# Di chuyển đến thư mục bạn muốn chứa project
cd ~/projects   # hoặc bất kỳ thư mục nào

# Clone project (hoặc tạo mới)
mkdir music_platform
cd music_platform

# Tạo virtual environment tên "venv"
python3 -m venv venv

# ── Kích hoạt virtual environment ──
# Linux / macOS:
source venv/bin/activate

# Windows (PowerShell):
venv\Scripts\Activate.ps1

# Windows (Command Prompt):
venv\Scripts\activate.bat

# Khi kích hoạt thành công, terminal hiện:
# (venv) user@machine:~/projects/music_platform$
```

> **Lưu ý:** Mỗi lần mở terminal mới phải kích hoạt lại venv bằng `source venv/bin/activate`.

```bash
# Kiểm tra đang dùng Python của venv (không phải system)
which python3
# → /home/user/projects/music_platform/venv/bin/python3   ✅

# Nâng cấp pip trong venv
pip install --upgrade pip
```

---

## 5. Cài Đặt Thư Viện Python

### 5.1. File `requirements.txt`

Đảm bảo file `requirements.txt` ở thư mục gốc project có nội dung:

```text
# Core
Django==5.2.3

# Database
psycopg2-binary==2.9.9

# Environment variables
python-decouple==3.8

# CORS
django-cors-headers==4.4.0

# Cloudinary — lưu trữ audio, ảnh bìa, avatar
cloudinary==1.40.0
django-cloudinary-storage==0.3.0

# Input sanitization — chống XSS (Fix R12)
bleach==6.1.0

# Rate limiting — chống brute force (Fix R6, bật ở Tuần 8)
django-ratelimit==4.1.0

# Testing utilities
factory-boy==3.3.0

# Image processing (dùng khi validate ảnh upload)
Pillow==10.4.0
```

### 5.2. Cài đặt

```bash
# Đảm bảo venv đang được kích hoạt
pip install -r requirements.txt
```

Kết quả mong đợi — tất cả installed:

```
Successfully installed Django-5.2.3
Successfully installed psycopg2-binary-2.9.9
Successfully installed python-decouple-3.8
Successfully installed django-cors-headers-4.4.0
Successfully installed cloudinary-1.40.0
Successfully installed django-cloudinary-storage-0.3.0
Successfully installed bleach-6.1.0
Successfully installed django-ratelimit-4.1.0
Successfully installed factory-boy-3.3.0
Successfully installed Pillow-10.4.0
```

### 5.3. Giải thích từng thư viện

| Thư viện | Phiên bản | Mục đích | Dùng từ tuần |
|---|---|---|---|
| `Django` | 5.2.3 | Web framework chính | 1 |
| `psycopg2-binary` | 2.9.9 | Driver kết nối PostgreSQL | 1 |
| `python-decouple` | 3.8 | Đọc biến môi trường từ `.env` | 1 |
| `django-cors-headers` | 4.4.0 | Cho phép frontend gọi API cross-origin | 1 |
| `cloudinary` | 1.40.0 | SDK upload file lên Cloudinary | 2 (cài sẵn từ tuần 1) |
| `django-cloudinary-storage` | 0.3.0 | Django storage backend cho Cloudinary | 2 (cài sẵn từ tuần 1) |
| `bleach` | 6.1.0 | Sanitize XSS trong text input (Fix R12) | 1 |
| `django-ratelimit` | 4.1.0 | Rate limiting chống brute force (Fix R6) | 8 (cài sẵn, chưa bật) |
| `factory-boy` | 3.3.0 | Factory tạo dữ liệu test | 1 |
| `Pillow` | 10.4.0 | Xử lý ảnh, cần cho `ImageField` | 1 |

### 5.4. Kiểm tra cài đặt thành công

```bash
python3 -c "import django; print('Django', django.__version__)"
# → Django 5.2.3

python3 -c "import cloudinary; print('Cloudinary OK')"
# → Cloudinary OK

python3 -c "import bleach; print('bleach OK')"
# → bleach OK
```

---

## 6. Tạo Cấu Trúc Thư Mục & File

> Thứ tự tạo quan trọng: tạo package (`__init__.py`) trước khi tạo các file bên trong.

```bash
# Đang ở thư mục gốc: music_platform/
# Tạo Django project package
mkdir -p music_platform

# Tạo app accounts
mkdir -p accounts/migrations

# Tạo các file __init__.py (đánh dấu là Python package)
touch music_platform/__init__.py
touch accounts/__init__.py
touch accounts/migrations/__init__.py
```

Sau khi tạo xong và copy code từ `WEEK_1_SOURCE_CODE.md`, cấu trúc thư mục phải là:

```
music_platform/                     ← Thư mục gốc project
│
├── manage.py                       ← Công cụ dòng lệnh Django
├── requirements.txt                ← Danh sách thư viện
├── .env.example                    ← Mẫu cấu hình môi trường
├── .env                            ← Cấu hình thật (tự tạo, KHÔNG commit git)
├── .gitignore                      ← Danh sách file không commit (xem mục 6.1)
│
├── music_platform/                 ← Django project package
│   ├── __init__.py
│   ├── settings.py                 ← Toàn bộ cấu hình Django
│   ├── urls.py                     ← URL router gốc
│   ├── wsgi.py                     ← WSGI entry point
│   └── sanitize.py                 ← Tiện ích XSS sanitize dùng chung
│
├── accounts/                       ← App quản lý tài khoản
│   ├── __init__.py
│   ├── apps.py                     ← Cấu hình app
│   ├── models.py                   ← User, ArtistVerification, BlockList
│   ├── exceptions.py               ← Custom exceptions nghiệp vụ
│   ├── validators.py               ← Kiểm tra dữ liệu đầu vào
│   ├── selectors.py                ← Read-only queries (tầng đọc)
│   ├── services.py                 ← Business logic (tầng ghi)
│   ├── decorators.py               ← require_auth, require_artist, require_admin
│   ├── views.py                    ← HTTP handlers
│   ├── auth_urls.py                ← URLs cho /api/v1/auth/
│   ├── urls.py                     ← URLs cho /api/v1/accounts/
│   ├── admin.py                    ← Đăng ký Django Admin
│   ├── tests.py                    ← 79 unit tests
│   └── migrations/
│       ├── __init__.py
│       └── 0001_initial.py         ← Tự sinh bởi makemigrations
│
└── venv/                           ← Virtual environment (KHÔNG commit git)
```

### 6.1. Tạo file `.gitignore`

```bash
cat > .gitignore << 'EOF'
# Virtual environment
venv/
.venv/
env/

# Biến môi trường — chứa secret keys, KHÔNG commit
.env

# Python cache
__pycache__/
*.py[cod]
*.pyo

# Django
*.sqlite3
db_test.sqlite3
staticfiles/
media/

# IDE
.vscode/
.idea/
*.swp

# OS
.DS_Store
Thumbs.db

# Logs
*.log
EOF
```

---

## 7. Cấu Hình Biến Môi Trường (.env)

### 7.1. Tạo file `.env` từ mẫu

```bash
cp .env.example .env
```

### 7.2. Điền các giá trị bắt buộc

Mở `.env` bằng editor bất kỳ và điền:

```ini
# ── BẮT BUỘC ──────────────────────────────────────────────────────────────────

# Chuỗi ngẫu nhiên ≥50 ký tự — tạo bằng lệnh bên dưới
SECRET_KEY=<paste kết quả lệnh tạo secret key vào đây>

DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Database PostgreSQL — điền đúng thông tin đã tạo ở Bước 3
DB_NAME=music_platform
DB_USER=music_user
DB_PASSWORD=your_password
DB_HOST=localhost
DB_PORT=5432

# ── TÙY CHỌN (để mặc định cho tuần 1) ────────────────────────────────────────

# Cloudinary — có thể để placeholder, chưa cần thật đến Tuần 2
CLOUDINARY_CLOUD_NAME=placeholder
CLOUDINARY_API_KEY=placeholder
CLOUDINARY_API_SECRET=placeholder

CORS_ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8080
CSRF_TRUSTED_ORIGINS=http://localhost:3000,http://localhost:8080
SESSION_COOKIE_AGE=1209600
SESSION_COOKIE_SECURE=False
CSRF_COOKIE_SECURE=False

# Email — để backend console cho dev (in ra terminal thay vì gửi thật)
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
FRONTEND_URL=http://localhost:3000

# Rate limiting — để False, sẽ bật ở Tuần 8
RATELIMIT_ENABLE=False
```

### 7.3. Tạo SECRET_KEY

```bash
python3 -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Copy kết quả (chuỗi ~50 ký tự), paste vào `SECRET_KEY=` trong file `.env`.

### 7.4. Kiểm tra Django đọc được `.env`

```bash
python3 -c "
from decouple import config
print('SECRET_KEY ok:', bool(config('SECRET_KEY')))
print('DB_NAME:', config('DB_NAME'))
print('DEBUG:', config('DEBUG'))
"
# → SECRET_KEY ok: True
# → DB_NAME: music_platform
# → DEBUG: True
```

---

## 8. Cài Đặt Cloudinary

> Tuần 1 chỉ cần cài thư viện và cấu hình sẵn. Upload ảnh thật lên Cloudinary bắt đầu từ Tuần 2.

### 8.1. Đăng ký tài khoản Cloudinary

1. Truy cập https://cloudinary.com → **Sign up for free**
2. Xác nhận email
3. Vào **Dashboard** → copy 3 giá trị:
   - **Cloud Name** → `CLOUDINARY_CLOUD_NAME`
   - **API Key** → `CLOUDINARY_API_KEY`
   - **API Secret** → `CLOUDINARY_API_SECRET`
4. Điền vào file `.env`

> **Free tier:** 25 GB storage + 25 GB bandwidth/tháng — đủ dùng cho toàn bộ 8 tuần.

### 8.2. Cấu hình đã có sẵn trong `settings.py`

```python
# Đã cấu hình sẵn — không cần chỉnh thêm
CLOUDINARY_STORAGE = {
    'CLOUD_NAME':  config('CLOUDINARY_CLOUD_NAME'),
    'API_KEY':     config('CLOUDINARY_API_KEY'),
    'API_SECRET':  config('CLOUDINARY_API_SECRET'),
    'PREFIX':      'music_platform',   # Prefix phân biệt môi trường dev/prod
}

DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.MediaCloudinaryStorage'
```

### 8.3. Test kết nối Cloudinary (tùy chọn)

```bash
python3 -c "
import cloudinary
from decouple import config
cloudinary.config(
    cloud_name = config('CLOUDINARY_CLOUD_NAME'),
    api_key    = config('CLOUDINARY_API_KEY'),
    api_secret = config('CLOUDINARY_API_SECRET'),
)
result = cloudinary.api.ping()
print('Cloudinary connected:', result)
"
```

---

## 9. Khởi Tạo Database & Migration

```bash
# Bước 1: Kiểm tra cấu hình không có lỗi
python manage.py check
# → System check identified no issues (0 silenced).

# Bước 2: Tạo file migration từ models
python manage.py makemigrations accounts
# → Migrations for 'accounts':
#     accounts/migrations/0001_initial.py
#       + Create model User
#       + Create model ArtistVerification
#       + Create model BlockList

# Bước 3: Áp dụng tất cả migrations vào database
python manage.py migrate
# → Applying contenttypes.0001_initial... OK
# → Applying accounts.0001_initial... OK
# → Applying admin.0001_initial... OK
# → ...
# → Applying sessions.0001_initial... OK
```

### Nếu gặp lỗi kết nối PostgreSQL

```
django.db.utils.OperationalError: could not connect to server
```

Kiểm tra PostgreSQL đang chạy:

```bash
# Ubuntu
sudo systemctl status postgresql
sudo systemctl start postgresql  # nếu chưa chạy

# macOS
brew services list | grep postgresql
brew services start postgresql@16

# Kiểm tra thông tin trong .env có đúng không
psql -U music_user -d music_platform -h localhost
```

---

## 10. Tạo Tài Khoản Admin

```bash
python manage.py createsuperuser
```

Nhập theo prompt:

```
Email address: admin@example.com
Username: admin
Password: Admin1234
Password (again): Admin1234
Superuser created successfully.
```

Sau đó nâng `role` lên `admin` trong Django shell:

```bash
python manage.py shell
```

```python
from accounts.models import User
u = User.objects.get(email='admin@example.com')
u.role = 'admin'
u.save()
print(f"Role updated: {u.role}")
exit()
```

---

## 11. Chạy Server & Kiểm Tra

```bash
python manage.py runserver 8000
```

Mở trình duyệt, kiểm tra các URL:

| URL | Mong đợi |
|---|---|
| http://localhost:8000/admin/ | Trang đăng nhập Django Admin |
| http://localhost:8000/api/v1/auth/csrf/ | `{"success": true, "detail": "CSRF cookie set"}` |
| http://localhost:8000/api/v1/auth/me/ | `{"success": false, "error": {"code": "AUTH_REQUIRED", ...}}` |
| http://localhost:8000/nonexistent/ | `{"success": false, "error": {"code": "NOT_FOUND", ...}}` |

---

## 12. Chạy Tests

> Tests dùng **SQLite in-memory** — không cần PostgreSQL, chạy hoàn toàn độc lập.

```bash
# Chạy toàn bộ test app accounts
python manage.py test accounts --verbosity=2

# Chạy theo nhóm cụ thể
python manage.py test accounts.tests.RegisterViewTest
python manage.py test accounts.tests.ValidateRegisterTest
python manage.py test accounts.tests.SelectorsTest
python manage.py test accounts.tests.DecoratorTest

# Chạy một test case cụ thể
python manage.py test accounts.tests.BlockViewTest.test_block_user
```

**Kết quả mong đợi:**

```
Creating test database for alias 'default'...
System check identified no issues (0 silenced).

test_register_success (accounts.tests.RegisterViewTest) ... ok
test_register_duplicate_email (accounts.tests.RegisterViewTest) ... ok
...

----------------------------------------------------------------------
Ran 79 tests in 44.972s

OK
Destroying test database for alias 'default'...
```

### Nhóm tests và ý nghĩa

| Test Class | Số tests | Kiểm tra gì |
|---|---|---|
| `SanitizeTextTest` | 9 | bleach XSS strip, sanitize_url |
| `ValidateRegisterTest` | 9 | username, email, password rules |
| `ValidateLoginTest` | 3 | trường bắt buộc |
| `ValidateChangePasswordTest` | 3 | old/new/confirm logic |
| `SelectorsTest` | 9 | DB queries, block policy (Fix R10) |
| `RegisterServiceTest` | 3 | duplicate email/username |
| `ToggleBlockServiceTest` | 4 | block/unblock, self-block, notfound |
| `CsrfViewTest` | 1 | cookie được set |
| `RegisterViewTest` | 4 | HTTP 201, 409, 400 responses |
| `LoginViewTest` | 4 | success, wrong password, inactive |
| `LogoutViewTest` | 2 | success, requires auth |
| `MeAuthViewTest` | 2 | authenticated, unauthenticated |
| `MyProfileViewTest` | 4 | GET, PATCH, XSS sanitize, requires auth |
| `PrivacyViewTest` | 2 | set private, invalid value |
| `PublicProfileViewTest` | 3 | public view, block=404, 404 |
| `BlockViewTest` | 3 | block, unblock, requires auth |
| `DecoratorTest` | 4 | require_auth, inactive, admin |
| `UserModelTest` | 7 | UUID PK, role, to_dict, password hash |

---

## 13. Cấu Trúc Thư Mục Hoàn Chỉnh

Sau khi hoàn thành tất cả bước, đây là cấu trúc đầy đủ:

```
music_platform/
├── .env                            ← Biến môi trường thật (KHÔNG commit)
├── .env.example                    ← Mẫu cấu hình (commit)
├── .gitignore
├── manage.py
├── requirements.txt
├── WEEK_1_GUIDE.md                 ← Hướng dẫn Postman
├── WEEK_1_SOURCE_CODE.md           ← Toàn bộ source code
├── WEEK_1_SETUP.md                 ← File này
│
├── venv/                           ← Virtual environment (KHÔNG commit)
│   ├── bin/
│   ├── lib/
│   └── ...
│
├── music_platform/                 ← Django project package
│   ├── __init__.py
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   └── sanitize.py
│
└── accounts/                       ← App accounts
    ├── __init__.py
    ├── apps.py
    ├── models.py
    ├── exceptions.py
    ├── validators.py
    ├── selectors.py
    ├── services.py
    ├── decorators.py
    ├── views.py
    ├── auth_urls.py
    ├── urls.py
    ├── admin.py
    ├── tests.py
    └── migrations/
        ├── __init__.py
        └── 0001_initial.py
```

---

## 14. Ghi Chú Cho Các Tuần Tiếp Theo

### Quy trình bắt đầu tuần mới

Mỗi tuần khi thêm app mới, thực hiện theo thứ tự:

```bash
# Bước 1: Tạo thư mục app mới (ví dụ app "music" ở Tuần 3)
mkdir -p music/migrations
touch music/__init__.py
touch music/migrations/__init__.py

# Bước 2: Tạo các file theo đúng thứ tự tầng kiến trúc
touch music/apps.py
touch music/models.py
touch music/exceptions.py    # (nếu có exception riêng)
touch music/validators.py
touch music/selectors.py
touch music/services.py
touch music/views.py
touch music/urls.py
touch music/admin.py
touch music/tests.py

# Bước 3: Đăng ký app trong settings.py
# Thêm 'music' vào INSTALLED_APPS

# Bước 4: Đăng ký URL trong music_platform/urls.py
# path('api/v1/music/', include('music.urls')),

# Bước 5: Tạo migration
python manage.py makemigrations music

# Bước 6: Migrate
python manage.py migrate
```

### Thêm thư viện mới

```bash
# Cài thư viện
pip install ten-thu-vien==x.y.z

# Cập nhật requirements.txt
pip freeze | grep ten-thu-vien >> requirements.txt
# Hoặc thêm tay vào requirements.txt với đúng version
```

### Checklist bắt buộc mỗi tuần

- [ ] Kích hoạt venv trước khi làm việc: `source venv/bin/activate`
- [ ] Tạo đúng cấu trúc file theo tầng kiến trúc
- [ ] Đăng ký app vào `INSTALLED_APPS`
- [ ] Đăng ký URL vào `music_platform/urls.py`
- [ ] Chạy `python manage.py makemigrations <app>` sau khi tạo/sửa models
- [ ] Chạy `python manage.py migrate` để áp dụng migration
- [ ] Chạy `python manage.py test <app>` — tất cả phải PASS trước khi bàn giao
- [ ] Xuất `WEEK_X_GUIDE.md` (Postman guide)
- [ ] Xuất `WEEK_X_SOURCE_CODE.md` (toàn bộ source code tuần đó)
- [ ] Xuất `WEEK_X_SETUP.md` (hướng dẫn cài đặt — file này)

### Thư viện sẽ thêm theo từng tuần

| Tuần | Thư viện mới | Lý do |
|---|---|---|
| **2** | *(không thêm)* | Dùng lại Cloudinary đã cài |
| **3** | `mutagen` | Đọc metadata audio (duration, bitrate) |
| **4** | *(không thêm)* | F() expression là built-in Django |
| **5** | *(không thêm)* | Search dùng ORM thuần |
| **6** | *(không thêm)* | Social dùng ORM thuần |
| **7** | `django-crontab` hoặc `django-q` | Cleanup jobs |
| **8** | *(không thêm)* | django-ratelimit đã cài sẵn từ tuần 1 |

---

## Xử Lý Lỗi Thường Gặp Khi Cài Đặt

| Lỗi | Nguyên nhân | Cách fix |
|---|---|---|
| `ModuleNotFoundError: No module named 'decouple'` | Chưa cài requirements hoặc venv chưa được kích hoạt | `source venv/bin/activate` → `pip install -r requirements.txt` |
| `django.core.exceptions.ImproperlyConfigured: AUTH_USER_MODEL refers to model 'accounts.User' that has not been installed` | Chưa thêm `'accounts'` vào `INSTALLED_APPS` | Thêm `'accounts'` vào `INSTALLED_APPS` trong `settings.py` |
| `django.db.utils.OperationalError: could not connect to server` | PostgreSQL chưa chạy hoặc sai thông tin `.env` | Kiểm tra PostgreSQL service + thông tin DB trong `.env` |
| `Error: That port is already in use` | Port 8000 đang bị chiếm | `python manage.py runserver 8001` hoặc kill process cũ |
| `django.db.migrations.exceptions.InconsistentMigrationHistory` | Migration DB không đồng bộ | `python manage.py migrate --run-syncdb` hoặc xóa DB tạo lại |
| `CSRF verification failed` khi test Postman | Thiếu header `X-CSRFToken` | Gọi `/api/v1/auth/csrf/` trước, thêm header `X-CSRFToken` |
| `Error loading psycopg2 module: No module named 'psycopg2'` | psycopg2-binary chưa cài đúng | `pip install psycopg2-binary==2.9.9` (cần `libpq-dev` trên Ubuntu) |
| `OSError: [Errno 8] Exec format error` (macOS ARM) | psycopg2-binary không tương thích chip M1/M2 | `pip install psycopg2` (thay binary) sau khi `brew install postgresql` |
