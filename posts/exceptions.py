from accounts.exceptions import AppException

class PostException(AppException):
    """Ngoại lệ chung cho ứng dụng Posts."""
    pass

class PostNotFound(PostException):
    status_code = 404
    default_detail = 'Không tìm thấy bài viết này hoặc bài viết đã bị xóa.'
    default_code = 'POST_NOT_FOUND'

class CommentNotFound(PostException):
    status_code = 404
    default_detail = 'Không tìm thấy bình luận này.'
    default_code = 'COMMENT_NOT_FOUND'

class PostPermissionDenied(PostException):
    status_code = 403
    default_detail = 'Bạn không có quyền thực hiện hành động này.'
    default_code = 'PERMISSION_DENIED'
