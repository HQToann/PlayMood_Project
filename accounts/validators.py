"""
accounts/validators.py

Kiểm tra và làm sạch dữ liệu đầu vào cho app accounts.

Quy ước tầng validators:
  - CHỈ kiểm tra kiểu dữ liệu, bắt buộc, độ dài, format
  - KHÔNG gọi service, KHÔNG truy vấn DB
  - KHÔNG raise HTTP exception — chỉ raise ValidationError từ exceptions.py
  - Trả về dict đã sanitize để service dùng

Mọi trường text public phải qua sanitize_text()
"""
import re
from music_platform.sanitize import sanitize_text
from accounts.exceptions import ValidationError

# Hằng số giới hạn
USERNAME_MIN = 3
USERNAME_MAX = 50
PASSWORD_MIN = 8
DISPLAY_NAME_MAX = 100
BIO_MAX = 500

# Pattern username: chỉ chữ cái, số, dấu gạch dưới, dấu chấm, gạch ngang
USERNAME_PATTERN = re.compile(r'^[\w.\-]+$')

# Các loại file hợp cho minh chứng
ALLOWED_ID_CARD_TYPES = {'image/jpeg', 'image/png', 'application/pdf'}
MAX_ID_CARD_SIZE = 10 * 1024 * 1024

def validate_register(data: dict) -> dict:
    """
    Validate dữ liệu đăng ký tài khoản mới.

    Args:
        data: dict từ request.body (JSON), kỳ vọng có: username, email, password

    Returns:
        dict đã validate và sanitize

    Raises:
        ValidationError: nếu có bất kỳ field nào không hợp lệ
    """
    errors = {}
    
    # username
    username = data.get('username', '').strip()
    if not username:
        errors['username'] = ['Tên đăng nhập là bắt buộc']
    elif len(username) < USERNAME_MIN:
        errors['username'] = [f'Tên đăng nhập phải có ít nhất {USERNAME_MIN} ký tự']
    elif len(username) > USERNAME_MAX:
        errors['username'] = [f'Tên đăng nhập tối đa {USERNAME_MAX} ký tự']
    elif not USERNAME_PATTERN.match(username):
        errors['username'] = ['Tên đăng nhập chỉ gồm chữ cái, số, dấu chấm, gạch dưới, gạch ngang']
    
    # email
    email = data.get('email', '').strip().lower()
    if not email:
        errors['email'] = ['Email là bắt buộc']
    elif not _is_valid_email(email):
        errors['email'] = ['Email không đúng định dạng']

    # password
    password = data.get('password', '')
    if not password:
        errors['password'] = ['Mật khẩu là bắt buộc']
    elif len(password) < PASSWORD_MIN:
        errors['password'] = [f'Mật khẩu phải có ít nhất {PASSWORD_MIN} ký tự']
    elif not _is_strong_password(password):
        errors['password'] = ['Mật khẩu phải có ít nhất 1 chữ hoa, 1 chữ thường và 1 số']

    if errors:
        raise ValidationError('Dữ liệu đăng ký không hợp lệ', fields=errors) 

    return {
        'username': username,
        'email': email,
        'password': password,
    }

def validate_login(data: dict) -> dict:
    """
    Validate dữ liệu đăng nhập.

    Returns:
        dict với email và password đã làm sạch
    """

    errors = {}

    email = data.get('email', '').strip().lơer()
    if not email:
        errors['email'] = ['Email là bắt buộc']

    password = data.get('password', '')
    if not password:
        errors['password'] = ['Mật khẩu là bắt buộc']

    if errors:
        raise ValidationError('Thông tin đăng nhập không hợp lệ', fields=errors)
    
    return {
        'email': email,
        'password': password
    }

def validate_update_profile(data: dict) -> dict:
    """
    Validate dữ liệu cập nhật hồ sơ cá nhân (PATCH /api/v1/accounts/me/).

    Chỉ validate các field được gửi lên (partial update).
    Tất cả text field được sanitize XSS.

    Returns:
        dict chỉ chứa các field hợp lệ được gửi lên
    """

    errors = {}
    result = {}

    if 'display_name' in data:
        display_name = sanitize_text(data['display_name'])
        if len(display_name) > DISPLAY_NAME_MAX:
            errors['display_name'] = [f'Tên hiển thị tối đa {DISPLAY_NAME_MAX} ký tự']
        else:
            result['display_name'] = display_name
    
    if 'bio' in data:
        bio = sanitize_text(data['bio'])
        if len(bio) > BIO_MAX:
            errors['bio'] = [f'Giới thiệu tối đa {BIO_MAX} ký tự']
        else:
            result['bio'] = bio
    
    if 'username' in data:
        username = data['username'].strip()
        if len(username) < USERNAME_MIN or len(username) > USERNAME_MAX:
            errors['username'] = [f'Tên đăng nhập từ {USERNAME_MIN} - {USERNAME_MAX} ký tự']
        elif not USERNAME_PATTERN.match(username):
            errors['username'] = ['Tên đăng nhập chứa ký tự không hợp lệ']
        else:
            result['username'] = username

    if errors:
        raise ValidationError('Dữ liệu cập nhật không hợp lệ', fields=errors)

    return result

def validate_change_password(data: dict) -> dict:
    """
    Validate dữ liệu đổi mật khẩu.

    Requires: old_password, new_password, confirm_password
    """

    errors = {}

    old_password = data.get('old_password', '')
    new_password = data.get('new_password', '')
    confirm_password = data.get('confirm_password', '')

    if not old_password:
        errors['old_password'] = ['Mật khẩu cũ là bắt buộc']

    if not new_password:
        errors['new_password'] = ['Mật khẩu mới là bắt buộc']    
    elif len(new_password) < PASSWORD_MIN:
        errors['new_password'] = [f'Mật khẩu mới phải có ít nhất {PASSWORD_MIN} ký tự']
    elif not _is_strong_password(new_password):
        errors['new_password'] = ['Mật khẩu phải có ít nhất 1 chữ hoa, 1 chữ thường và 1 số']
    elif new_password == old_password:
        errors['new_password'] = ['Mật khẩu mới không được trùng với mật khẩu cũ']

    if not confirm_password:
        errors['confirm_password'] = ['Xác nhận mật khẩu là bắt buộc']
    elif new_password and confirm_password != new_password:
        errors['confirm_password'] = ['Xác nhận mật khẩu không khớp']

    if errors:
        raise ValidationError('Dữ liệu đổi mật khẩu không hợp lệ', fields=errors)

    return {
        'old_password': old_password,
        'new_password': new_password,
    }

def validate_password_reset_request(data: dict) -> dict:
    """Validate yêu cầu reset mật khẩu qua email."""
    email = data.get('email', '').strip().lower()
    if not email or not _is_valid_email(email):
        raise ValidationError(
            'Email không hợp lệ', 
            fields={'email': ['Email không đúng định dạng']}
        )
    return {'email': email}

def validate_password_reset_confirm(data: dict) -> dict:
    """Validate token + mật khẩu mới khi đặt lại mật khẩu."""
    
    errors = {}

    token = data.get('token', '').strip()
    if not token:
        errors['token'] = ['Token là bắt buộc']

    new_password = data.get('new_password', '')
    if not new_password:
        errors['new_password'] = ['Mật khẩu mới là bắt buộc']
    elif len(new_password) < PASSWORD_MIN:
        errors['new_password'] = [f'Mật khẩu mới phải có ít nhất {PASSWORD_MIN} ký tự']
    elif not _is_strong_password(new_password):
        errors['new_password'] = ['Mật khẩu phải có ít nhất 1 chữ hoa, 1 chữ thường và 1 số']

    if errors:
        raise ValidationError('Dữ liệu đặt lại mật khẩu không hợp lệ', fields=errors)
    
    return {
        'token': token,
        'new_password': new_password,
    }

def validate_id_card_upload(files: dict) -> None:
    """
    Validate file ảnh minh chứng.

    Chỉ chấp nhận: JPG, PNG, PDF — tối đa 10 MB.
    Không trả dict vì view tự lấy file từ request.FILES.

    Raises:
        ValidationError: nếu file không hợp lệ
    """

    errors = {}

    if 'id_card_image' not in files:
        errors['id_card_image'] = ['Ảnh minh chứng là bắt buộc']
    else:
        f = files['id_card_image']
        if f.content_type not in ALLOWED_ID_CARD_TYPES:
            errors['id_card_image'] = ['Chỉ nhận file JPG, PNG hoặc PDF']
        elif f.size > MAX_ID_CARD_SIZE:
            errors['id_card_image'] = ['File tối đa 10MB']

    if errors:
        raise ValidationError('File không hợp lệ', files=errors)
    

# Helpers nội bộ
def _is_valid_email(email: str) -> bool:
    """Kiểm tra định dạng email cơ bản."""
    pattern = re.compile(r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$')
    return bool(pattern.match(email))

def _is_strong_password(password: str) -> bool:
    """
    Mật khẩu mạnh: ít nhất 1 chữ hoa, 1 chữ thường và 1 số.
    Độ dài tối thiểu đã kiểm tra trước khi gọi hàm.
    """

    has_upper = any(c.isupper() for c in password)
    has_lower = any(c.islower() for c in password)
    has_digit = any(c.isdigit() for c in password)
    return has_upper and has_lower and has_digit