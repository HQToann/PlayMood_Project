#mỗi text public phải qua sanitize_text()

import uuid
from datetime import timedelta
from django.utils import timezone
from music_platform.sanitize import sanitize_text
from accounts.exceptions import ValidationError


STATUS_TEXT_MAX = 200

#thời gian max/min 1 mood tồn tại (tính bằng giờ)
MOOD_MIN_DURATION_HOURS = 1
MOOD_MAX_DURATION_HOURS = 168 #7 ngày
MOOD_DEFAULT_DURATION_HOURS = 24


"""
validate dữ liệu thiết lập mood mới
kỳ vọng: {
    'status_text': '....',
    'song_id': 'uuid',
    'duration_hours': 24 (optinal, mặc định 24h)
}
- expires_at ddwuocj tính toán ở đay từ duration_hours , không nhận trược tiếp
từ client để tránh client gửi ngày trong quá khú/quá xa tương lai
"""
def validate_set_mood(data: dict) -> dict:
    errors = {}
    mood_type_id = data.get('mood_type_id', None)
    
    status_text = data.get('status_text', '').strip()
    if not status_text and not mood_type_id:
        errors['status_text'] = ['Trạng thái hoặc loại cảm xúc là bắt buộc']
    elif len(status_text) > STATUS_TEXT_MAX:
        errors['status_text'] = [f'Trạng thái tối đa {STATUS_TEXT_MAX} ký tự']
    
    song_id = data.get('song_id', None)
    if song_id:
        try:
            song_id = uuid.UUID(str(song_id))
        except (ValueError, AttributeError):
            errors['song_id'] = ['song_id không đúng định dạng UUID']
    else:
        song_id = None
    
    duration_hours = data.get('duration_hours', MOOD_DEFAULT_DURATION_HOURS)
    try:
        duration_hours = int(duration_hours)
        if not (MOOD_MIN_DURATION_HOURS <= duration_hours <= MOOD_MAX_DURATION_HOURS):
            errors['duration_hours'] = [f'Thời gian phải từ {MOOD_MIN_DURATION_HOURS} đến {MOOD_MAX_DURATION_HOURS} giờ']
    except (ValueError, TypeError):
        errors['duration_hours'] = ['Thời gian hiển thị không phải là số nguyên (giờ)']
        duration_hours = MOOD_DEFAULT_DURATION_HOURS

    theme_id = data.get('theme_id', None)
    if theme_id:
        try:
            theme_id = uuid.UUID(str(theme_id))
        except (ValueError, AttributeError):
            errors['theme_id'] = ['theme_id không đúng định dạng UUID']
            
    mood_type_id = data.get('mood_type_id', None)
    if mood_type_id:
        try:
            mood_type_id = uuid.UUID(str(mood_type_id))
        except (ValueError, AttributeError):
            errors['mood_type_id'] = ['mood_type_id không đúng định dạng UUID']

    if errors:
        raise ValidationError('Dữ liệu tâm trạng không hợp lệ', fields=errors)
    
    return {
        'status_text': sanitize_text(status_text),
        'song_id': song_id,
        'theme_id': theme_id,
        'mood_type_id': mood_type_id,
        'expires_at': timezone.now() + timedelta(hours=duration_hours),
    }

#validate và làm sạch query params khi lấy feed
def validate_list_feed_params(params: dict) -> dict:
    try: 
        page = max(1, int(params.get('page', 1)))
    except (ValueError, TypeError):
        page = 1

    
    try:
        page_size = min(100, max(1, int(params.get('page_size', 20))))
    except (ValueError, TypeError):
        page_size = 20

    
    return {
        'page': page,
        'page_size': page_size,
    }


#validate và làm sạch query params khi list followers/following
def validate_list_follow_params(params: dict) -> dict:
    try:
        page = max(1, int(params.get('page', 1)))
    except (ValueError, TypeError):
        page = 1

    try:
        page_size = min(100, max(1, int(params.get('page_size', 20))))
    except (ValueError, TypeError):
        page_size = 20

    return {
        'page': page,
        'page_size': page_size,
    }