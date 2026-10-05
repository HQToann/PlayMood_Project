# Stage 1: Base
FROM python:3.11-slim AS base

# Tránh Python tạo file .pyc và buffer stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Cài dependencies hệ thống (cần cho psycopg2, Pillow)
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    netcat-openbsd \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Stage 2: Dependencies
FROM base AS deps

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Stage 3: Production
FROM deps AS production

# Copy toàn bộ source code
COPY . .

# Thu thập static files (whitenoise sẽ serve)
# Cấp biến giả (dummy values) để bypass lỗi thiếu config khi build
ARG SECRET_KEY=build-only-dummy-key
ARG DATABASE_URL=sqlite:///dummy.db
ARG CLOUDINARY_URL=cloudinary://dummy:dummy@dummy
ENV SECRET_KEY=$SECRET_KEY \
    DATABASE_URL=$DATABASE_URL \
    CLOUDINARY_URL=$CLOUDINARY_URL
RUN python manage.py collectstatic --noinput --settings=music_platform.settings

# Tạo user không phải root (bảo mật)
RUN adduser --disabled-password --gecos '' appuser && \
    chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Daphne: ASGI server hỗ trợ WebSocket (Django Channels)
CMD ["daphne", \
    "-b", "0.0.0.0", \
    "-p", "8000", \
    "music_platform.asgi:application"]