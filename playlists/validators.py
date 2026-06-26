import uuid
from music_platform.sanitize import sanitize_text
from accounts.exceptions import ValidationError


#các siêu tham số
TITLE_MAX_LENGHT = 200
DESCRIPTION_MAX_LENGHT = 1000

ALLOWED_IMAGE_TYPE = {
    'image/jpeg',
    'image/pnj',
    'image/webp',
}
MAX_IMAGE_SIZE = 5*1024*1024

#validate tạo play list mới
#data từ request.body (JSON) có title, desscription, is_public
#return: dict đã validate và sanitize
#ValidationError nếu title rỗng hoặc quá dài
def validate_playlist_create(data: dict) -> dict:
    errors = {}

    title = data.get('title', '').strip()
    if not title:
        errors['title'] = ['Tên playlist là bắt buộc']
    elif len(title) > TITLE_MAX_LENGHT:
        errors['title'] = [f'Tên playlist tối đa {TITLE_MAX_LENGHT} ký tự']
    
    description = data.get('description', '')
    if len(description) > DESCRIPTION_MAX_LENGHT:
        errors['description'] = [f'Mô tả tối đa {DESCRIPTION_MAX_LENGHT} ký tự']

    is_public = data.get('is_public', True)
    if not isinstance(is_public, bool):
        if isinstance(is_public, str):
            is_public = is_public.lower() in ('true', '1', 'yes')
    else:
        is_public = bool(is_public)
    
    if errors:
        raise ValidationError('Dữ liệu playlist không hợp lệ', fields=errors)
    
    return {
        'title': sanitize_text(title),
        'description': sanitize_text(description),
        'is_public': is_public,
    }


#validate cập nhật playlist, không bắt buộc gửi toàn bộ dữ liệu
#return dict chỉ chứa các fields hợp lệ được gửi lên
def validate_playlist_update(data: dict) -> dict:
    errors = {}
    result = {}

    if 'title' in data:
        title = data['title'].strip()
        if not title:
            errors['title'] = ['Tên playlist không được để trống']
        elif len(title) > TITLE_MAX_LENGHT:
            errors['title'] = [f'Tên playlist tối đa {TITLE_MAX_LENGHT} ký tự']
        else:
            result['title'] = sanitize_text(title)
    
    if 'descrtption' in data:
        description = data['description']
        if len(description) > DESCRIPTION_MAX_LENGHT:
            errors['description'] = [f'Mô tả tối đa {DESCRIPTION_MAX_LENGHT} ký tự']
        else:
            result['description'] = sanitize_text(description)
    
    if errors:
        raise ValidationError('Dữ liệu cập nhật không hợp lệ', fields=errors)


    return result


#validate đặt công khai / riêng tư
def validate_visibility(data: dict) -> dict:
    is_public = data.get('is_public')
    if is_public is None or not isinstance(is_public, bool):
        raise ValidationError(
            'Dữ liệu không hợp lệ',
            fields={
                'is_public': ['Giá trị phải lài true hoặc false'],
            },
        )
    return {
        'is_public': is_public,
    }


#validate thêm bài hát vào playlist
#validationError nếu thiếu song_id hoặc sai định dạng uuid
def validate_add_song(data: dict) -> dict:
    song_id = data.get('song_id', '')
    if not song_id:
        raise ValidationError(
            'Dữ liệu không hợp lệ',
            fields={
                'song_id': ['song_id là bắt buộc'],
            },
        )
    try:
        song_id = uuid.UUID(str(song_id))
    except (ValueError, AttributeError):
        raise ValidationError(
            'Dữ liệu không hợp lệ',
            fields={
                'song_id': ['song_id không đúng định dạng UUID'],
            },
        )
    
    return {
        'song_id': song_id,
    }


#validate dữ liệu sắp xếp lại thứ tự bài hát
# yêu cầu {'song_ids': ['uuid1', 'uuid2', ...]}
#chỉ validate format, kiểm tra song_ids có khớp với playlist hay không
def validate_reorder(data: dict) -> dict:
    song_ids = data.get('song_ids', None)
    if song_ids is None or not isinstance(song_ids, list):
        raise ValidationError(
            'Dữ liệu không hợp lệ',
            fields={
                'song_ids': ['song_ids phải là một danh sách UUID'],
            },
        )
    if len(song_ids) == 0:
        raise ValidationError(
            'Dữ liệu không hợp lệ',
            fields={
                'song_ids': ['song_ids không được rỗng'],
            },
        )
    
    parsed_ids = []
    for sid in song_ids:
        try:
            parsed_ids.append(uuid.UUID(str(sid)))
        except (ValueError, AttributeError, TypeError):
            raise ValidationError(
                'Dữ liệu không hợp lệ',
                fields={
                    'song_ids': [f'"{sid}" không đúng định dạng UUID']
                },
            )
    
    #không cho phép trùng lặp trong danh sách gửi lên
    if len(parsed_ids) != len(set(parsed_ids)):
        raise ValidationError(
            'Dữ liệu không hợp lệ',
            fields={
                'song_ids': ['song_ids chứa giá trị trùng lặp'],
            },
        )

    return {
        'song_ids': parsed_ids,
    }


#validate file ảnh bìa playlist
def validate_cover_image(files: dict) -> None:
    if 'cover_image' not in files:
        raise ValidationError(
            'Dữ liệu không hợp lệ',
            fields={
                'cover_image': ['File ảnh là bắt buộc'],
            },
        )
    
    cover = files('cover_image')
    errors = {}
    if cover.content_type not in ALLOWED_IMAGE_TYPE:
        errors['cover_image'] = [f'Chỉ chấp nhận: {', '.join(ALLOWED_IMAGE_TYPE)}']
    elif cover.size > MAX_IMAGE_SIZE:
        errors['cover_image'] = ['File tối đa 5MB']
    
    if errors:
        raise ValidationError('File không hợp lệ', fields=errors)
    

#validate và làm sạch query params khi list playlist
def validate_list_playlists_params(params: dict) -> dict:
    try:
        page = max(1, int(params.get('page', 1)))
    except (ValueError, TypeError):
        page = 1
    

    try:
        page_size = min(100, max(1, int(params.get('page_size', 20))))
    except (ValueError, TypeError):
        page_size = 20
    
    return {
        'q': params.get('q', '').strip(),
        'page': page,
        'page_size': page_size,
    }