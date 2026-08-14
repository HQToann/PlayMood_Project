"""
music_platform/settings.py

Cấu hình Django cho Hệ thống Âm nhạc.
"""

import os
from pathlib import Path
from decouple import config, Csv

# Đường dẫn gốc prooject
BASE_DIR = Path(__file__).resolve().parent.parent


# Bảo mật cốt lõi
SECRET_KEY = config('SECRET_KEY')
DEBUG = config('DEBUG', default=False, cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1', cast=Csv())
RENDER_EXTERNAL_HOSTNAME = os.environ.get('RENDER_EXTERNAL_HOSTNAME')
if RENDER_EXTERNAL_HOSTNAME:
    ALLOWED_HOSTS = list(ALLOWED_HOSTS) + [RENDER_EXTERNAL_HOSTNAME]
if 'testserver' not in ALLOWED_HOSTS:
    ALLOWED_HOSTS = list(ALLOWED_HOSTS) + ['testserver']
    
AUTH_USER_MODEL = 'accounts.User'

# BÁO CHO DJANGO BIẾT NÓ ĐANG CHẠY HTTPS QUA RENDER:
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')


# Ứng dụng đã cài đặc
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Third-party
    'corsheaders',
    'anymail',
    'cloudinary',
    'cloudinary_storage',

    # Ứng dụng nội bộ
    'accounts',
    'music',
    'playlists',
    'artists',
    'social',
    'notifications',
    'search',
    'recommendations',

]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'music_platform.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
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
WSGI_APPLICATION = 'music_platform.wsgi.application'


# Database
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

import dj_database_url
db_from_env = dj_database_url.config(conn_max_age=600)
if db_from_env:
    DATABASES['default'].update(db_from_env)


# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', 'OPTIONS': {'min_length': 8}
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
LANGUAGE_CODE = 'vi'
TIME_ZONE = 'Asia/Ho_Chi_Minh'
USE_I18N = True
USE_TZ = True


# Static files (CSS, JavaScript, Images) + Media files

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

if not DEBUG:
    STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'


# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# Cloudinary Storage
CLOUDINARY_STORAGE = {
    'CLOUD_NAME': config('CLOUDINARY_CLOUD_NAME', default=''),
    'API_KEY': config('CLOUDINARY_API_KEY', default=''),
    'API_SECRET': config('CLOUDINARY_API_SECRET', default=''),
    'PREFIX': config('CLOUDINARY_PREFIX', default='music_platform'),
}
DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.MediaCloudinaryStorage'

# Session
SESSION_ENGINE = 'django.contrib.sessions.backends.db'
SESSION_COOKIE_AGE = config('SESSION_COOKIE_AGE', default=1209600, cast=int) # 14 ngày
SESSION_COOKIE_HTTPONLY = True # JS không được đọc sessionid
SESSION_COOKIE_SECURE = config('SESSION_COOKIE_SECURE', default=False, cast=bool)
SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_NAME = 'sessionid'

# CSRF
CSRF_COOKIE_HTTPONLY = False # JS CẦN đọc csrftoken để gửi trong header X-CSRFToken
CSRF_COOKIE_SECURE = config('CSRF_COOKIE_SECURE', default=False, cast=bool)
CSRF_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_NAME = 'csrftoken'
CSRF_TRUSTED_ORIGINS = config(
    'CSRF_TRUSTED_ORIGINS',
    default='http://localhost:3000,http://localhost:8080',
    cast=Csv(),
)
if RENDER_EXTERNAL_HOSTNAME:
    CSRF_TRUSTED_ORIGINS = list(CSRF_TRUSTED_ORIGINS) + [f'https://{RENDER_EXTERNAL_HOSTNAME}']

# CORS
CORS_ALLOWED_ORIGINS = config(
    'CORS_ALLOWED_ORIGINS',
    default='http://localhost:3000,http://localhost:8080',
    cast=Csv(),
)

CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',    # Header CSRF Token
    'x-requested-with',
]

# Email
EMAIL_BACKEND = "anymail.backends.resend.EmailBackend"
ANYMAIL = {
    "RESEND_API_KEY": config("RESEND_API_KEY", default=""),
}
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='no-reply@trainghiemthuhtq.id.vn')
FRONTEND_URL = config('FRONTEND_URL', default='http://localhost:3000')


# Rate Limiting (bật Tuần 8)
RATELIMIT_ENABLE = config('RATELIMIT_ENABLE', default=False, cast=bool)


# Logging
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
# Block này tự detect: nếu không có DB_NAME trong .env thì dùng SQLite
import os as _os
if not _os.environ.get('DATABASE_URL') and not _os.environ.get('DB_NAME'):

    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db_test.sqlite3',
        }
    }
    # Dùng filesystem storage khi Cloudinary chưa cấu hình
    DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'