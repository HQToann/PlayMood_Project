"""
social/models.py

Models cho app social:
    - Follow: Quan hệ theo dõi giữa 2 User
    - Mood: Trạng thái tâm trạng hiện tại của User, có thể gắn kèm bài hát
    - FriendActivity: Log hoạt động (nghe nhạc, like, mood..) để hiện thị Feed

Tất cả PK là UUIDField theo quy ước chung của hệ thống.
"""

import uuid
from django.db import models
from django.utils import timezone

class Follow(models.Model):
    """
    Quan hệ theo dõi - follower theo dõi following
    """
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    follower = models.ForeignKey(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='following', # user.following.all = những người user đang theo dõi
        verbose_name='Người theo dõi',
    )

    following = models.ForeignKey(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='followers', # user.followers.all() = những người đang theo dõi User
        verbose_name='Người được theo dõi',
    )

    created_at = models.DateTimeField(
        auto_now_add=True, 
        verbose_name='Ngày theo dõi',
    )

    class Meta:
        db_table = 'social_follow'
        unique_together = [('follower', 'following')]
        ordering = ['-created_at']
        verbose_name = 'Theo dõi'
        verbose_name_plural = 'Theo dõi'

    def __str__(self):
        return f'{self.follower.username} -> follow -> {self.following.username}'

class FollowRequest(models.Model):
    """
    Yêu cầu kết bạn - dành cho quan hệ User <-> User (không áp dụng khi target là Artist).
    Vòng đời: sender gửi -> receiver nhận thông báo -> accept (tạo Follow 2 chiều) hoặc reject/cancel.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    sender = models.ForeignKey(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='sent_follow_requests',
        verbose_name='Người gửi yêu cầu',
    )
    receiver = models.ForeignKey(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='received_follow_requests',
        verbose_name='Người nhận yêu cầu',
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Ngày gửi')

    class Meta:
        db_table = 'social_follow_request'
        unique_together = [('sender', 'receiver')]
        ordering = ['-created_at']
        verbose_name = 'Yêu cầu kết bạn'
        verbose_name_plural = 'Yêu cầu kết bạn'

    def __str__(self):
        return f'{self.sender.username} -> request -> {self.receiver.username}'

    def to_dict(self):
        return {
            'id': str(self.id),
            'sender': {
                'id': str(self.sender.id),
                'username': self.sender.username,
                'display_name': self.sender.get_display_name(),
                'avatar': self.sender.avatar.url if self.sender.avatar else None,
            },
            'receiver': {
                'id': str(self.receiver.id),
                'username': self.receiver.username,
                'display_name': self.receiver.get_display_name(),
                'avatar': self.receiver.avatar.url if self.receiver.avatar else None,
            },
            'created_at': self.created_at.isoformat(),
        }


class MoodTheme(models.Model):
    """
    Bản màu chủ đề (Theme) do Admin định nghĩa.
    Dùng để gắn màu cho MoodType hoặc cho người dùng tự chọn khi viết status tự do.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(
        max_length=100, unique=True, verbose_name='Tên bản màu',
        help_text='VD: Bản màu Vàng Tươi'
    )
    color_hex = models.CharField(
        max_length=30, default='#FFFFFF', verbose_name='Màu chính (Mã Hex)',
        help_text='Dùng làm màu chữ cho tag. VD: #FBBF24'
    )
    gradient_from = models.CharField(
        max_length=30, default='#FFD194', verbose_name='Gradient Bắt đầu',
        help_text='Dùng làm màu nền. VD: #FFD194'
    )
    gradient_to = models.CharField(
        max_length=30, default='#70E1F5', verbose_name='Gradient Kết thúc',
        help_text='VD: #70E1F5'
    )
    is_active = models.BooleanField(default=True, verbose_name='Kích hoạt')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'social_mood_theme'
        ordering = ['name']
        verbose_name = 'Chủ đề màu'
        verbose_name_plural = 'Chủ đề màu'

    def __str__(self):
        return self.name

    def to_dict(self):
        return {
            'id': str(self.id),
            'name': self.name,
            'color_hex': self.color_hex,
            'gradient_from': self.gradient_from,
            'gradient_to': self.gradient_to,
        }


class MoodType(models.Model):
    """
    Loại cảm xúc - do Admin quản lý.
    Frontend chỉ cần gọi API GET /api/v1/social/mood-types/ để render danh sách.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    name = models.CharField(
        max_length=100,
        unique=True,
        verbose_name='Tên cảm xúc',
        help_text='VD: Vui vẻ, Buồn man mác, Thư giãn...',
    )

    emoji = models.CharField(
        max_length=10,
        verbose_name='Emoji',
        help_text='Emoji đại diện cho cảm xúc này',
    )

    description = models.CharField(
        max_length=200,
        blank=True,
        default='',
        verbose_name='Mô tả ngắn',
        help_text='VD: Tràn đầy năng lượng',
    )

    theme = models.ForeignKey(
        MoodTheme,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='mood_types',
        verbose_name='Chủ đề màu (Theme)',
        help_text='Gắn một bản màu cho cảm xúc này'
    )

    order = models.PositiveSmallIntegerField(
        default=0,
        verbose_name='Thứ tự hiển thị',
        help_text='Số nhỏ hơn sẽ hiển thị trước',
    )

    is_active = models.BooleanField(
        default=True,
        verbose_name='Đang kích hoạt',
        help_text='Bỏ tick để ẩn cảm xúc này khỏi frontend',
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'social_mood_type'
        ordering = ['order', 'name']
        verbose_name = 'Loại cảm xúc'
        verbose_name_plural = 'Loại cảm xúc'

    def __str__(self):
        return f'{self.emoji} {self.name}'

    def to_dict(self):
        return {
            'id': str(self.id),
            'name': self.name,
            'emoji': self.emoji,
            'description': self.description,
            'theme': self.theme.to_dict() if self.theme else None,
            'order': self.order,
        }


class Mood(models.Model):
    """
    Trạng thái cảm xúc hiên tại của User - có thể gắn kèm bài hát
    Business rule quan trọng:
        - Mỗi User chỉ có 1 Mood tài 1 thời điểm
        - Mood có thể hết hạn (Không còn hiển thị)
        - Cập nhật Mood mới, không tạo nhiều bản ghi rác
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    user = models.OneToOneField(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='mood',
        verbose_name='Người dùng',
    )

    status_text = models.CharField(
        max_length=200,
        blank=True,
        default='',
        verbose_name='Trạng thái'
    )

    # Loại cảm xúc do admin tạo (tuỳ chọn)
    mood_type = models.ForeignKey(
        'social.MoodType',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='moods',
        verbose_name='Loại cảm xúc',
    )

    # Bài hát gắn kèm Mood (tuỳ chọn)
    song = models.ForeignKey(
        'music.Song',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='moods',
        verbose_name='Bài hát đính kèm',
    )

    theme = models.ForeignKey(
        MoodTheme,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='moods',
        verbose_name='Chủ đề màu tuỳ chọn',
        help_text='Màu do user tự chọn khi viết custom mood'
    )

    expires_at = models.DateTimeField(verbose_name='Hết hạn lúc')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Ngày tạo')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Cập nhật lần cuối')

    class Meta:
        db_table = 'social_mood'
        ordering = ['-updated_at']
        verbose_name = 'Tâm trạng'
        verbose_name_plural = 'Tâm trạng'

    def __str__(self):
        return f'{self.user.username}: {self.status_text[:30]}'
    
    def is_expired(self) -> bool:
        """Kiểm tra Mood đã hết hạn hay chưa"""
        return timezone.now() >= self.expires_at
    
    def to_dict(self):
        return {
            'id': str(self.id),
            'user': {
                'id': str(self.user_id),
                'username': self.user.username,
                'display_name': self.user.get_display_name(),
                'avatar': self.user.avatar.url if self.user.avatar else None,
            },
            'mood_type': self.mood_type.to_dict() if self.mood_type_id else None,
            'status_text': self.status_text,
            'song': {
                'id': str(self.song_id),
                'title': self.song.title,
                'artist_display_name': self.song.artist.get_display_name(),
                'cover_image': self.song.cover_image.url if self.song.cover_image else None,
            } if self.song_id else None,
            'theme': self.theme.to_dict() if self.theme_id else None,
            'expires_at': self.expires_at.isoformat(),
            'is_expired': self.is_expired(),
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
        }
    
class FriendActivity(models.Model):
    """
    Log hoạt động của User - dùng để hiển thị Feed cho nhưngz người follow họ
    Xác định các loại hoạt động:
        - playing: vừa nghe một bài
        - liked: vừa thích một bài
        - mood: vừa cập nhật tâm trạng mới
    """

    TYPE_PLAYING = 'playing'
    TYPE_LIKED = 'liked'
    TYPE_MOOD = 'mood'
    TYPE_CHOICES = [
        (TYPE_PLAYING, 'Đang nghe'),
        (TYPE_LIKED, 'Đã thích'),
        (TYPE_MOOD, 'Cập nhật tâm trạng'),
    ]

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    user = models.ForeignKey(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='friend_activities',
        verbose_name='Người dùng',
        db_index=True,
    )

    activity_type = models.CharField(
        max_length=10,
        choices=TYPE_CHOICES,
        db_index=True,
    )

    song = models.ForeignKey(
        'music.Song',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='friend_activities',
        verbose_name='Bài hát liên quan',
    )

    # Lưu lại status_text của Mood tại thời điểm tạo activity
    extra_text = models.CharField(
        max_length=200,
        blank=True,
        default='',
        verbose_name='Nội dung bổ sung',
    )

    created_at = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='Thời điểm')

    class Meta:
        db_table = 'social_friend_activity'
        ordering = ['-created_at']
        verbose_name = 'Hoạt động bạn bè'
        verbose_name_plural = 'Hoạt động bạn bè'
        indexes = [
            # Composite index hỗ trợ query Feed: lấy hoạt động của nhiều user, sắp xếp theo thời gian
            models.Index(fields=['user', 'created_at'], name='activity_user_time_idx'),
        ]

    def __str__(self):
        return f'{self.user.username} - {self.activity_type} - {self.created_at}'
    
    def to_dict(self):
        data = {
            'id': str(self.id),
            'user': {
                'id': str(self.user_id),
                'username': self.user.username,
                'display_name': self.user.get_display_name(),
                'avatar': self.user.avatar.url if self.user.avatar else None,
            },
            'activity_type': self.activity_type,
            'extra_text': self.extra_text,
            'created_at': self.created_at.isoformat(),
        }
        if self.song_id:
            data['song'] = {
                'id': str(self.song_id),
                'title': self.song.title,
                'artist_display_name': self.song.artist.get_display_name(),
                'cover_image': self.song.cover_image.url if self.song.cover_image else None,
            }
        else:
            data['song'] = None
        return data