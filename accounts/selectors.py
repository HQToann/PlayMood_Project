from django.db.models import QuerySet
from accounts.models import User, BlockList, ArtistVerification
from accounts.exceptions import NotFound


#truy vấn user
def get_user_by_id(user_id) -> User:
    #lấy theo UUID
    try:
        return User.objects.get(id=user_id, is_active=True)
    except User.DoesNotExist:
        raise NotFound('Người dùng không tồn tại')
    

def get_user_by_email(email: str) -> User | None:
    try:
        return User.objects.get(email__iexact=email)
    except User.DoesNotExist:
        return None


def get_public_profile(user_id, viewer=None) -> User:
    try:
        target = User.objects.get(id=user_id, is_active=True)

    except User.DoesNotExist:
        raise NotFound('Người dùng không tồn tại')
    

    if viewer and viewer.is_authenticated and is_blocked(viewer.id, target.id):
        raise NotFound('Người dùng không tồn tại')
    
    return target
    
def check_email_exists(email: str) -> bool:
    #kiểm tra xem email đã được đăng ký hay chưa
    return User.objects.filter(email__iexact=email).exists()


def check_username_exists(username: str) -> bool:
    #kiểm tra username đã tồn tại hay chưa
    return User.objects.filter(username__iexact=username).exists()


#truy vấn block
def is_blocked(viewer_id, target_id) -> bool:
    #kiếm tra viewer có bị target block hay không
    # target là người chặn, viewer là người bị chặn

    #Dùng trong:
    # get_public_profile()
    # song views (ẩn bài hát của người đã block)
    # comment service (cấm comment)
    # follow service (cấm follow)

    return BlockList.objects.filter(
        blocker_id=target_id,
        blocked_id=viewer_id,
    ).exists()

def list_blocked_users(user: User) -> QuerySet:
    #Danh sách những người user đã block
    return User.objects.filter(
        blocked_by__blocker=user,
    ).order_by('-blocked_by__created_at')


#try vấn xác minh nghệ sĩ
def get_my_verification(user: User) -> ArtistVerification | None:
    #lấy yêu cầu xác thực mới nhất  của user trả về None nếu chưa có
    return ArtistVerification.objects.filter(user=user).order_by('-created_at').first()


def list_pending_verifications() -> QuerySet:
    #danh sách yêu cầu xác thực đang chờ duyệt, dùng cho admin
    return ArtistVerification.objects.filter(
        status=ArtistVerification.STATUS_PENDING,
        ).select_related('user').order_by('created_at')

def get_verification_by_id(verification_id) -> ArtistVerification:
    #lấy ArtistVerification theo id
    try:
        return ArtistVerification.objects.select_related('user').get(id=verification_id)
    except ArtistVerification.DoesNotExist:
        raise NotFound('Yêu cầu xác thực không tồn tại')
    

def has_pending_verification(user: User) -> bool:
    #kiểm tra user có yêu cầu xác thực đang chờ hay không
    return ArtistVerification.objects.filter(
        user=user,
        status=ArtistVerification.STATUS_PENDING,
    ).exists()

def get_reset_token_by_value(token: str):
    """Lấy PasswordResetToken theo giá trị token. Trả None nếu không tìm thấy."""
    from accounts.models import PasswordResetToken
    try:
        return PasswordResetToken.objects.select_related('user').get(token=token)
    except PasswordResetToken.DoesNotExist:
        return None