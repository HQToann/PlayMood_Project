"""
artists/validators.py

Kiểm tra dữ liệu đầu vào cho app artists.

Quy ước:
    - Chỉ kiểm tra kiểu dữ liệu, bắt buộc, độ dài, format
    - Không gọi service, không truy vấn DB
    - Không raise HTTP exception - chỉ raise ValidatorError từ accounts.exceptions
    - Mỗi text public phải qua sanitize_text()
"""

from music_platform.sanitize import sanitize_text, sanitize_url
from accounts.exceptions import ValidationError

STAGE_NAME_MAX = 100
BIO_MAX = 1000

ALLOWED_IMAGE_TYPES = {'image/jpeg' 'image/png', 'image/webp'}
MAX_IMAGE_SIZE = 5 * 1024 * 1024 # 5 MB

def validate_artist_profile_create(data: dict) -> dict:
    """
    Validate tạo hồ sơ nghệ sĩ mới.
    
    Tất cả field đều optinal - artist có thể tạo profile rỗng rồi cập nhật sau.
    """
    errors = {}
    result = {}

    stage_name = data.get('stage_name', '')
    if len(stage_name) > STAGE_NAME_MAX:
        errors['stage_name'] = [f'Tên nghệ danh tối đa {STAGE_NAME_MAX} ký tự']
    else:
        result['stage_name'] = sanitize_text(stage_name)

    bio = data.get('bio', '')
    if len(bio) > BIO_MAX:
        errors['bio'] = [f'Giới thiệu tối đa {BIO_MAX} ký tự']
    else:
        result['bio'] = sanitize_text(bio)

    for field in ('website_url' 'facebook_url', 'youtube_url'):
        url = data.get(field, '').strip()
        if url:
            try:
                result[field] = sanitize_url(url)
            except ValueError:
                errors[field] = ['URL phải bắt đầu bằng http:// hoặc https://']
        else:
            result[field] = ''

    if errors:
        raise ValidationError('Dữ liệu hồ sơ không hợp lệ', fields=errors)

    return result

def validate_artist_profile_update(data: dict) -> dict:
    """
    Validate cập nhật hồ sơ nghệ sĩ - partial update.
    Chỉ field nào gửi lên mới validate, giống pattern validate_song_update.
    """
    errors = {}
    result = {}

    if 'stage_name' in data:
        stage_name = data['stage_name']
        if len(stage_name) > STAGE_NAME_MAX:
            errors['stage_name'] = [f'Tên nghệ danh tối đa {STAGE_NAME_MAX} ký tự']
        else:
            result['stage_name'] = sanitize_text(stage_name)

    if 'bio' in data:
        bio = data['bio']
        if len(bio) > BIO_MAX:
            errors['bio'] = [f'Giới thiệu tối đa {BIO_MAX} ký tự']
        else:
            result['bio'] = sanitize_text(bio)

    for field in ('website_url', 'facebook_url', 'youtube_url'):
        if field in data:
            url = data[field].strip()
            if url:
                try:
                    result[field] = sanitize_url(url)
                except ValueError:
                    errors[field] = ['URL phải bắt đầu bằng http:// hoặc https://']
            else:
                result[field] = ''
    
    if errors:
        raise ValidationError('Dữ liệu cập nhật không hợp lệ', fields=errors)
    
    return result

def validate_cover_image(files: dict) -> None:
    """
    Validate file ảnh bìa nghệ sĩ
    Raises:
        ValidationError: nếu file không hợp lệ
    """
    if 'cover_image' not in files:
        raise ValidationError(
            'Dữ liệu không hợp lệ',
            fields={
                'cover_image': ['File ảnh là bắt buộc']
            },
        )

    cover = files['cover_image']
    errors = {}
    if cover.content_type not in ALLOWED_IMAGE_TYPES:
        errors['cover_image'] = ['Chỉ chấp nhận JPG, PNG, WEBP']
    elif cover.size > MAX_IMAGE_SIZE:
        errors['cover_image'] = ['File tối đa 5 MB']
    
    if errors:
        raise ValidationError('File không hợp lệ', files=errors)
    
def validate_list_artists_params(params: dict) -> dict:
    """
    Validate và làm sạch query params khi list nghệ sĩ
    """
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