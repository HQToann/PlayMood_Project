from accounts.exceptions import AppException

#playlist không tồn tại hoặc không có quyền xem
class PlaylistNotFound(AppException):
    def __init__(self, message='Playlist không tồn tại'):
        super().__init__(message, error_code='NOT_FOUND')


#Không phải chủ playlist
class NotPlaylistOwner(AppException):
    def __init__(self, message='Bạn không có quyền thực hiện hành động này với playlist này'):
        super().__init__(message, error_code='PERMISSION_DENIED')


#bài hát này đã có trong playlist
class SongAlreadyInPlaylist(AppException):
    def __init__(self, message='Bài hát này đã có trong playlist'):
        super().__init__(message, error_code='ALREADY_EXISTS')


#bài hát này không có trong playlist
class SongNotInPlaylist(AppException):
    def __init__(self, message='Bài hát không có trong playlist này'):
        super().__init__(message, error_code='NOT_FOUND')


#dữ liệu reorder không hợp lệ (thiếu bài, sai ID)
class InvalidReorderData(AppException):
    def __init__(self, message='Dữ liệu sắp xếp lại không hợp lệ'):
        super().__init__(message, error_code='VALIDATION_ERROR')