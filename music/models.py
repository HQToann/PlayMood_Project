"""
music/models.py

Models cho app music:
  - Genre:         Thể loại nhạc
  - Song:          Bài hát (audio + cover)
  - Like:          Yêu thích bài hát
  - Rating:        Đánh giá sao
  - Comment:       Bình luận (hỗ trợ threaded 1 cấp)
  - CommentLike:   Yêu thích bình luận
  - ListenHistory: Lịch sử nghe
  - Report:        Báo cáo vi phạm
  - Album:         Album nhạc của nghệ sĩ
  - AlbumSong:     Bài hát trong album (quan hệ M2M có thứ tự)

Tất cả PK là UUIDField
"""

import uuid
from django.db import models
from django.core.exceptions import ValidationError
from django.conf import settings
from django.utils.text import slugify
from music_platform.utils import optimize_cloudinary_url

from django.core.files.storage import FileSystemStorage
audio_storage = FileSystemStorage()

class Genre(models.Model):
    """Thể loại âm nhạc - Admin quản lý, Public xem."""

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    name = models.CharField(
        max_length=100,
        unique=True,
        verbose_name='Tên thể loại',
    )

    slug = models.SlugField(
        max_length=120,
        unique=True,
        blank=True,
        verbose_name='Slug URL',
    )

    description = models.TextField(
        blank=True,
        default='',
        verbose_name='Mô tả',
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Ngày tạo',
    )

    class Meta:
        db_table = 'music_genre'
        ordering = ['name']
        verbose_name = 'Thể loại nhạc'
        verbose_name_plural = 'Thể loại nhạc'

    def save(self, *args, **kwargs):
        # tự động tạo slug từ name nếu chưa có
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name
    
    def to_dict(self, include_song_count=False):
        data = {
            'id': str(self.id),
            'name': self.name,
            'slug': self.slug,
            'description': self.description,
            'created_at': self.created_at.isoformat(),
        }
        if include_song_count:
            data['song_count'] = self.songs.filter(status=Song.STATUS_PUBLISHED).count()
        return data
    
class Song(models.Model):
    """
    Bài hát - trung tâm của hệ thống âm nhạc.
        
    Workflow trạng thái:
        draft -> publushed (qua endpoint /publish/)
        published -> hidden (artist ẩn hoặc admin ẩn)
        hidden -> published (artist/admin mở lại)

    audio_file và cover_image lưu trên Cloudinary.
    Path pattern:
        audio: audio/<artist_id>/<uuid>.<ext>
        cover: covers/songs/<uuid>.<ext>
    """

    STATUS_DRAFT = 'draft'
    STATUS_PUBLISHED = 'published'
    STATUS_HIDDEN = 'hidden'
    STATUS_CHOICES = [
        (STATUS_DRAFT, 'Bản nháp'),
        (STATUS_PUBLISHED, 'Đã phát hành'),
        (STATUS_HIDDEN, 'Đã ẩn'),
    ]

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    title = models.CharField(
        max_length=200,
        verbose_name='Tên bài hát',
        db_index=True,
    )

    # Nghệ sĩ là User với role='artist'
    artist = models.ForeignKey(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='songs',
        verbose_name='Nghệ sĩ',
        db_index=True,
    )

    genre = models.ForeignKey(
        Genre,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='songs',
        verbose_name='Thể loại',
    )

    # FIle lưu trên Local VPS qua DEFAULT_FILE_STORAGE
    audio_file = models.FileField(
        upload_to='audio/',
        verbose_name='File audio',
    )


    cover_image = models.ImageField(
        upload_to='covers/songs/',
        blank=True,
        null=True,
        verbose_name='Ảnh bìa',
    )

    lyrics = models.TextField(
        blank=True,
        default='',
        verbose_name='Lời bài hát'
    )

    duration = models.PositiveIntegerField(
        default=0,
        verbose_name='Thời lượng (giây)'
    )

    status = models.CharField(
        max_length=15,
        choices=STATUS_CHOICES,
        default=STATUS_DRAFT,
        verbose_name='Trạng thái',
        db_index=True,
    )

    hidden_by_admin = models.BooleanField(
        default=False,
        verbose_name='Bị khoá bởi Admin',
    )
    hidden_reason = models.TextField(
        blank=True,
        null=True,
        verbose_name='Lý do bị khoá',
    )
    is_appealed = models.BooleanField(
        default=False,
        verbose_name='Đang có kiến nghị',
    )
    appeal_message = models.TextField(
        blank=True,
        null=True,
        verbose_name='Nội dung kiến nghị',
    )

    allow_download = models.BooleanField(
        default=False,
        verbose_name='Cho phép tải',
    )

    is_trending = models.BooleanField(
        default=False,
        verbose_name='Trending',
        db_index=True,
    )

    # play_count chỉ được tăng qua F() expression, không gán trước tiếp.
    play_count = models.PositiveIntegerField(
        default=0,
        verbose_name='Lượt nghe',
        db_index=True,
    )

    released_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Ngày phát hành',
    )

    created_at=models.DateTimeField(
        auto_now_add=True,
        verbose_name='Ngày tạo',
        db_index=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Cập nhật lần cuối',
    )

    class Meta:
        db_table = 'music_song'
        ordering = ['-created_at']
        verbose_name = 'Bài hát'
        verbose_name_plural = 'Bài hát'

    def __str__(self):
        return f'{self.title} - {self.artist.username}'
    
    def to_dict(self, viewer=None, include_stats=True, include_viewer_state=True):
        """
        Serialize Song thành dict.
        
        Args:
            viewer: User đang xem
            include_stats: bao gồm like_count, avg_rating
        """
        data = {
            'id': str(self.id),
            'title': self.title,
            'artist': {
                'id': str(self.artist_id),
                'username': self.artist.username,
                'display_name': self.artist.get_display_name(),
                'avatar': optimize_cloudinary_url(self.artist.avatar.url, 'image') if self.artist.avatar else None,
            },
            'genre': self.genre.to_dict() if self.genre else None,
            'audio_file': optimize_cloudinary_url(self.audio_file.url, 'audio') if (self.audio_file and viewer and viewer.is_authenticated) else None,
            'cover_image': optimize_cloudinary_url(self.cover_image.url, 'image') if self.cover_image else None,
            'lyrics': self.lyrics,
            'duration': self.duration,
            'play_count': self.play_count,
            'status': self.status,
            'is_trending': self.is_trending,
            'allow_download': self.allow_download,
            'release_at': self.released_at.isoformat() if self.released_at else None,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'hidden_by_admin': self.hidden_by_admin,
            'hidden_reason': self.hidden_reason,
            'is_appealed': self.is_appealed,
            'appeal_message': self.appeal_message,
        }

        if include_stats:
            data['like_count'] = self.likes.count()
            ratings = self.ratings.all()
            data['rating_count'] = ratings.count()
            data['avg_rating'] = (
                round(sum(r.score for r in ratings) / ratings.count(), 1)
                if ratings.count() > 0 else None
            )

            from django.utils import timezone
            from datetime import timedelta
            thirty_days_ago = timezone.now() - timedelta(days=30)
            data['artist']['monthly_listeners'] = ListenHistory.objects.filter(
                song__artist=self.artist,
                listened_at__gte=thirty_days_ago
            ).values('user').distinct().count()
        if include_viewer_state and viewer and hasattr(viewer, 'id') and viewer.is_authenticated:
            data['is_liked'] = self.likes.filter(user=viewer).exists()
            my_rating = self.ratings.filter(user=viewer).first()
            data['my_rating'] = my_rating.score if my_rating else None
        return data

class Like(models.Model):
    """Yêu thích bài hát - toggle: POST = like nếu chưa, unlike nếu có."""
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    user = models.ForeignKey(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='song_likes',
    )
    song = models.ForeignKey(
        Song,
        on_delete=models.CASCADE,
        related_name='likes',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'music_like'
        unique_together = [('user', 'song')]
        ordering = ['-created_at']
    
    def __str__(self):
        return f'{self.user.username} like {self.song.title}'

class Rating(models.Model):
    """Đánh giá 1-5 sao - upset: mỗi user chỉ có rating/bài."""
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    user = models.ForeignKey(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='ratings'
    )
    song = models.ForeignKey(
        Song,
        on_delete=models.CASCADE,
        related_name='ratings'
    )
    score = models.PositiveSmallIntegerField(
        verbose_name='Điểm',
        help_text='1-5 sao',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'music_rating'
        unique_together = [('user', 'song')]

    def __str__(self):
        return f'{self.user.username} rating {self.song.title}: {self.score} sao'
    
class Comment(models.Model):
    """
    Bình luận bài hát - hỗ trợ threaded 1 cấp (comment gốc + replies).
    
    Không cho phép reply của reply (parent phải là comment gốc + replies).
    is_hidden dùng để admin ẩn vi phạm (solf delete, không xoá thật).
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    user = models.ForeignKey(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='comments',
    )
    song = models.ForeignKey(
        Song,
        on_delete=models.CASCADE,
        related_name='comments'
    )

    # parent=None -> comment gốc; parent!=None -> reply
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='replies',
        verbose_name='Comment cha',
    )

    content = models.TextField(
        verbose_name='Nội dung' # sanitized XSS trước khi lưu 
    )
    is_hidden = models.BooleanField(
        default=False,
        verbose_name='Đã ẩn',
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
    )

    class Meta:
        db_table = 'music_comment'
        ordering = ['created_at']
        verbose_name = 'Bình luận'

    def __str__(self):
        return f'{self.user.username}: {self.content[:50]}'
    
    def to_dict(self, viewer=None, include_replies=False):
        data = {
            'id': str(self.id),
            'user': {
                'id': str(self.user_id),
                'username': self.user.username,
                'display_name': self.user.get_display_name(),
                'avatar': optimize_cloudinary_url(self.user.avatar.url, 'image') if self.user.avatar else None,
            },
            'content': self.content,
            'like_count': self.comment_likes.count(),
            'parent_id': str(self.parent_id) if self.parent_id else None,
            'created_at': self.created_at.isoformat(), 
        }
        if viewer and hasattr(viewer, 'id') and viewer.is_authenticated:
            data['is_liked_by_viewer'] = self.comment_likes.filter(user=viewer).exists()
        else:
            data['is_liked_by_viewer'] = False
        if include_replies:
            data['replies'] = [
                r.to_dict(viewer=viewer)
                for r in self.replies.filter(is_hidden=False).order_by('created_at')
            ]
        return data

class CommentLike(models.Model):
    """Yêu thích bình luận - toggle giống SongLike."""
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    user = models.ForeignKey(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='comment_likes',
    )
    comment = models.ForeignKey(
        Comment,
        on_delete=models.CASCADE,
        related_name='comment_likes',
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        db_table = 'music_comment_like'
        unique_together = [('user', 'comment')]

class ListenHistory(models.Model):
    """Lịch sử nghe nhạc."""
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    user = models.ForeignKey(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='listen_history',
    )
    song = models.ForeignKey(
        Song,
        on_delete=models.CASCADE,
        related_name='listen_history',
    )
    listened_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
    )

    class Meta:
        db_table = 'music_listen_history'
        ordering = ['-listened_at']
        indexes = [
            # Index composite để dedup query nhanh
            models.Index(fields=['user', 'song', 'listened_at'],
                         name='history_user_song_time_idx'),
        ]
    
class Report(models.Model):
    """
    Báo cáo vi phạm - target_type + target_id xác định đối tượng bị báo cáod.
    
    target_type: 'song' | 'comment' | 'user'
    target_id: UUID của đối tượng
    """
    
    TARGET_SONG = 'song'
    TARGET_COMMENT = 'comment'
    TARGET_USER = 'user'
    TARGET_PLAYLIST = 'playlist'
    TARGET_CHOICES = [
        (TARGET_SONG, 'Bài hát'),
        (TARGET_COMMENT, 'Bình luận'),
        (TARGET_USER, 'Người dùng'),
        (TARGET_PLAYLIST, 'Playlist'),
    ]

    REASON_COPYRIGHT = 'copyright'
    REASON_SPAM = 'spam'
    REASON_OFFENSIVE = 'offensive'
    REASON_OTHER = 'other'
    REASON_CHOICES = [
        (REASON_COPYRIGHT, 'Vi phạm bản quyền'),
        (REASON_SPAM, 'Spam'),
        (REASON_OFFENSIVE, 'Nội dung sản phẩm'),
        (REASON_OTHER, 'Lý do khác'),
    ]

    STATUS_PENDING = 'pending'
    STATUS_RESOLVED = 'resolved'
    STATUS_DISMISSED = 'dismissed'
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Chờ xử lý'),
        (STATUS_RESOLVED, 'Đã xử lý'),
        (STATUS_DISMISSED, 'Bỏ qua'),
    ]

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    reporter = models.ForeignKey(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='reports',
    )
    target_type = models.CharField(
        max_length=10,
        choices=TARGET_CHOICES,
        db_index=True,
    )
    target_id = models.UUIDField(
        verbose_name='ID đối tượng',
        db_index=True,
    )
    reason = models.CharField(
        max_length=20,
        choices=REASON_CHOICES
    )
    description = models.TextField(
        blank=True,
        default='',
        verbose_name='Mô tả chi tiết',
    )
    status = models.CharField(
        max_length=15,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
        db_index=True,
    )
    resolved_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='resolved_reports',
        verbose_name='Admin xử lý',
    )
    resolved_note = models.TextField(
        blank=True,
        default='',
        verbose_name='Ghi chú xử lý',
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
    )

    class Meta:
        db_table = 'music_report'
        ordering = ['-created_at']
        verbose_name = 'Báo cáo vi phạm'

    def __str__(self):
        return f'Report({self.target_type}/{self.target_id}, {self.status})'

    def to_dict(self):
        return {
            'id': str(self.id),
            'reporter': {'id': str(self.reporter_id), 'username': self.reporter.username},
            'target_type': self.target_type,
            'target_id': str(self.target_id),
            'reason': self.reason,
            'description': self.description,
            'status': self.status,
            'resolved_by': str(self.resolved_by_id) if self.resolved_by_id else None,
            'resolved_note': self.resolved_note,
            'created_at': self.created_at.isoformat(),
        }


class Album(models.Model):
    """
    Album nhạc của nghệ sĩ.

    Workflow:
        draft → published (qua endpoint /publish/)
        published → draft (ẩn album)
    """

    STATUS_DRAFT = 'draft'
    STATUS_PUBLISHED = 'published'
    STATUS_CHOICES = [
        (STATUS_DRAFT, 'Bản nháp'),
        (STATUS_PUBLISHED, 'Đã phát hành'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    title = models.CharField(
        max_length=200,
        verbose_name='Tên album',
        db_index=True,
    )

    artist = models.ForeignKey(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='albums',
        verbose_name='Nghệ sĩ',
    )

    cover_image = models.ImageField(
        upload_to='covers/albums/',
        blank=True,
        null=True,
        verbose_name='Ảnh bìa album',
    )

    description = models.TextField(
        blank=True,
        default='',
        verbose_name='Mô tả',
    )

    status = models.CharField(
        max_length=15,
        choices=STATUS_CHOICES,
        default=STATUS_DRAFT,
        verbose_name='Trạng thái',
        db_index=True,
    )

    released_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Ngày phát hành',
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Ngày tạo')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Cập nhật lần cuối')

    class Meta:
        db_table = 'music_album'
        ordering = ['-created_at']
        verbose_name = 'Album'
        verbose_name_plural = 'Album'

    def __str__(self):
        return f'{self.title} - {self.artist.username}'

    def to_dict(self, viewer=None):
        songs = [
            {
                'order': asong.order,
                'added_at': asong.added_at.isoformat() if asong.added_at else None,
                'song': asong.song.to_dict(viewer=viewer, include_stats=False, include_viewer_state=True)
            }
            for asong in self.album_songs.select_related('song', 'song__artist').order_by('order', 'added_at')
        ]
        # Fallback cover: dùng cover bài đầu tiên nếu album chưa có cover
        cover_url = optimize_cloudinary_url(self.cover_image.url, 'image') if self.cover_image else (
            songs[0]['song']['cover_image'] if songs else None
        )
        return {
            'id': str(self.id),
            'title': self.title,
            'description': self.description,
            'status': self.status,
            'cover_image': cover_url,
            'released_at': self.released_at.isoformat() if self.released_at else None,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'artist': {
                'id': str(self.artist_id),
                'username': self.artist.username,
                'display_name': self.artist.get_display_name(),
                'avatar': optimize_cloudinary_url(self.artist.avatar.url, 'image') if self.artist.avatar else None,
            },
            'song_count': len(songs),
            'songs': songs,
        }


class AlbumSong(models.Model):
    """Bài hát trong album — quan hệ M2M có thứ tự."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    album = models.ForeignKey(
        Album,
        on_delete=models.CASCADE,
        related_name='album_songs',
        verbose_name='Album',
    )

    song = models.ForeignKey(
        Song,
        on_delete=models.CASCADE,
        related_name='in_albums',
        verbose_name='Bài hát',
    )

    order = models.PositiveSmallIntegerField(
        default=0,
        verbose_name='Thứ tự',
    )

    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'music_album_song'
        ordering = ['order', 'added_at']
        unique_together = [('album', 'song')]
        verbose_name = 'Bài hát trong album'
        verbose_name_plural = 'Bài hát trong album'

    def __str__(self):
        return f'{self.album.title} / {self.song.title} (#{self.order})'