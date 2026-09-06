from accounts.exceptions import AppException

class ChatException(AppException):
    """
    Lỗi cơ bản cho module Chat - HTTP 400
    """
    def __init__(self, message='Lỗi ứng dụng chat', error_code='CHAT_ERROR'):
        super().__init__(message, error_code=error_code)

class NotFriendsError(AppException):
    """
    Lỗi khi 2 người chưa phải là bạn bè (chưa follow 2 chiều) - HTTP 403
    """
    def __init__(self, message='Chỉ có thể nhắn tin với bạn bè (yêu cầu follow 2 chiều).'):
        super().__init__(message, error_code='NOT_FRIENDS')

class ConversationNotFoundError(AppException):
    """
    Lỗi khi không tìm thấy cuộc trò chuyện hoặc không có quyền truy cập - HTTP 404
    """
    def __init__(self, message='Không tìm thấy cuộc trò chuyện hoặc bạn không có quyền xem.'):
        super().__init__(message, error_code='NOT_FOUND')