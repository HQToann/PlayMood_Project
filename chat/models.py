import uuid
from django.db import models
from accounts.models import User
from music.models import Song
from music_platform.utils import optimize_cloudinary_url

class Conversation(models.Model):
    """
    Lưu trữ thông tin cuộc trò chuyện giữa 2 (hoặc nhiều) người.
    Trong phạm vi ứng dụng chat 1-1, số lượng participants thường là 2.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    participants = models.ManyToManyField(
        User,
        related_name='conversations',
        verbose_name='Người tham gia',
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Ngày tạo',
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Cập nhật lần cuối',
    )

    class Meta:
        db_table = 'chat_conversation'
        verbose_name = 'Cuộc trò chuyện'
        verbose_name_plural = 'Cuộc trò chuyện'
        ordering = ['-updated_at']

    def __str__(self):
        return f"Conversation {self.id}"

    def to_dict(self, viewer=None):
        """
        Serialize Conversation thành dict.
        viewer: truyền vào User hiện tại để tự động lấy ra người kia (other_user).
        """

        data = {
            'id': str(self.id),
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
        }

        # Nếu biết ai đang xem tìm người còn lại trong cuộc trò chuyện
        if viewer:
            other_participants = self.participants.exclude(id=viewer.id)
            if other_participants.exists():
                other = other_participants.first()
                data['other_user'] = other.to_dict()

        return data

class Message(models.Model):
    """
    Lưu trữ thông tin chi tiết của 1 tin nhắn.
    Bao gồm text, ảnh, bài hát chia sẻ và thả tim (reactions).
    """
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name='messages',
        verbose_name='Cuộc trò chuyện',
    )

    sender = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null = True,
        verbose_name='Người gửi',
    )

    # Nội dung text (có thể rỗng nếu chỉ gửi ảnh/nhạc)
    content = models.TextField(
        blank=True,
        default='',
        verbose_name='Nội dung',
    )

    # URL ảnh được lưu trên cloudinary
    image_url = models.URLField(
        blank=True,
        null=True,
        verbose_name='Ảnh đính kèm',
    )

    # Chia sẻ bài hát (có thể tuỳ biến thêm Playlist nếu cần)
    shared_song = models.ForeignKey(
        Song,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Bài hát chia sẻ'
    )

    # Lưu danh sách thả cảm xúc dạng JSON dict
    reactions = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='Cảm xúc',
    )

    # Trạng thái đã xem tin nhắn hay chưa
    is_read = models.BooleanField(
        default=False,
        verbose_name='Đã xem',
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        verbose_name='Ngày gửi',
    )

    class Meta:
        db_table='chat_message'
        verbose_name='Tin nhắn'
        verbose_name_plural='Tin nhắn'
        ordering = ['created_at'] # Xếp tin cũ lên trên, tin mới ở dưới

    def __str__(self):
        return f"Message {self.id} by {self.sender}"

    def to_dict(self):
        """
        Serialize Message thành dict cho API.
        """
        return {
            'id': str(self.id),
            'conversation_id': str(self.conversation_id),
            'sender': self.sender.to_dict() if self.sender else None,
            'content': self.content,
            'image_url': optimize_cloudinary_url(self.image_url, 'image') if self.image_url else None,
            'shared_song': self.shared_song.to_dict() if self.shared_song else None,
            'reactions': self.reactions,
            'is_read': self.is_read,
            'created_at': self.created_at.isoformat(),
        }