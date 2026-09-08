"""
music_platform/settings.py
Cấu hình Django cho dự án PlayMood (Hệ thống Âm nhạc & Mạng xã hội).
"""

import os
from pathlib import Path
from decouple import config, Csv
import dj_database_url
from django.templatetags.static import static

# 1. CẤU HÌNH THƯ MỤC GỐC (BASE DIRECTORY)
# Trỏ đến thư mục gốc của toàn bộ dự án
BASE_DIR = Path(__file__).resolve().parent.parent

# 2. BẢO MẬT HỆ THỐNG (SECURITY)
# Cảnh báo: Giữ bí mật SECRET_KEY trong môi trường production!
SECRET_KEY = config('SECRET_KEY')

# Bật tính năng gỡ lỗi (chỉ dùng cho môi trường phát triển - Development)
DEBUG = config('DEBUG', default=False, cast=bool)

# Danh sách các domain/IP được phép truy cập vào hệ thống
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1', cast=Csv())

# Hỗ trợ tự động thêm hostname khi deploy trên nền tảng Render
RENDER_EXTERNAL_HOSTNAME = os.environ.get('RENDER_EXTERNAL_HOSTNAME')
if RENDER_EXTERNAL_HOSTNAME:
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)
if 'testserver' not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append('testserver')

# Chỉ định model người dùng tùy chỉnh (Custom User Model)
AUTH_USER_MODEL = 'accounts.User'

# Báo cho Django biết ứng dụng đang chạy sau một proxy an toàn (HTTPS)
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')


# 3. DANH SÁCH ỨNG DỤNG & MIDDLEWARE (APPS & MIDDLEWARE)
INSTALLED_APPS = [
    # Giao diện admin và hỗ trợ WebSocket
    "daphne",
    "unfold",
    
    # Các ứng dụng cốt lõi của Django
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Thư viện của bên thứ ba (Third-party)
    'corsheaders',
    'anymail',
    'cloudinary',
    'cloudinary_storage',

    # Các ứng dụng nội bộ của dự án (Local Apps)
    'accounts',
    'music',
    'playlists',
    'artists',
    'social',
    'notifications',
    'search',
    'recommendations',
    'chat',
    'posts',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    # WhiteNoise dùng để phục vụ static files hiệu quả
    'whitenoise.middleware.WhiteNoiseMiddleware',
    # Cấu hình CORS cho phép frontend gọi API
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]


# 4. ĐỊNH TUYẾN & GIAO DIỆN (URLS & TEMPLATES)
ROOT_URLCONF = 'music_platform.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'], # Thư mục chứa các giao diện HTML
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]


# 5. SERVER CHẠY ỨNG DỤNG (WSGI, ASGI & WEBSOCKETS)
WSGI_APPLICATION = 'music_platform.wsgi.application'
ASGI_APPLICATION = 'music_platform.asgi.application'

# Cấu hình Channels Layer cho WebSocket (dùng Redis nếu có)
redis_url = config('REDIS_URL', default='')
if redis_url:
    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels_redis.pubsub.RedisPubSubChannelLayer",
            "CONFIG": {
                "hosts": [redis_url],
            },
        },
    }
else:
    # Nếu không có Redis, dùng InMemory (chỉ thích hợp cho test/dev)
    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels.layers.InMemoryChannelLayer",
        },
    }


# 6. CƠ SỞ DỮ LIỆU (DATABASE)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('DB_NAME', default='Play_Mood_db'),
        'USER': config('DB_USER', default='postgres'),
        'PASSWORD': config('DB_PASSWORD', default=''),
        'HOST': config('DB_HOST', default='localhost'),
        'PORT': config('DB_PORT', default='5432'),
    }
}

# Nếu có chuỗi kết nối DATABASE_URL (như trên Supabase, Render), sẽ ưu tiên sử dụng
database_url = config('DATABASE_URL', default='')
if database_url:
    DATABASES['default'] = dj_database_url.parse(database_url, conn_max_age=600)

# Tự động lùi về SQLite cục bộ nếu không cấu hình DB trong .env
if not config('DATABASE_URL', default='') and not config('DB_NAME', default=''):
    DATABASES['default'] = {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db_test.sqlite3',
    }


# 7. CHÍNH SÁCH MẬT KHẨU & QUỐC TẾ HÓA (PASSWORD & I18N)
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', 'OPTIONS': {'min_length': 8}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'vi' # Cài đặt ngôn ngữ hiển thị mặc định là Tiếng Việt
TIME_ZONE = 'Asia/Ho_Chi_Minh' # Múi giờ Việt Nam
USE_I18N = True
USE_TZ = True
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# 8. TỆP TĨNH & MULTIMEDIA (STATIC & MEDIA FILES)
# Cấu hình đường dẫn cho các tệp tĩnh (CSS, JS, Hình ảnh giao diện)
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

STATIC_DIR = BASE_DIR / 'static'
if STATIC_DIR.exists():
    STATICFILES_DIRS = [STATIC_DIR]

# Cấu hình thư mục lưu trữ file được upload cục bộ
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Cấu hình lưu trữ tệp tin trên Cloudinary (nếu sử dụng)
CLOUDINARY_STORAGE = {
    'PREFIX': config('CLOUDINARY_PREFIX', default='music_platform'),
}

cloudinary_url = config('CLOUDINARY_URL', default='')
if cloudinary_url:
    os.environ['CLOUDINARY_URL'] = cloudinary_url

# Định nghĩa Storage Backend: dùng Cloudinary cho media và WhiteNoise cho static
STORAGES = {
    "default": {
        "BACKEND": "cloudinary_storage.storage.MediaCloudinaryStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage" if not DEBUG else "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}

# Nếu không cấu hình DB, đồng nghĩa đang chạy môi trường test/dev đơn giản -> lưu media cục bộ
if not config('DATABASE_URL', default='') and not config('DB_NAME', default=''):
    STORAGES["default"]["BACKEND"] = "django.core.files.storage.FileSystemStorage"


# 9. BẢO MẬT PHIÊN LÀM VIỆC & CSRF (SESSIONS & CSRF)
SESSION_ENGINE = 'django.contrib.sessions.backends.db'
SESSION_COOKIE_AGE = config('SESSION_COOKIE_AGE', default=1209600, cast=int) # Mặc định 2 tuần
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SECURE = config('SESSION_COOKIE_SECURE', default=False, cast=bool)
SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_NAME = 'sessionid'

CSRF_COOKIE_HTTPONLY = False
CSRF_COOKIE_SECURE = config('CSRF_COOKIE_SECURE', default=False, cast=bool)
CSRF_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_NAME = 'csrftoken'
CSRF_TRUSTED_ORIGINS = config('CSRF_TRUSTED_ORIGINS', default='http://localhost:3000,http://localhost:8080', cast=Csv())
if RENDER_EXTERNAL_HOSTNAME:
    CSRF_TRUSTED_ORIGINS.append(f'https://{RENDER_EXTERNAL_HOSTNAME}')


# 10. DỊCH VỤ BÊN NGOÀI & CHÍNH SÁCH TRUY CẬP (EXTERNAL API & CORS)
# Danh sách Frontend được phép kết nối API (Cross-Origin)
CORS_ALLOWED_ORIGINS = config('CORS_ALLOWED_ORIGINS', default='http://localhost:3000,http://localhost:8080', cast=Csv())
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_HEADERS = [
    'accept', 'accept-encoding', 'authorization', 'content-type',
    'dnt', 'origin', 'user-agent', 'x-csrftoken', 'x-requested-with',
]

# Cấu hình gửi thư (Email) qua Resend (Sử dụng cho tính năng Quên mật khẩu, v.v...)
EMAIL_BACKEND = "anymail.backends.resend.EmailBackend"
ANYMAIL = {
    "RESEND_API_KEY": config("RESEND_API_KEY", default=""),
}
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='no-reply@trainghiemthuhtq.id.vn')

# Đường dẫn URL của Frontend, dùng để đính kèm link vào Email gửi đi
FRONTEND_URL = config('FRONTEND_URL', default='http://localhost:3000')

# Kích hoạt hoặc vô hiệu hóa tính năng giới hạn lượt truy cập (Rate Limiting)
RATELIMIT_ENABLE = config('RATELIMIT_ENABLE', default=False, cast=bool)


# 11. GHI NHẬT KÝ (LOGGING)
# Cấu hình hệ thống lưu nhật ký quá trình hoạt động của server
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[{levelname}] {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'WARNING',
            'propagate': False,
        },
        'accounts': {
            'handlers': ['console'],
            'level': 'DEBUG' if DEBUG else 'INFO',
            'propagate': False,
        },
    },
}


# 12. GIAO DIỆN QUẢN TRỊ (UNFOLD ADMIN THEME)
# Tùy biến thư viện Unfold để trang quản trị admin hiện đại và tối màu (Dark Mode)
UNFOLD = {
    "SITE_HEADER": "PlayMood Admin",
    "SITE_TITLE": "PlayMood Dashboard",
    "SITE_SYMBOL": "music_note",
    "DASHBOARD_CALLBACK": "music_platform.dashboard.dashboard_callback",
    "THEME": "dark", # Ép buộc giao diện ban đêm
    "STYLES": [
        lambda request: static("css/admin_custom.css"),
    ],
    # Bảng màu xanh chủ đạo của hệ thống (Accent Color)
    "COLORS": {
        "primary": {
            "50": "#effdf5",
            "100": "#d9f9e6",
            "200": "#b5f2d1",
            "300": "#8ce1b2",
            "400": "#5bd194",
            "500": "#36b77b",
            "600": "#239360",
            "700": "#1d754e",
            "800": "#195d40",
            "900": "#154d35",
        },
    },
}
