"""
accounts/exceptions.py

Custom exceptions cho nghiệp vụ app accounts.

Quy ước: mỗi exception mang theo error_code để views map sang HTTP response.
Views chỉ bắt exception và gọi .to_response() — không chứa logic nghiệp vụ.
"""

class AppException(Exception):
    """Base class cho mọi custom exception nghiệp vụ."""
    def __init__(self, message: str, error_code: str = 'API_ERROR'):
        self.message = message
        self.error_code = error_code
        super().__init__(message)

class ValidationError(AppException):
    """Dữ liệu đầu vào không hợp lệ - HTTP 400."""

    def __init__(self, message: str = 'Dữ liệu không hợp lệ', fields: dict = None):
        self.fields = fields or {}
        super(). __init__(message, error_code='VALIDATION_ERROR')

class AuthenticationError(AppException):
    """Chưa đăng nhập hoặc session hết hạn - HTTP 401."""

    def __init__(self, message: str = 'Bạn cần đăng nhập'):
        super().__init__(message, error_code='AUTH_REQUIRED')

class PermissionDenied(AppException):
    """Đã đăng nhập nhưng không đủ quyền - HTTP 403."""
    
    def __init__(self, message: str = 'Bạn không có quyền thực hiện hành động này'):
        super().__init__(message, error_code='PERMISSION_DENIED')

class AccountInactive(AppException):
    """Tài khoản bị khoá - HTTT 403."""

    def __init__(self, message: str = 'Tài khoản của bạn đã bị khoá'):
        super().__init__(message, error_code='ACCOUNT_INACTIVE')

class NotFound(AppException):
    """Tài nguyên không tìm thấy - HTTP 404."""

    def __init__(self, message: str = 'Không tìm thấy'):
        super().__init__(message, error_code='NOT_FOUND')

class AlreadyExists(AppException):
    """Dữ liệu đã tồn tại - HTTP 409."""
    
    def __init__(self, message: str = 'Dữ liệu đã tồn tại'):
        super().__init__(message, error_code='ALREADY_EXISTS')

class BlockedError(AppException):
    """Hành động bị chặn do block policy - HTTP 403."""

    def __init__(self, message: str = 'Bạn không thể thực hiện hành động này'):
        super().__init__(message, error_code='BLOCKED')

class ArtistOnlyError(AppException):
    """Chỉ nghệ sĩ mới được thực hiện - HTTP 403."""

    def __init__(self, message: str = 'Chỉ nghệ sĩ mới thực hiện được hành động này'):
        super().__init__(message, error_code='ARTIST_ONLY')

class AdminOnlyError(AppException):
    """Chỉ admin mới được thực hiện - HTTP 403."""

    def __init__(self, message: str = 'Chỉ quản trị viên mới được thực hiện hành động này'):
        super().__init__(message, error_code='ADMIN_ONLY')