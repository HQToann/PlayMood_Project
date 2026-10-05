import uuid
from music_platform.sanitize import sanitize_text
from accounts.exceptions import ValidationError


#các siêu tham số

#mp3, flac, wav, ogg, m4a/aac, flac alternate
ALLOWED_AUDIO_TYPES = {
    'audio/mpeg',
    'audio/flac',
    'audio/wav',
    'audio/ogg',
    'audio/m4a',
    'audio/x-flac',
}

#kích thước giới hạn của 1 file
MAX_AUDIO_SIZE = 50*1024*1024

#loại hình ảnh được phép up
ALLOWED_IMAGE_TYPES = {
    'image/jpeg',
    'image/png',
    'image/webp',
}
MAX_IMAGE_SIZE = 5*1024*1024

#các loại sắp xếp
VALID_ORDERINGS = {
    '-created_at', 'created_at',
    '-play_count', 'play_count',
    '-released_at', 'released_at',
    'title', '-title',
}

#các loại report
REPORT_REASONS = {
    'copyright',
    'spam',
    'offensive',
    'other',
}

#target report
REPORT_TARGETS = {
    'song',
    'comment',
    'user',
    'playlist',
}

#validate create/update genre
def validate_genre(data: dict) -> dict:
    errors = {}
    name = data.get('name', '').strip()
    if not name:
        errors['name'] = ['Tên thể loại là bắt buộc']
    elif len(name) > 100:
        errors['name'] = ['Tên thể loại không được vượt quá 100 ký tự']
    
    if errors:
        raise ValidationError('Dữ liệu thể loại không hợp lệ', fields=errors)
    
    return {
        'name': name,
        'description': sanitize_text(data.get('description', '')),
    }


# Validate upload bài hát mới
# Kiểm tra:
# title, genre_id, duration bắt buộc
# audio_file: MIME type + size
# cover_image: MIME type + size
# lyrics: sanitize XSS
def validate_song_create(data: dict, files: dict) -> dict:
    errors = {}

    #title
    title = data.get('title', '').strip()
    if not title:
        errors['title'] = ['Tên bài hát là bắt buộc']
    elif len(title) > 200:
        errors['title'] = ['tên bài hát tối đa 200 ký tự']

    #thể loại id
    genre_id = data.get('genre_id', '')
    if not genre_id:
        errors['genre_id'] = ['Thể loại là bắt buộc']
    else:
        try:
            genre_id = uuid.UUID(str(genre_id))
        except (ValueError, AttributeError):
            errors['genre_id'] = ['genre_id không đúng định dạng UUID']
    
    #thời lượng
    try:
        duration = int(data.get('duration', 0))
        if duration <= 0:
            errors['duration'] = ['Thời lượng phải lớn hơn 0']
    except (ValueError, TypeError):
        errors['duration'] = ['Thời lượng phải là số nguyên (giây)']
        duration = 0
    
    #audio_file
    if 'audio_file' not in files:
        errors['audio_file'] = ['File audio là bắt buộc']
    else:
        audio = files['audio_file']
        if audio.content_type not in ALLOWED_AUDIO_TYPES:
            errors['audio_file'] = [f'Chỉ chấp nhận: {", ".join(sorted(ALLOWED_AUDIO_TYPES))}']
        elif audio.size > MAX_AUDIO_SIZE:
            errors['audio_file'] = ['File audio tối đa 50MB']
    
    #cover_image
    if 'cover_image' in files:
        cover = files['cover_image']
        if cover.content_type not in ALLOWED_IMAGE_TYPES:
            errors['cover_image'] = [f'Chỉ chấp nhận: {", ".join(ALLOWED_IMAGE_TYPES)}']
        elif cover.size > MAX_IMAGE_SIZE:
            errors['cover_image'] = ['Ảnh bìa tối đa 5MB']
    
    if errors:
        raise ValidationError('Dữ liệu bài hát không hợp lệ', fields=errors)
    
    #allow_download
    allow_dl = data.get('allow_download', False)
    if isinstance(allow_dl, str):
        allow_dl = allow_dl.lower() in ('true', '1', 'yes')
    
    return {
        'title': sanitize_text(title),
        'genre_id': genre_id,
        'duration': duration,
        'lyrics': sanitize_text(data.get('lyrics', '')),
        'allow_download': bool(allow_dl),
        'released_at': data.get('released_at', None),
    }

#validate cập nhật bài hát
def validate_song_update(data: dict, files: dict) -> dict:
    errors = {}
    result = {}

    if 'title' in data:
        title = data['title'].strip()
        if not title:
            errors['title'] = ['Tên bài hát không được để trống']
        elif len(title) > 200:
            errors['title'] = ['Tên bài hát tối đa 200 ký tự']
        else:
            result['title'] = sanitize_text(title)

    if 'genre_id' in data:
        try:
            result['genre_id'] = uuid.UUID(str(data['genre_id']))
        except (ValueError, AttributeError):
            errors['genre_id'] = ['genre_id không đúng định dạng UUID']

    if 'lyrics' in data:
        result['lyrics'] =  sanitize_text(data['lyrics'])
    
    if 'allow_download' in data:
        val = data['allow_download']
        if isinstance(val, str):
            val = val.lower() in ('true', '1', 'yes')
        result['allow_download'] = bool(val)

    if 'cover_image' in files:
        cover = files['cover_image']
        if cover.content_type not in ALLOWED_IMAGE_TYPES:
            errors['cover_image'] = [f'Chỉ chấp nhận: {", ".join(ALLOWED_IMAGE_TYPES)}']
        elif cover.size > MAX_IMAGE_SIZE:
            errors['cover_image'] = ['Ảnh bìa tối đa 5MB']

    if errors:
        raise ValidationError('Dữ liệu cập nhật không hợp lệ', fields=errors)
    
    return result


#validate đánh giá 5 sao
def validate_rating(data: dict) -> dict:
    try:
        score = int(data.get('score', 0))
    except (ValueError, TypeError):
        raise ValidationError('Điểm đánh giá không hợp lệ', fields={
            'score': ['Điểm đánh gái phải là số nguyên từ 1 đến 5'],
            })
    
    if not 1 <= score <= 5:
        raise ValidationError('Điểm đánh giá không hợp lệ', fields={
            'scoore': ['Điểm phải là từ 1 đến 5'],
        })
    
    return {'score': score}


#validate nội dung bình luận
def validate_comment(data: dict) -> dict:
    errors = {}
    content = data.get('content', '').strip()

    if not content:
        errors['content'] = ['Nội dung bình luận là bắt buộc']
    elif len(content) > 2000:
        errors['content'] = ['Bình luận tối đa 2000 ký tự']
    
    if errors:
        raise ValidationError('Nội dung bình luận này không hợp lệ', fields=errors)
    
    parent_id = data.get('parent_id', None)
    if parent_id:
        try:
            parent_id = uuid.UUID(str(parent_id))
        except (ValueError, AttributeError):
            raise ValidationError('parent_id không hợp lệ', fields={
                'parent_id': ['parent_id phải là UUID hợp lệ'],
            })
    
    return {
        'content': sanitize_text(content),
        'parent_id': parent_id
    }
    

#validate báo cáo vi phạm
def validate_report(data: dict) -> dict:
    errors = {}

    target_type = data.get('target_type', '').strip()
    if target_type not in REPORT_TARGETS:
        errors['target_type'] = [f'target_type phải là một trong: {", ".join(REPORT_TARGETS)}']

    target_id = data.get('target_id', '')
    try:
        target_id = uuid.UUID(str(target_id))
    except (ValueError, AttributeError):
        errors['target_id'] = ['target_id phải là UUID hợp lệ']
    
    reason = data.get('reason', '').strip()
    if reason not in REPORT_REASONS:
        errors['reason'] = [f'reason phải là một trong: {", ".join(REPORT_REASONS)}']
    
    if errors:
        raise ValidationError('Dữ liệu báo cáo không hợp lệ', fields=errors)
    
    return {
        'target_type': target_type,
        'target_id': target_id,
        'reason': reason,
        'description': sanitize_text(data.get('description', '')),
    }

#Validate và làm sạch query params khi list bài hát
def validate_list_songs_params(params: dict) -> dict:
    try:
        page = max(1, int(params.get('page', 1)))
    except (ValueError, TypeError):
        page = 1
    
    try:
        page_size = min(100, max(1, int(params.get('page_size', 20))))
    except (ValueError, TypeError):
        page_size = 20
    
    ordering = params.get('ordering', '-created_at')
    if ordering not in VALID_ORDERINGS:
        ordering = '-created_at'

    return {
        'q': params.get('q', '').strip(),
        'genre': params.get('genre', '').strip(),
        'artist_id': params.get('artist_id', '').strip(),
        'ordering': ordering,
        'page': page,
        'page_size': page_size,
    }