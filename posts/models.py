import uuid
from django.db import models
from accounts.models import User
from music_platform.utils import optimize_cloudinary_url

class Post(models.Model):
    """Bảng lưu trữ Bài viết."""
    VISIBILITY_CHOICES = (
        ('PUBLIC', 'Công khai'),
        ('FRIENDS', 'Bạn bè'),
        ('PRIVATE', 'Chỉ mình tôi'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='posts', verbose_name='Người đăng')
    content = models.TextField(blank=True, verbose_name='Nội dung bài viết')
    visibility = models.CharField(max_length=10, choices=VISIBILITY_CHOICES, default='PUBLIC', verbose_name='Phạm vi hiển thị')
    
    # Hỗ trợ chức năng chia sẻ bài viết (share)
    shared_post = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='shares', verbose_name='Bài viết được chia sẻ')
    
    # Hỗ trợ chức năng chia sẻ bài hát
    shared_song = models.ForeignKey('music.Song', on_delete=models.SET_NULL, null=True, blank=True, related_name='shared_in_posts', verbose_name='Bài hát chia sẻ')
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Ngày đăng')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Cập nhật lần cuối')

    class Meta:
        db_table = 'posts_post'
        ordering = ['-created_at']

    def __str__(self):
        return f"Post by {self.author.username} at {self.created_at}"

class PostMedia(models.Model):
    """Bảng lưu trữ Hình ảnh/Video đính kèm bài viết."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='media', verbose_name='Bài viết')
    file_url = models.URLField(max_length=500, verbose_name='URL File (Cloudinary)')
    media_type = models.CharField(max_length=10, default='image', verbose_name='Loại (image/video)')
    order = models.IntegerField(default=0, verbose_name='Thứ tự hiển thị')

    class Meta:
        db_table = 'posts_media'
        ordering = ['order']

class PostReaction(models.Model):
    """Bảng lưu trữ Cảm xúc (Thả tim, Like, Haha...)."""
    REACTION_CHOICES = (
        ('LIKE', 'Thích'),
        ('LOVE', 'Yêu thích'),
        ('HAHA', 'Haha'),
        ('WOW', 'Wow'),
        ('SAD', 'Buồn'),
        ('ANGRY', 'Phẫn nộ'),
    )
    
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='reactions')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='post_reactions')
    reaction_type = models.CharField(max_length=10, choices=REACTION_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'posts_reaction'
        # Ràng buộc dữ liệu: 1 người dùng chỉ được thả 1 cảm xúc trên 1 bài viết
        unique_together = ['post', 'user']

class Comment(models.Model):
    """Bảng lưu trữ Bình luận và Trả lời bình luận."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='post_comments')
    content = models.TextField(verbose_name='Nội dung bình luận')
    
    # Khóa ngoại tự chiếu: Nếu null là bình luận gốc, nếu có ID thì là trả lời (reply)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='replies')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'posts_comment'
        ordering = ['created_at'] # Bình luận cũ xếp trên, mới xếp dưới
