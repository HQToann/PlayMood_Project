"""
- ArtistProfile: Hồ sơ nghệ sĩ mở rộng (stage_name, bio, cover_image riêng)
    + ArtistProfile là 1-1 với accounts.User (chỉ user cod role='artist' mới có profile)
    + Thống kê (play_count, like_count, comment_count...) không lưu trong model này,
    mà ddwuocj tính real-time qua selectors.py từ các bảng
    Song/Like/Rating/Comment/ListenHistory đã có sẵn trong app music tránh dữ liệu thừa và out-of-sync.
"""
import uuid
from django.db import models

class ArtistProfile(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4, editable=False,
    )

    user = models.OneToOneField(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='artist_profile',
        verbose_name='Nghệ sĩ',
    )

    stage_name = models.CharField(
        max_length=100,
        blank=True,
        default='',
        verbose_name='Tên nghệ danh',
    )

    bio = models.TextField(
        blank=True,
        default='',
        verbose_name='Giới thiệu nghệ sĩ',
    )

    website_url = models.CharField(
        max_length=225,
        blank=True,
        default='',
        verbose_name='Website',
    )

    facebook_url = models.CharField(
        max_length=255,
        default='',
        verbose_name='Facebook',
    )

    youtube_url = models.CharField(
        max_length=255,
        blank=True,
        default='',
        verbose_name='Youtube',
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'artists_artist_profile'
        ordering = ['-created_at']
        verbose_name = 'Hồ sơ nghệ sĩ'
        verbose_name_plural = 'Hồ sơ nghệ sĩ'

    def __str__(self):
        return f'{self.get_display_name()} ({self.user.username})'
    
    #trả tên nghệ danh fallback về display_name/username của User
    def get_display_name(self):
        return self.stage_name or self.user.get_display_name()
    

    """
    serialize ArtistProfile thành dict
    - viewer: User đang xem (để quyết định is_owner)
    - include_stats: có tính stats hay không luôn dùng selectors.get_artist_stast()
        + tầng selectors/views để tính không tính trong model này (tránh phụ thuộc ngược 
        vào selectors của app khác)
    """
    def to_dict(self, viewer=None, include_stats=False):
        data = {
            'id': str(self.id),
            'user': {
                'id': str(self.user_id),
                'username': self.user.username,
                'avatar': self.user.avatar.url if self.user.avatar else None,
            },
            'stage_name': self.stage_name,
            'display_name': self.get_display_name(),
            'bio': self.bio,
            'cover_image': self.user.cover.url if self.user.cover else None,
            'website_url': self.website_url,
            'facebook': self.facebook_url,
            'youtube': self.youtube_url,
            'created_at': self.created_at.isoformat(),
            'update_at': self.updated_at.isoformat(),
        }

        viewer_id = getattr(viewer, 'id', None)
        if viewer_id and getattr(viewer, 'is_authenticated', False):
            data['is_owner'] = str(viewer_id) == str(self.user_id)
        else:
            data['is_owner'] = False
        
        
        return data

from django.db.models.signals import pre_delete
from django.dispatch import receiver

@receiver(pre_delete, sender=ArtistProfile)
def downgrade_user_role_on_profile_delete(sender, instance, **kwargs):
    """
    Khi xóa ArtistProfile (ví dụ từ Admin), tự động cập nhật role của User 
    trở về 'user' bình thường. Dùng update() để tránh xung đột khi User 
    đang trong quá trình bị xóa (CASCADE delete).
    """
    try:
        if instance.user_id:
            from accounts.models import User
            User.objects.filter(id=instance.user_id, role='artist').update(role='user')
    except Exception as e:
        pass
