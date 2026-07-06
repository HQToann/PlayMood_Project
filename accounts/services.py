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

def login_user(request, data: dict) -> User:
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
    
    # Tạo session
    login(request, authenticate_user)
    logger.info('User logger in: %s', authenticate_user.username)
    return authenticate_user

def logout_user(request) -> None:
    """
    Đăng xuất — xóa session khỏi DB và clear cookie.

    Django's logout() gọi session.flush() bên trong.
    """
    username = request.user.username
    logout(request)
    logger.info('User logger out: %s', username)

# Profile management
def update_profile(user: User, data: dict) -> User:
    """
    Cập nhật thông tin hồ sơ cá nhân.

    Args:
        user: User cần cập nhật
        data: dict đã validate từ validators.validate_update_profile()
              Có thể chứa: display_name, bio, username

    Returns:
        User sau khi cập nhật

    Raises:
        AlreadyExists: nếu username mới đã tồn tại
    """
    if 'username' in data:
        if (
            data['username'].lower() != user.username.lower()
            and check_username_exists(data['username'])
        ):
            raise AlreadyExists('Tên đăng nhập này đã tồn tại')
    
    for field, value in data.items():
        setattr(user, field, value)

    user.save(update_fields=list(data.keys()) + ['updated_at'])
    logger.info('Profile updated: %s', user.username)
    return user

def update_images(user: User, avatar_file=None, cover_file=None) -> User:
    """
    Cập nhật ảnh đại diện và/hoặc ảnh bìa.

    Args:
        user:        User cần cập nhật
        avatar_file: File ảnh đại diện (optional)
        cover_file:  File ảnh bìa (optional)

    Returns:
        User sau khi cập nhật
    """
    updated_fields = ['updated_at']

    if avatar_file:
        if user.avatar:
            try:
                user.avatar.delete(save=False)
            except Exception:
                pass
        user.avatar = avatar_file
        updated_fields.append('avatar')
        logger.info('Avatar updated: %s', user.username)

    if cover_file:
        if user.cover:
            try:
                user.cover.delete(save=False)
            except Exception:
                pass
        user.cover = cover_file
        updated_fields.append('cover')
        logger.info('Cover updated: %s', user.username)

    user.save(update_fields=updated_fields)
    return user

def update_privacy(user: User, is_private: bool) -> User:
    """Cập nhật chế độ riêng tư."""
    user.is_private = is_private
    user.save(update_fields=['is_private', 'updated_at'])
    return user

def change_password(request, user: User, data: dict) -> None:
    """
    Đổi mật khẩu khi đã đăng nhập.

    Django tự động update session hash sau khi đổi mật khẩu
    (tránh logout toàn bộ thiết bị khác nếu dùng update_session_auth_hash).

    Args:
        request: Django HttpRequest (cần để update session)
        user:    User đang đăng nhập
        data:    dict đã validate, gồm old_password và new_password

    Raises:
        AuthenticationError: nếu old_password sai
    """

    from django.contrib.auth import update_session_auth_hash

    if not user.check_password(data['old_password']):
        raise AuthenticationError('Mật khẩu cũ không đúng')
    
    user.set_password(data['new_password'])
    user.save(update_fields=['password', 'updated_at'])

    # Giữ session hiện tại hợp lệ sau khi đổi mật khẩu
    update_session_auth_hash(request, user)
    logger.info('Password changed: %s', user.username)

# Block management
def toggle_block(blocker: User, blocked_id) -> dict:
    """
    Toggle block/unblock một user.

    Nếu chưa block → tạo BlockList record → trả {'action': 'blocked'}
    Nếu đã block   → xóa BlockList record → trả {'action': 'unblocked'}

    Args:
        blocker:    User thực hiện block
        blocked_id: UUID của user bị block

    Raises:
        NotFound:        nếu blocked_id không tồn tại
        ValidationError: nếu tự block bản thân
    """

    if str(blocker.id) == str(blocked_id):
        raise ValidationError('Bạn không thể tự chặn bản thân')
    
    try:
        blocked = User.objects.get(id=blocked_id, is_active=True)
    except User.DoesNotExist:
        raise NotFound('Người dùng không tồn tại')
    
    block_record, created = BlockList.objects.get_or_create(
        blocker=blocker,
        blocked=blocked,
    )

    if not created:
        # Đã block -> unblock
        block_record.delete()
        return {'action': 'unblocked', 'blocked_user_id': str(blocked_id)}
    
    return {'action': 'blocked', 'blocked_user_id': str(blocked_id)}

# Artist Verification
def submit_verification(user: User, data: dict, id_card_file) -> ArtistVerification:
    """
    Nộp yêu cầu xác thực nghệ sĩ.

    Args:
        user:         User nộp yêu cầu
        data:         dict gồm real_name và note
        id_card_file: file ảnh CMND/CCCD từ request.FILES

    Raises:
        PermissionDenied: nếu user đã là artist
        AlreadyExists:    nếu đã có yêu cầu pending
    """

    if user.role == User.ROLE_ARTIST:
        raise PermissionDenied('Tài khoản của bạn đã là nghệ sĩ')
    
    if has_pending_verification(user):
        raise AlreadyExists('Bạn đã có yêu cầu xác thực đang chờ duyệt')
    
    verification = ArtistVerification.objects.create(
        user=user,
        real_name=data.get('real_name', '').strip(),
        note=data.get('note', '').strip(),
        id_card_image=id_card_file,
    )

    logger.info('Artist verification submitted: user=%s', user.username)
    return verification

def approve_verification(verification_id, admin: User) -> ArtistVerification:
    """
    Admin duyệt yêu cầu xác thực → tự động nâng role user lên 'artist'.

    Raises:
        PermissionDenied: nếu caller không phải admin
        ValidationError:  nếu verification không ở trạng thái pending
    """

    if admin.role != User.ROLE_ADMIN:
        raise PermissionDenied('Chỉ admin mới được duyệt yêu cầu')
    
    verification = get_verification_by_id(verification_id)

    if verification.status != ArtistVerification.STATUS_PENDING:
        raise ValidationError(
            'Chỉ có thể duyệt yêu cầu đang ở trạng thái pending',
            fields={'status': ['Yêu cầu đang ở trạng thái pending']},
        )
    
    # Cập nhật verification
    verification.status = ArtistVerification.STATUS_APPROVED
    verification.reviewed_by = admin
    verification.reviewed_at = timezone.now()
    verification.save(update_fields=['status', 'reviewed_by', 'reviewed_at'])

    # Nâng cấp role user
    User.objects.filter(id=verification.user_id).update(role=User.ROLE_ARTIST)

    # Tự động tạo hồ sơ nghệ sĩ
    from artists.services import create_artist_profile
    user = User.objects.get(id=verification.user_id)
    try:
        create_artist_profile(user, {'stage_name': verification.real_name})
    except Exception as e:
        logger.warning('Could not auto-create artist profile for user %s: %s', user.username, str(e))

    logger.info(
        'Verification approved: user=%s, admin=%s',
        verification.user.username,
        admin.username,
    )
    return verification

def reject_verification(verification_id, admin: User, reason: str = '') -> ArtistVerification:
    """
    Admin từ chối yêu cầu xác thực.

    Args:
        verification_id: UUID của ArtistVerification
        admin:           User admin thực hiện
        reason:          Lý do từ chối (ghi vào note)

    Raises:
        PermissionDenied: nếu caller không phải admin
        ValidationError:  nếu verification không ở trạng thái pending
    """

    if admin.role != User.ROLE_ADMIN:
        raise PermissionDenied('Chỉ admin mới được từ chối yêu cầu')
    
    verification = get_verification_by_id(verification_id)

    if verification.status != ArtistVerification.STATUS_PENDING:
        raise ValidationError(
            'Chỉ có thể từ chối yêu cầu đang ở trạng thái pending',
            fields={'status': ['Yêu cầu không ở trạng thái pending']},
        )
    
    verification.status = ArtistVerification.STATUS_REJECTED
    verification.reviewed_by = admin
    verification.reviewed_at = timezone.now()
    if reason:
        verification.note = f'{verification.note}\n[Lý do từ chối]: {reason}'.strip()
    verification.save(update_fields=['status', 'reviewed_by', 'reviewed_at', 'note'])
    
    logger.info(
        'Verification rejected: user=%s, admin=%s',
        verification.user.username,
        admin.username,
    )
    return verification