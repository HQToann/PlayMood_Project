import uuid
from django.db import models


class Notification(models.Model):
    TYPE_FOLLOW = 'follow'
    TYPE_LIKE = 'like'
    TYPE_COMMENT = 'comment'
    TYPE_REPLY = 'reply'
    TYPE_SYSTEM = 'system'
    TYPE_VERIFY_RESULT = 'verify_result'
    TYPE_CHOICES = [
        (TYPE_FOLLOW, 'Theo dõi mới'),
        (TYPE_LIKE, 'Lượt thích'),
        (TYPE_COMMENT, 'Bình luận mới'),
        (TYPE_REPLY, 'Trả lời bình luận'),
        (TYPE_SYSTEM, 'Hệ thống'),
        (TYPE_VERIFY_RESULT, 'Kết quả xác thực'),
    ]

    TARGET_SONG = 'song'
    TARGET_PLAYLIST = 'playlist'
    TARGET_COMMENT = 'comment'
    TARGET_USER = 'user'
    TARGET_CHOICES = [
        (TARGET_SONG, 'Bài hát'),
        (TARGET_PLAYLIST, 'Playlist'),
        (TARGET_COMMENT, 'Bình luận'),
        (TARGET_USER, 'Người dùng'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    recipient = models.ForeignKey(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='notifications',
        verbose_name='Người nhận',
        db_index=True,
    )

    sender = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sent_notifications',
        verbose_name='Người gửi',
    )

    notif_type = models.CharField(
        max_length=20,
        choices=TARGET_CHOICES,
        db_index=True,
        verbose_name='Loại',
    )

    #bắt buộc với mọi loại trừ system/verify_result, enforce ở services.py
    target_type = models.CharField(
        max_length=10,
        choices=TARGET_CHOICES,
        null=True,
        blank=True,
    )
    target_id = models.UUIDField(
        null=True,
        blank=True,
    )

    message = models.TextField(
        verbose_name='Nội dung'
    )
    is_read = models.BooleanField(
        default=False,
        db_index=True,
        verbose_name='Đã đọc',
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        verbose_name='Thời điểm',
    )

    class Meta:
        db_table = 'notifications_notification'
        ordering = ['-created_at']
        verbose_name = 'Thông báo'
        verbose_name_plural = 'Thông báo'
        indexes = [
            #hỗ trợ 2 truy vấn phổ biến nhất: list theo recipient và đếm unread
            models.Index(fields=[
             'recipient',
             'is_read',
             'created_at',
            ], name='notif_recipient_read_idx'),
        ]

    def __str__(self):
        state = 'read' if self.is_read else 'unread'
        return f'{self.recipient.username}: {self.notif_type} ({state})'
    
    def to_dict(self):
        return {
            'id': str(self.id),
            'sender': {
                'id': str(self.sender_id),
                'username': self.sender.username,
                'display_name': self.sender.get_display_name(),
                'avatar': self.sender.avatar.url if self.sender.avatar else None,
            } if self.sender_id else None,
            'notif_type': self.notif_type,
            'target_type': self.target_type,
            'target_id': str(self.target_id) if self.target_id else None,
            'message': self.message,
            'is_read': self.is_read,
            'created_at': self.created_at.isoformat(),
        }


