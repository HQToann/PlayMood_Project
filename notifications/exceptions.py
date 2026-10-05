from accounts.exceptions import AppException


class NotificationNotFound(AppException):

    #thông báo không tồn tại hoặc không thuộc về user (404)
    def __init__(self, message='Thông báo không tồn tại'):
        super().__init__(message, error_code='NOT_FOUND')