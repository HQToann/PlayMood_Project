from accounts.exceptions import AppException


#không thể tự follow bản thân (404)
class CannotFollowSelf(AppException):
    def __init__(self, message='Không thể tự theo dõi bản thân'):
        super().__init__(message, error_code='VALIDATION_ERROR')


#User muốn follow không tồn tại (404)
class FollowTargetNotFound(AppException):
    def __init__(self, message='Người dùng không tồn tại'):
        super().__init__(message, error_code='NOT_FOUND')


#không thể follow do bị block (403)
class BlockedFollowError(AppException):
    def __init__(self, message='Không thể thực hiện hành động này'):
        super().__init__(message, error_code='BLOCKED')


#User chưa có Mood nào (404)
class MoodNotFound(AppException):
    def __init__(self, message='Chưa có tâm trạng nào được thiết lập'):
        super().__init__(message, error_code='NOT_FOUND')