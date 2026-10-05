"""
artists/exceptions.py

Custom exceptions cho nghiệp vụ app artists.
"""

from accounts.exceptions import AppException

class ArtistProfileNotFound(AppException):
    """
    Hồ sơ nghệ sĩ không tồn tại.
        User chưa phải artist hoặc chưa tạo profile - HTTP 404.
    """
    def __init__(self, message='Hồ sơ nghệ sĩ không tồn tại'):
        super().__init__(message, error_code='NOT_FOUND')

class ArtistProfileAlreadyExists(AppException):
    """
    User đã có ArtistProfile
        Không tạo thêm được - HTTP 409.
    """
    def __init__(self, message='Hồ sơ nghệ sĩ đã tồn tại'):
        super().__init__(message, error_code='ALREADY_EXISTS')

class NotArtistProfileOwner(AppException):
    """
    Không phải chủ hồ sơ
        Không được chỉnh sửa - HTTP 403.
    """
    def __init__(self, message='Bạn không có quyền thực hiện hành động này'):
        super().__init__(message, error_code='PERMISSION_DENIED')

class UserNotArtist(AppException):
    """
    User chưa có role='artist'
        Không thể tạo ArtistProfile - HTTP 403.
    """
    def __init__(self, message='Chỉ tài khoản nghệ sĩ mới được tạo hồ sơ nghệ sĩ'):
        super().__init__(message, error_code='ARTIST_ONLY')