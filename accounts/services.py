"""
accounts/services.py

Tầng Ghi cho app accounts — mọi logic Create/Update/Delete ở đây.

Quy ước tầng services (§1.2):
  - Xử lý toàn bộ business logic ghi dữ liệu
  - KHÔNG trả HTTP response
  - Có thể gọi selectors để đọc, nhưng không ngược lại
  - Raise custom exception từ exceptions.py khi có lỗi nghiệp vụ
  - Tên hàm bắt đầu bằng động từ: create_, update_, delete_, approve_, reject_
"""

import logging
from django.contrib.auth import authenticate, login, logout
from django.utils import timezone

from accounts.models import User, ArtistVerification, BlockList
from accounts.selectors import (
    check_email_exists,
    check_username_exists,
    get_user_by_email,
    has_pending_verification,
    get_verification_by_id,
)
from accounts.exceptions import (
    ValidationError,
    AlreadyExists,
    AuthenticationError,
    PermissionDenied,
    NotFound,
    AccountInactive,
)

logger = logging.getLogger(__name__)

# Authentication
def register_user(data: dict) -> User:
    """
    Tạo tài khoản người dùng mới.

    Args:
        data: dict đã validate từ validators.validate_register()
              Gồm: username, email, password

    Returns:
        User mới đã được lưu vào DB

    Raises:
        AlreadyExists: nếu email hoặc username đã tồn tại
    """

    # Kiểm tra trùng lặp trước khi tạo
    if check_email_exists(data['email']):
        raise AlreadyExists('Email này đã được đăng ký')
    
    if check_username_exists(data['username']):
        raise AlreadyExists('Tên đăng nhập này đã tồn tại')
    
    # create_user() tự động hash password
    user = User.objects.create_user(
        username=data['username'],
        email=data['email'],
        password=data['password'],
    )

    logger.info('New user registered: %s (%s)', user.username, user.email)
    return user

def login_user(request, dât: dict) -> User:
    """
    Xác thực và đăng nhập người dùng.

    Django tự tạo session và set cookie sessionid.

    Args:
        request: Django HttpRequest
        data:    dict đã validate, gồm email và password

    Returns:
        User đã đăng nhập

    Raises:
        AuthenticationError: nếu email/password sai
        AccountInactive: nếu tài khoản bị khóa
    """

    # Lấy user theo email
    user = get_user_by_email(data['email'])

    if user is None:
        # Vẫn chạy authenticate() để tránh timing attack
        raise AuthenticationError('Email hoặc mật khẩu không dúng')
    
    if not user.is_active:
        raise AccountInactive()
    
    # Xác thực password
    authenticate_user = authenticate(
        request,
        username=data['email'],
        password=data['password'],
    )

    if authenticate_user is None:
        raise AuthenticationError('Email hoặc mật khẩu không đúng')