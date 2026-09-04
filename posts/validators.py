from accounts.exceptions import ValidationError
from .models import PostReaction

def validate_post_creation(content: str, has_media: bool, has_shared_song: bool = False):
    """Bài viết phải có chữ, ảnh, hoặc bài hát. Không được để trống hoàn toàn."""
    if not content.strip() and not has_media and not has_shared_song:
        raise ValidationError(
            'Dữ liệu không hợp lệ',
            fields={'content': ['Vui lòng nhập nội dung, đính kèm hình ảnh/video hoặc chia sẻ bài hát.']}
        )

def validate_reaction_type(reaction: str):
    """Đảm bảo cảm xúc gửi lên nằm trong 6 loại cho phép."""
    valid_types = [choice[0] for choice in PostReaction.REACTION_CHOICES]
    if reaction not in valid_types:
        raise ValidationError(
            'Cảm xúc không hợp lệ',
            fields={'reaction_type': [f'Cảm xúc phải là một trong {valid_types}']}
        )
