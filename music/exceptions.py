"""
music/exceptions.py

Custom exceptions cho nghiệp vụ app music.
"""

from accounts.exceptions import AppException

class SongNotFound(AppException):
    """Bài hát không tồn tại hoặc đã bị ẩn - HTTP 404."""
    def __init__(self, message='Bài hát không tồn tại'):
        super().__init__(message, error_code='NOT_FOUND')

class SongNotPublished(AppException):
    """Bài hát chưa được phát hành - HTTP 404."""
    def __init__(self, message='Bài hát không tồn tại'):
        super().__init__(message, error_code='NOT_FOUND')
class DownloadNotAllowed(AppException):
    """Bài hát không cho phép tải về - HTTP 403."""
    def __init__(self, message='Bài hát này không cho phép tải về'):
        super().__init__(message, error_code='DOWNLOAD_NOT_ALLOWED')

class NotSongOwner(AppException):
    """Không phải chủ bài hát - HTTP 403."""
    def __init__(self, message='Bạn không có quyền thực hiện hành động này với bài hát này'):
        super().__init__(message, error_code='PREMISSION_DENIED')

class SongAlreadyPublished(AppException):
    """Bài hát đã published, không thể publish lại - HTTP 400."""
    def __init__(self, message='Bài hát đã được phát hành'):
        super().__init__(message, error_code='ALREADY_PUBLISHED')

class AdminHiddenSongCannotBePublished(AppException):
    """Bài hát bị khoá bởi Admin, nghệ sĩ không thể mở khoá - HTTP 403."""
    def __init__(self, message='Bài hát này đã bị khoá bởi Quản trị viên do vi phạm chính sách'):
        super().__init__(message, error_code='ADMIN_LOCKED')

class CommentNotFound(AppException):
    """Bình luận không tồn tại hoặc ẩn - HTTP 404."""
    def __init__(self, message='Bình luận không tồn tại'):
        super().__init__(message, error_code='NOT_FOUND')

class NotCommentOwner(AppException):
    """Không phải chủ bình luận - HTTP 404."""
    def __init__(self, message='Bạn không có quyền xoá bình luận này'):
        super().__init__(message, error_code='PERMISSION_DENIED')

class GenreNotFound(AppException):
    """Thể loại không tồn tại - HTTP 403."""
    def __init__(self, message='Thể loại không tồn tại'):
        super().__init__(message, error_code='NOT_FOUND')

class GenreHasSongs(AppException):
    """Không thể xoá thể loại đang có bài hát - HTTP 404."""
    def __init__(self, message='Không thể xoá thể loại đang có bài hát'):
        super().__init__(message, error_code='GENRE_HAS_SONGS')

class BlockedByArtist(AppException):
    """Bị nghệ sĩ block, không thể bình luận - HTTP 403."""
    def __init__(self, message='Bạn không thể thực hiện hành động này'):
        super().__init__(message, error_code='BLOCKED')

class ReportNotFound(AppException):
    """Báo cáo không tồn tại - HTTP 404."""
    def __init__(self, message='Báo cáo không tồn tại'):
        super().__init__(message, error_code='NOT_FOUND')

class InvalidParentComment(AppException):
    """Parent comment không hợp lệ (khác bài hát hoặc reply) - HTTP 400."""
    def __init__(self, message='Bình luận cha không hợp'):
        super().__init__(message, error_code='INVALID_PARENT')

class AlbumNotFound(AppException):
    """Album không tồn tại - HTTP 404."""
    def __init__(self, message='Album không tồn tại'):
        super().__init__(message, error_code='NOT_FOUND')

class NotAlbumOwner(AppException):
    """Không phải chủ album - HTTP 403."""
    def __init__(self, message='Bạn không có quyền thực hiện hành động này với album này'):
        super().__init__(message, error_code='PERMISSION_DENIED')

class SongAlreadyInAlbum(AppException):
    """Bài hát đã có trong album - HTTP 400."""
    def __init__(self, message='Bài hát đã có trong album này'):
        super().__init__(message, error_code='ALREADY_EXISTS')