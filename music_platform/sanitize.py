"""
music_platform/sanitize.py
===========================
Tiện ích sanitize dùng chung cho toàn project.

Mọi trường text do người dùng nhập và hiển thị công khai PHẢI được
xử lý qua các hàm này trước khi lưu vào database

Thư viện: bleach
"""

import re
import bleach

# Các tag nguy hiểm cần xóa cả nội dung bên trong (không chỉ strip tag)
_DANGEROUS_TAGS_RE = re.compile(
    r'<(script|style|iframe|object|embed|applet|form|input|button|select|textarea|link|meta)'
    r'[^>]*>.*?</\1>',
    flags=re.DOTALL | re.IGNORECASE,
)
# Xóa nốt các self-closing dangerous tags
_DANGEROUS_SELF_CLOSING_RE = re.compile(
    r'<(script|style|link|meta|input|button)[^>]*/?>',
    flags=re.IGNORECASE,
)


def sanitize_text(value: str) -> str:
    
    if not value:
        return ''
    # Bước 1: xóa hẳn dangerous tags + content bên trong
    value = _DANGEROUS_TAGS_RE.sub('', value)
    value = _DANGEROUS_SELF_CLOSING_RE.sub('', value)
    # Bước 2: strip mọi HTML tag còn lại, giữ text thuần
    return bleach.clean(value, tags=[], attributes={}, strip=True).strip()


def sanitize_url(value: str) -> str:
    
    if not value:
        return ''
    value = value.strip()
    if not value.startswith(('http://', 'https://')):
        raise ValueError('URL phải bắt đầu bằng http:// hoặc https://')
    return value