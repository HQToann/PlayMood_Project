from accounts.exceptions import ValidationError
from music.models import Song

def validate_message_content(content: str, image_url: str, shared_song_id: str):
    """
    Kiểm tra tính hợp lệ của tin nhắn:
    Phải có ít nhất 1 trong 3 thứ: text, hình ảnh, hoặc chia sẻ bài hát.
    """
    if not content and not image_url and not shared_song_id:
        raise ValidationError(
            'Tin nhắn không hợp lệ',
            fields={
                'content': ['Tin nhắn phải có nội dung chữ, ảnh hoặc bài hát đính kèm']
            }
        )

    if shared_song_id:
        # Kiểm tra xem bài hát có tồn tại không
        if not Song.objects.filter(id=shared_song_id).exists():
            raise ValidationError(
                'Bài hát không hợp lệ',
                fields={
                    'shared_song_id': ['Bài hát đính kèm không tồn tại hoặc đã bị xoá']
                }
            )