"""
accounts/models.py

Models cho app accounts:
  - User: kế thừa AbstractUser, dùng UUID làm PK, thêm role/is_private/avatar
  - ArtistVerification: yêu cầu xác thực trở thành nghệ sĩ
  - BlockList: danh sách người dùng bị chặn

Tất cả PK là UUIDField theo quy ước chung của hệ thống (§12.1).
"""

import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    """
    Custom User model thay thế User mặc định của Django.

    Lý do kế thừa AbstractUser thay vì AbstractBaseUser:
    - Giữ nguyên toàn bộ hệ thống quyền Django (is_staff, is_superuser)
    - Giữ groups, permissions cho Django Admin
    - Chỉ cần override những gì cần thiết

    Trường email là định danh đăng nhập (USERNAME_FIELD = 'email').
    Trường username vẫn giữ để hiển thị (unique handle).
    """

    # Phân loại role
    ROLE_USER = 'user'
    ROLE_ARTIST = 'artist'
    ROLE_ADMIN = 'admin'
    ROLE_CHOICES = [
        (ROLE_USER, 'Người dùng'),
        (ROLE_ARTIST, 'Nghệ sĩ'),
        (ROLE_ADMIN, 'Quản trị viên'),
    ]

    # Override PK: dùng UUID thay BigAutoInt
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name='ID',
    )

    # Email là định danh đăng nhập
    email = models.EmailField(
        unique=True,
        verbose_name='Email',
    )

    # Username vẫn bắt buộc
    username = models.CharField(
        max_length=50,
        unique=True,
        verbose_name='Tên đăng nhập',
    )

    # Tên hiển thị - có thể trùng
    display_name = models.CharField(
        max_length=100,
        blank=True,
        default='',
        verbose_name='Tên hiển thị',
    )

    # Avatar lưu trên Cloudinary
    avatar = models.ImageField(
        upload_to='avatars/users/',
        blank=True,
        null=True,
        verbose_name='Ảnh đại diện',
    )

    # Giới thiệu bản thân
    bio = models.TextField(
        blank=True,
        default='',
        verbose_name='Giới thiệu',
    )

    # Phân quyền nghiệp vụ
    role = models.CharField(
        max_length=10,
        choices=ROLE_CHOICES,
        default=ROLE_USER,
        verbose_name='Vai trò',
        db_index=True,
    )

    # Chế độ riêng tư
    is_private = models.BooleanField(
        default=False,
        verbose_name='Chế độ riêng tư',
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Ngày tạo')
    updated_at = models.DateTimeField(auto_now= True, verbose_name='Cập nhật lần cuối')

    # Dùng email làm field đăng nhập chính
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username'] # Bắt buộc khi dùng createsuperuser

    class Meta:
        db_table = 'accounts_user'
        verbose_name = 'Người dùng'
        verbose_name_plural = 'Người dùng'
        ordering = ['-created_at']
    
    def __str__(self):
        return f'{self.username} ({self.email})'
    
    def get_display_name(self):
        """Trả tên hiển thị, fallback về username nếu chưa đặt."""
        return self.display_name or self.username
    
    def to_dict(self, include_private=False):
        """
        Serialize User thành dict — dùng trong views khi trả JsonResponse.

        Args:
            include_private: nếu True, bao gồm cả email và các trường nhạy cảm 
            (chỉ dùng khi trả cho chính user đó hoặc admin)
        """

        data = {
            'id': str(self.id),
            'username': self.username,
            'display_name': self.get_display_name(),
            'avatar': self.avatar.url if self.avatar else None,
            'bio': self.bio,
            'role': self.role,
            'is_private': self.is_private,
            'created_at': self.created_at.isoformat(),
        }
        if include_private:
            data['email'] = self.email
        return data

class ArtistVerification(models.Model):
    """
    Yêu cầu xác thực tài khoản nghệ sĩ.

    User nộp yêu cầu kèm ảnh . Admin duyệt/từ chối.
    Khi approved, user.role tự động chuyển thành 'artist'.

    Lưu ý bảo mật: file phải lưu private (không public URL).
    Trong Cloudinary: dùng signed URL hoặc private delivery.
    """

    STATUS_PENDING = 'pending'
    STATUS_APPROVED = 'approved'
    STATUS_REJECTED = 'rejected'
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Chờ duyệt'),
        (STATUS_APPROVED, 'Đã duyệt'),
        (STATUS_REJECTED, 'Từ chối'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    user = models.ForeignKey(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='verifications',
        verbose_name='Người dùng',
    )
    real_name = models.CharField(
        max_length=100,
        verbose_name='Tên thật'
    )

    # Ảnh minh chứng - lưu private trên Cloudinary
    # Đường dẫn: verifications/<uuid>.<ext>
    id_card_image = models.ImageField(
        upload_to='verifications/',
        verbose_name='Ảnh minh chứng',
    )

    note = models.TextField(
        blank=True,
        default='',
        verbose_name='Ghi chú'
    )

    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
        verbose_name='Trạng thái',
        db_index=True,
    )

    # Thông tin duyệt
    reviewed_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_verifications',
        verbose_name='Admin duyệt',
    )
    reviewed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Thời điểm duyệt'
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Ngày tạo'
    )

    class Meta:
        db_table = 'accounts_artist_verification'
        verbose_name = 'Yêu cầu xác thự nghệ sĩ'
        verbose_name_plural = 'Yêu cầu xác thực nghệ sĩ'
        ordering = ['-created_at']

    def __str__(self):
        return f'Verification({self.user.username}, {self.status})'
    
    def to_dict(self):
        return {
            'id': str(self.id),
            'user': {'id': str(self.user_id), 'username': self.user.username},
            'real_name': self.real_name,
            'note': self.note,
            'status': self.status,
            'reviewed_by': str(self.reviewed_by_id) if self.reviewed_by_id else None,
            'reviewed_at': self.reviewed_at.isoformat() if self.reviewed_at else None,
            'created_at': self.created_at.isoformat(),
        }

class BlockList(models.Model):
    """
    Danh sách block: blocker chặn blocked.

    Áp dụng policy:
    - Người bị chặn xem profile blocker → 404
    - Người bị chặn xem bài hát blocker → ẩn khỏi danh sách / 404 trực tiếp
    - Người bị chặn follow blocker → 403 BLOCKED
    - Người bị chặn comment bài hát blocker → 403 BLOCKED
    - Blocker không nhận notification từ người bị chặn
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    blocker = models.ForeignKey(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='blocking',
        verbose_name='Người chặn',
    )
    
    blocked = models.ForeignKey(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='blocked_by',
        verbose_name='Người bị chặn',
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Ngày chặn'
    )

    class Meta:
        db_table = 'accounts_block_list'
        verbose_name = 'Danh sách chặn'
        unique_together = [('blocker', 'blocked')]
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.blocker.username} -> block -> {self.blocked.username}'