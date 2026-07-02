# 03 — Source Code Hoàn Chỉnh Tuần 2

**App `music` — models, exceptions, validators, selectors, services, views, urls**

> Copy từng file vào đúng thư mục `music/` trong project.
> Sau khi copy xong, xem file `04_week2_configs_and_db_changes.md` để biết các bước apply.

---

## Cấu Trúc File

```
music/
├── __init__.py
├── apps.py
├── models.py
├── exceptions.py
├── validators.py
├── selectors.py
├── services.py
├── views.py
├── urls.py
└── admin.py
```

---

## `music/__init__.py`

```python
```

---

## `music/apps.py`

```python
"""music/apps.py"""
from django.apps import AppConfig


class MusicConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name  = 'music'
    label = 'music'
    verbose_name = 'Âm nhạc'
```

---

## `music/models.py`

```python
"""
music/models.py
===============
Models cho app music:
  - Genre:         Thể loại nhạc
  - Song:          Bài hát (audio + cover)
  - Like:          Yêu thích bài hát
  - Rating:        Đánh giá sao
  - Comment:       Bình luận (hỗ trợ threaded 1 cấp)
  - CommentLike:   Yêu thích bình luận
  - ListenHistory: Lịch sử nghe
  - Report:        Báo cáo vi phạm

Tất cả PK là UUIDField theo quy ước §12.1.
"""

import uuid
from django.db import models
from django.utils.text import slugify


class Genre(models.Model):
    """Thể loại nhạc — Admin quản lý, Public xem."""

    id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name        = models.CharField(max_length=100, unique=True, verbose_name='Tên thể loại')
    slug        = models.SlugField(max_length=120, unique=True, blank=True,
                                   verbose_name='Slug URL')
    description = models.TextField(blank=True, default='', verbose_name='Mô tả')
    created_at  = models.DateTimeField(auto_now_add=True, verbose_name='Ngày tạo')

    class Meta:
        db_table     = 'music_genre'
        ordering     = ['name']
        verbose_name = 'Thể loại nhạc'
        verbose_name_plural = 'Thể loại nhạc'

    def save(self, *args, **kwargs):
        # Tự động tạo slug từ name nếu chưa có
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    def to_dict(self, include_song_count=False):
        data = {
            'id':          str(self.id),
            'name':        self.name,
            'slug':        self.slug,
            'description': self.description,
            'created_at':  self.created_at.isoformat(),
        }
        if include_song_count:
            data['song_count'] = self.songs.filter(status=Song.STATUS_PUBLISHED).count()
        return data


class Song(models.Model):
    """
    Bài hát — trung tâm của hệ thống âm nhạc.

    Workflow trạng thái:
        draft → published (qua endpoint /publish/)
        published → hidden (artist ẩn hoặc admin ẩn)
        hidden → published (artist/admin mở lại)

    audio_file và cover_image lưu trên Cloudinary.
    Path pattern (§12.3):
        audio:  audio/<artist_id>/<uuid>.<ext>
        cover:  covers/songs/<uuid>.<ext>
    """

    STATUS_DRAFT     = 'draft'
    STATUS_PUBLISHED = 'published'
    STATUS_HIDDEN    = 'hidden'
    STATUS_CHOICES   = [
        (STATUS_DRAFT,     'Bản nháp'),
        (STATUS_PUBLISHED, 'Đã phát hành'),
        (STATUS_HIDDEN,    'Đã ẩn'),
    ]

    id             = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title          = models.CharField(max_length=200, verbose_name='Tên bài hát', db_index=True)

    # Nghệ sĩ là User với role='artist'
    artist         = models.ForeignKey(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='songs',
        verbose_name='Nghệ sĩ',
        db_index=True,
    )
    genre          = models.ForeignKey(
        Genre,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='songs',
        verbose_name='Thể loại',
    )

    # File lưu trên Cloudinary qua DEFAULT_FILE_STORAGE
    audio_file     = models.FileField(
        upload_to='audio/',
        verbose_name='File audio',
    )
    cover_image    = models.ImageField(
        upload_to='covers/songs/',
        blank=True,
        null=True,
        verbose_name='Ảnh bìa',
    )

    lyrics         = models.TextField(blank=True, default='', verbose_name='Lời bài hát')
    duration       = models.PositiveIntegerField(default=0, verbose_name='Thời lượng (giây)')

    status         = models.CharField(
        max_length=15,
        choices=STATUS_CHOICES,
        default=STATUS_DRAFT,
        verbose_name='Trạng thái',
        db_index=True,
    )
    allow_download = models.BooleanField(default=False, verbose_name='Cho phép tải')
    is_trending    = models.BooleanField(default=False, verbose_name='Trending', db_index=True)

    # play_count chỉ được tăng qua F() expression, không bao giờ gán trực tiếp (Fix R1)
    play_count     = models.PositiveIntegerField(default=0, verbose_name='Lượt nghe', db_index=True)

    released_at    = models.DateTimeField(null=True, blank=True, verbose_name='Ngày phát hành')
    created_at     = models.DateTimeField(auto_now_add=True, verbose_name='Ngày tạo', db_index=True)
    updated_at     = models.DateTimeField(auto_now=True, verbose_name='Cập nhật lần cuối')

    class Meta:
        db_table     = 'music_song'
        ordering     = ['-created_at']
        verbose_name = 'Bài hát'
        verbose_name_plural = 'Bài hát'

    def __str__(self):
        return f'{self.title} — {self.artist.username}'

    def to_dict(self, viewer=None, include_stats=True, include_viewer_state=True):
        """
        Serialize Song thành dict.

        Args:
            viewer:        User đang xem (để check is_liked, my_rating)
            include_stats: bao gồm like_count, avg_rating (tốn thêm query)
        """
        data = {
            'id':             str(self.id),
            'title':          self.title,
            'artist': {
                'id':           str(self.artist_id),
                'username':     self.artist.username,
                'display_name': self.artist.get_display_name(),
                'avatar':       self.artist.avatar.url if self.artist.avatar else None,
            },
            'genre': self.genre.to_dict() if self.genre else None,
            'audio_file':     self.audio_file.url if self.audio_file else None,
            'cover_image':    self.cover_image.url if self.cover_image else None,
            'lyrics':         self.lyrics,
            'duration':       self.duration,
            'play_count':     self.play_count,
            'status':         self.status,
            'is_trending':    self.is_trending,
            'allow_download': self.allow_download,
            'released_at':    self.released_at.isoformat() if self.released_at else None,
            'created_at':     self.created_at.isoformat(),
            'updated_at':     self.updated_at.isoformat(),
        }
        if include_stats:
            data['like_count']    = self.likes.count()
            ratings               = self.ratings.all()
            data['rating_count']  = ratings.count()
            data['avg_rating']    = (
                round(sum(r.score for r in ratings) / ratings.count(), 1)
                if ratings.count() > 0 else None
            )
        if include_viewer_state and viewer and hasattr(viewer, 'id') and viewer.is_authenticated:
            data['is_liked']  = self.likes.filter(user=viewer).exists()
            my_rating         = self.ratings.filter(user=viewer).first()
            data['my_rating'] = my_rating.score if my_rating else None
        return data


class Like(models.Model):
    """Yêu thích bài hát — toggle: POST = like nếu chưa, unlike nếu đã có."""

    id         = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user       = models.ForeignKey(
        'accounts.User', on_delete=models.CASCADE, related_name='song_likes')
    song       = models.ForeignKey(Song, on_delete=models.CASCADE, related_name='likes')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table        = 'music_like'
        unique_together = [('user', 'song')]
        ordering        = ['-created_at']

    def __str__(self):
        return f'{self.user.username} ♥ {self.song.title}'


class Rating(models.Model):
    """Đánh giá 1–5 sao — upsert: mỗi user chỉ có 1 rating/bài."""

    id         = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user       = models.ForeignKey(
        'accounts.User', on_delete=models.CASCADE, related_name='ratings')
    song       = models.ForeignKey(Song, on_delete=models.CASCADE, related_name='ratings')
    score      = models.PositiveSmallIntegerField(
        verbose_name='Điểm',
        help_text='1–5 sao',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table        = 'music_rating'
        unique_together = [('user', 'song')]

    def __str__(self):
        return f'{self.user.username} → {self.song.title}: {self.score}★'


class Comment(models.Model):
    """
    Bình luận bài hát — hỗ trợ threaded 1 cấp (comment gốc + replies).

    Không cho phép reply của reply (parent phải là comment gốc).
    is_hidden dùng để admin ẩn vi phạm (soft delete, không xóa thật).
    """

    id        = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user      = models.ForeignKey(
        'accounts.User', on_delete=models.CASCADE, related_name='comments')
    song      = models.ForeignKey(Song, on_delete=models.CASCADE, related_name='comments')

    # parent=None → comment gốc; parent!=None → reply
    parent    = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='replies',
        verbose_name='Comment cha',
    )

    content   = models.TextField(verbose_name='Nội dung')  # sanitized XSS trước khi lưu
    is_hidden = models.BooleanField(default=False, verbose_name='Đã ẩn')
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table     = 'music_comment'
        ordering     = ['created_at']
        verbose_name = 'Bình luận'

    def __str__(self):
        return f'{self.user.username}: {self.content[:50]}'

    def to_dict(self, viewer=None, include_replies=False):
        data = {
            'id':        str(self.id),
            'user': {
                'id':           str(self.user_id),
                'username':     self.user.username,
                'display_name': self.user.get_display_name(),
                'avatar':       self.user.avatar.url if self.user.avatar else None,
            },
            'content':    self.content,
            'like_count': self.comment_likes.count(),
            'parent_id':  str(self.parent_id) if self.parent_id else None,
            'created_at': self.created_at.isoformat(),
        }
        if viewer and hasattr(viewer, 'id') and viewer.is_authenticated:
            data['is_liked'] = self.comment_likes.filter(user=viewer).exists()
        else:
            data['is_liked'] = False
        if include_replies:
            data['replies'] = [
                r.to_dict(viewer=viewer)
                for r in self.replies.filter(is_hidden=False).order_by('created_at')
            ]
        return data


class CommentLike(models.Model):
    """Yêu thích bình luận — toggle giống SongLike."""

    id         = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user       = models.ForeignKey(
        'accounts.User', on_delete=models.CASCADE, related_name='comment_likes')
    comment    = models.ForeignKey(
        Comment, on_delete=models.CASCADE, related_name='comment_likes')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table        = 'music_comment_like'
        unique_together = [('user', 'comment')]


class ListenHistory(models.Model):
    """
    Lịch sử nghe nhạc.

    Dùng cho dedup 5 phút (Fix R8):
        ListenHistory.objects.filter(user=user, song=song, listened_at__gte=cutoff).exists()
    """

    id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user        = models.ForeignKey(
        'accounts.User', on_delete=models.CASCADE, related_name='listen_history')
    song        = models.ForeignKey(Song, on_delete=models.CASCADE, related_name='listen_history')
    listened_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = 'music_listen_history'
        ordering = ['-listened_at']
        indexes  = [
            # Index composite để dedup query nhanh (Fix R8)
            models.Index(fields=['user', 'song', 'listened_at'],
                         name='history_user_song_time_idx'),
        ]


class Report(models.Model):
    """
    Báo cáo vi phạm — target_type + target_id xác định đối tượng bị báo cáo.

    target_type: 'song' | 'comment' | 'user'
    target_id:   UUID của đối tượng
    """

    TARGET_SONG    = 'song'
    TARGET_COMMENT = 'comment'
    TARGET_USER    = 'user'
    TARGET_CHOICES = [
        (TARGET_SONG,    'Bài hát'),
        (TARGET_COMMENT, 'Bình luận'),
        (TARGET_USER,    'Người dùng'),
    ]

    REASON_COPYRIGHT  = 'copyright'
    REASON_SPAM       = 'spam'
    REASON_OFFENSIVE  = 'offensive'
    REASON_OTHER      = 'other'
    REASON_CHOICES    = [
        (REASON_COPYRIGHT, 'Vi phạm bản quyền'),
        (REASON_SPAM,      'Spam'),
        (REASON_OFFENSIVE, 'Nội dung phản cảm'),
        (REASON_OTHER,     'Lý do khác'),
    ]

    STATUS_PENDING   = 'pending'
    STATUS_RESOLVED  = 'resolved'
    STATUS_DISMISSED = 'dismissed'
    STATUS_CHOICES   = [
        (STATUS_PENDING,   'Chờ xử lý'),
        (STATUS_RESOLVED,  'Đã xử lý'),
        (STATUS_DISMISSED, 'Bỏ qua'),
    ]

    id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    reporter    = models.ForeignKey(
        'accounts.User', on_delete=models.CASCADE, related_name='reports')
    target_type = models.CharField(max_length=10, choices=TARGET_CHOICES, db_index=True)
    target_id   = models.UUIDField(verbose_name='ID đối tượng', db_index=True)
    reason      = models.CharField(max_length=20, choices=REASON_CHOICES)
    description = models.TextField(blank=True, default='', verbose_name='Mô tả chi tiết')
    status      = models.CharField(
        max_length=15, choices=STATUS_CHOICES, default=STATUS_PENDING, db_index=True)
    resolved_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='resolved_reports',
        verbose_name='Admin xử lý',
    )
    resolved_note = models.TextField(blank=True, default='', verbose_name='Ghi chú xử lý')
    created_at  = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table     = 'music_report'
        ordering     = ['-created_at']
        verbose_name = 'Báo cáo vi phạm'

    def __str__(self):
        return f'Report({self.target_type}/{self.target_id}, {self.status})'

    def to_dict(self):
        return {
            'id':            str(self.id),
            'reporter':      {'id': str(self.reporter_id), 'username': self.reporter.username},
            'target_type':   self.target_type,
            'target_id':     str(self.target_id),
            'reason':        self.reason,
            'description':   self.description,
            'status':        self.status,
            'resolved_by':   str(self.resolved_by_id) if self.resolved_by_id else None,
            'resolved_note': self.resolved_note,
            'created_at':    self.created_at.isoformat(),
        }
```

---

## `music/exceptions.py`

```python
"""
music/exceptions.py
===================
Custom exceptions cho nghiệp vụ app music.
"""

from accounts.exceptions import AppException


class SongNotFound(AppException):
    """Bài hát không tồn tại hoặc đã bị ẩn — HTTP 404."""
    def __init__(self, message='Bài hát không tồn tại'):
        super().__init__(message, error_code='NOT_FOUND')


class SongNotPublished(AppException):
    """Bài hát chưa được phát hành — HTTP 404."""
    def __init__(self, message='Bài hát không tồn tại'):
        super().__init__(message, error_code='NOT_FOUND')


class DownloadNotAllowed(AppException):
    """Bài hát không cho phép tải về — HTTP 403."""
    def __init__(self, message='Bài hát này không cho phép tải về'):
        super().__init__(message, error_code='DOWNLOAD_NOT_ALLOWED')


class NotSongOwner(AppException):
    """Không phải chủ bài hát — HTTP 403."""
    def __init__(self, message='Bạn không có quyền thực hiện hành động này với bài hát này'):
        super().__init__(message, error_code='PERMISSION_DENIED')


class SongAlreadyPublished(AppException):
    """Bài hát đã published, không thể publish lại — HTTP 400."""
    def __init__(self, message='Bài hát đã được phát hành'):
        super().__init__(message, error_code='ALREADY_PUBLISHED')


class CommentNotFound(AppException):
    """Bình luận không tồn tại hoặc đã ẩn — HTTP 404."""
    def __init__(self, message='Bình luận không tồn tại'):
        super().__init__(message, error_code='NOT_FOUND')


class NotCommentOwner(AppException):
    """Không phải chủ bình luận — HTTP 403."""
    def __init__(self, message='Bạn không có quyền xóa bình luận này'):
        super().__init__(message, error_code='PERMISSION_DENIED')


class GenreNotFound(AppException):
    """Thể loại không tồn tại — HTTP 404."""
    def __init__(self, message='Thể loại không tồn tại'):
        super().__init__(message, error_code='NOT_FOUND')


class GenreHasSongs(AppException):
    """Không thể xóa thể loại đang có bài hát — HTTP 400."""
    def __init__(self, message='Không thể xóa thể loại đang có bài hát'):
        super().__init__(message, error_code='GENRE_HAS_SONGS')


class BlockedByArtist(AppException):
    """Bị nghệ sĩ block, không thể bình luận — HTTP 403."""
    def __init__(self, message='Bạn không thể thực hiện hành động này'):
        super().__init__(message, error_code='BLOCKED')


class ReportNotFound(AppException):
    """Báo cáo không tồn tại — HTTP 404."""
    def __init__(self, message='Báo cáo không tồn tại'):
        super().__init__(message, error_code='NOT_FOUND')


class InvalidParentComment(AppException):
    """Parent comment không hợp lệ (khác bài hát hoặc là reply) — HTTP 400."""
    def __init__(self, message='Bình luận cha không hợp lệ'):
        super().__init__(message, error_code='INVALID_PARENT')
```

---

## `music/validators.py`

```python
"""
music/validators.py
===================
Kiểm tra dữ liệu đầu vào cho app music.

Quy ước: KHÔNG gọi DB, KHÔNG gọi service.
Mọi text public phải qua sanitize_text() (Fix R12).
"""

import uuid
from music_platform.sanitize import sanitize_text
from accounts.exceptions import ValidationError

# ── Hằng số (Fix R5) ──────────────────────────────────────────────────────────
ALLOWED_AUDIO_TYPES = {
    'audio/mpeg',   # mp3
    'audio/flac',   # flac
    'audio/wav',    # wav
    'audio/ogg',    # ogg
    'audio/mp4',    # m4a/aac
    'audio/x-flac', # flac alternate
}
MAX_AUDIO_SIZE = 50 * 1024 * 1024   # 50 MB

ALLOWED_IMAGE_TYPES = {'image/jpeg', 'image/png', 'image/webp'}
MAX_IMAGE_SIZE      = 5 * 1024 * 1024    # 5 MB

VALID_ORDERINGS = {
    '-created_at', 'created_at',
    '-play_count', 'play_count',
    '-released_at', 'released_at',
    'title', '-title',
}

REPORT_REASONS = {'copyright', 'spam', 'offensive', 'other'}
REPORT_TARGETS = {'song', 'comment', 'user'}


def validate_genre(data: dict) -> dict:
    """Validate tạo/cập nhật thể loại."""
    errors = {}
    name = data.get('name', '').strip()
    if not name:
        errors['name'] = ['Tên thể loại là bắt buộc']
    elif len(name) > 100:
        errors['name'] = ['Tên thể loại tối đa 100 ký tự']

    if errors:
        raise ValidationError('Dữ liệu thể loại không hợp lệ', fields=errors)

    return {
        'name':        name,
        'description': sanitize_text(data.get('description', '')),
    }


def validate_song_create(data: dict, files: dict) -> dict:
    """
    Validate upload bài hát mới.

    Kiểm tra:
    - title, genre_id, duration bắt buộc
    - audio_file: MIME type + size (Fix R5)
    - cover_image: MIME type + size (nếu có)
    - lyrics: sanitize XSS (Fix R12)
    """
    errors = {}

    # title
    title = data.get('title', '').strip()
    if not title:
        errors['title'] = ['Tên bài hát là bắt buộc']
    elif len(title) > 200:
        errors['title'] = ['Tên bài hát tối đa 200 ký tự']

    # genre_id
    genre_id = data.get('genre_id', '')
    if not genre_id:
        errors['genre_id'] = ['Thể loại là bắt buộc']
    else:
        try:
            genre_id = uuid.UUID(str(genre_id))
        except (ValueError, AttributeError):
            errors['genre_id'] = ['genre_id không đúng định dạng UUID']

    # duration
    try:
        duration = int(data.get('duration', 0))
        if duration <= 0:
            errors['duration'] = ['Thời lượng phải lớn hơn 0']
    except (ValueError, TypeError):
        errors['duration'] = ['Thời lượng phải là số nguyên (giây)']
        duration = 0

    # audio_file (Fix R5)
    if 'audio_file' not in files:
        errors['audio_file'] = ['File audio là bắt buộc']
    else:
        audio = files['audio_file']
        if audio.content_type not in ALLOWED_AUDIO_TYPES:
            errors['audio_file'] = [
                f'Chỉ chấp nhận: {", ".join(sorted(ALLOWED_AUDIO_TYPES))}'
            ]
        elif audio.size > MAX_AUDIO_SIZE:
            errors['audio_file'] = ['File audio tối đa 50 MB']

    # cover_image (tùy chọn)
    if 'cover_image' in files:
        cover = files['cover_image']
        if cover.content_type not in ALLOWED_IMAGE_TYPES:
            errors['cover_image'] = ['Chỉ chấp nhận JPG, PNG, WEBP']
        elif cover.size > MAX_IMAGE_SIZE:
            errors['cover_image'] = ['Ảnh bìa tối đa 5 MB']

    if errors:
        raise ValidationError('Dữ liệu bài hát không hợp lệ', fields=errors)

    # allow_download
    allow_dl = data.get('allow_download', False)
    if isinstance(allow_dl, str):
        allow_dl = allow_dl.lower() in ('true', '1', 'yes')

    return {
        'title':          sanitize_text(title),
        'genre_id':       genre_id,
        'duration':       duration,
        'lyrics':         sanitize_text(data.get('lyrics', '')),
        'allow_download': bool(allow_dl),
        'released_at':    data.get('released_at', None),
    }


def validate_song_update(data: dict, files: dict) -> dict:
    """Validate cập nhật bài hát — partial update (chỉ field nào có mới validate)."""
    errors = {}
    result = {}

    if 'title' in data:
        title = data['title'].strip()
        if not title:
            errors['title'] = ['Tên bài hát không được để trống']
        elif len(title) > 200:
            errors['title'] = ['Tên bài hát tối đa 200 ký tự']
        else:
            result['title'] = sanitize_text(title)

    if 'genre_id' in data:
        try:
            result['genre_id'] = uuid.UUID(str(data['genre_id']))
        except (ValueError, AttributeError):
            errors['genre_id'] = ['genre_id không đúng định dạng UUID']

    if 'lyrics' in data:
        result['lyrics'] = sanitize_text(data['lyrics'])

    if 'allow_download' in data:
        val = data['allow_download']
        if isinstance(val, str):
            val = val.lower() in ('true', '1', 'yes')
        result['allow_download'] = bool(val)

    if 'cover_image' in files:
        cover = files['cover_image']
        if cover.content_type not in ALLOWED_IMAGE_TYPES:
            errors['cover_image'] = ['Chỉ chấp nhận JPG, PNG, WEBP']
        elif cover.size > MAX_IMAGE_SIZE:
            errors['cover_image'] = ['Ảnh bìa tối đa 5 MB']

    if errors:
        raise ValidationError('Dữ liệu cập nhật không hợp lệ', fields=errors)

    return result


def validate_rating(data: dict) -> dict:
    """Validate đánh giá 1–5 sao."""
    try:
        score = int(data.get('score', 0))
    except (ValueError, TypeError):
        raise ValidationError(
            'Điểm đánh giá không hợp lệ',
            fields={'score': ['Điểm phải là số nguyên từ 1 đến 5']},
        )
    if not 1 <= score <= 5:
        raise ValidationError(
            'Điểm đánh giá không hợp lệ',
            fields={'score': ['Điểm phải từ 1 đến 5']},
        )
    return {'score': score}


def validate_comment(data: dict) -> dict:
    """Validate nội dung bình luận — sanitize XSS (Fix R12)."""
    errors = {}
    content = data.get('content', '').strip()
    if not content:
        errors['content'] = ['Nội dung bình luận là bắt buộc']
    elif len(content) > 2000:
        errors['content'] = ['Bình luận tối đa 2000 ký tự']

    if errors:
        raise ValidationError('Nội dung bình luận không hợp lệ', fields=errors)

    parent_id = data.get('parent_id', None)
    if parent_id:
        try:
            parent_id = uuid.UUID(str(parent_id))
        except (ValueError, AttributeError):
            raise ValidationError(
                'parent_id không hợp lệ',
                fields={'parent_id': ['parent_id phải là UUID hợp lệ']},
            )

    return {
        'content':   sanitize_text(content),
        'parent_id': parent_id,
    }


def validate_report(data: dict) -> dict:
    """Validate báo cáo vi phạm."""
    errors = {}

    target_type = data.get('target_type', '').strip()
    if target_type not in REPORT_TARGETS:
        errors['target_type'] = [f'target_type phải là một trong: {", ".join(REPORT_TARGETS)}']

    target_id = data.get('target_id', '')
    try:
        target_id = uuid.UUID(str(target_id))
    except (ValueError, AttributeError):
        errors['target_id'] = ['target_id phải là UUID hợp lệ']

    reason = data.get('reason', '').strip()
    if reason not in REPORT_REASONS:
        errors['reason'] = [f'reason phải là một trong: {", ".join(REPORT_REASONS)}']

    if errors:
        raise ValidationError('Dữ liệu báo cáo không hợp lệ', fields=errors)

    return {
        'target_type': target_type,
        'target_id':   target_id,
        'reason':      reason,
        'description': sanitize_text(data.get('description', '')),
    }


def validate_list_songs_params(params: dict) -> dict:
    """Validate và làm sạch query params khi list bài hát."""
    try:
        page = max(1, int(params.get('page', 1)))
    except (ValueError, TypeError):
        page = 1

    try:
        page_size = min(100, max(1, int(params.get('page_size', 20))))
    except (ValueError, TypeError):
        page_size = 20

    ordering = params.get('ordering', '-created_at')
    if ordering not in VALID_ORDERINGS:
        ordering = '-created_at'

    return {
        'q':         params.get('q', '').strip(),
        'genre':     params.get('genre', '').strip(),
        'artist_id': params.get('artist_id', '').strip(),
        'ordering':  ordering,
        'page':      page,
        'page_size': page_size,
    }
```

---

## `music/selectors.py`

```python
"""
music/selectors.py
==================
Tầng Đọc cho app music — mọi truy vấn DB chỉ viết ở đây.

Quy ước:
  - CHỈ đọc dữ liệu, KHÔNG ghi
  - Prefix: get_*, list_*, count_*, is_*, check_*
  - KHÔNG raise HTTP exception
"""

import math
from django.db.models import Avg, Count, Q

from music.models import Genre, Song, Like, Rating, Comment, ListenHistory, Report
from music.exceptions import (
    SongNotFound, GenreNotFound, CommentNotFound, ReportNotFound
)
from accounts.selectors import is_blocked


# ── Genre ─────────────────────────────────────────────────────────────────────

def list_genres() -> list:
    """Trả danh sách tất cả thể loại kèm số bài hát published."""
    genres = Genre.objects.all().order_by('name')
    return [g.to_dict(include_song_count=True) for g in genres]


def get_genre_by_id(genre_id) -> Genre:
    """
    Lấy Genre theo UUID.
    Raises:
        GenreNotFound: nếu không tồn tại
    """
    try:
        return Genre.objects.get(id=genre_id)
    except Genre.DoesNotExist:
        raise GenreNotFound()


def get_genre_by_slug(slug: str) -> Genre | None:
    """Lấy Genre theo slug. Trả None nếu không tìm thấy."""
    return Genre.objects.filter(slug=slug).first()


# ── Song ──────────────────────────────────────────────────────────────────────

def list_songs(filters: dict, viewer=None) -> dict:
    """
    Danh sách bài hát với filter + phân trang.

    Business rules:
    - Anonymous/user thường: chỉ thấy status=published
    - Artist: thấy published + draft của chính mình
    - Ẩn bài hát của người đã block viewer (Fix R10)

    Args:
        filters: dict từ validate_list_songs_params()
        viewer:  request.user (có thể AnonymousUser)

    Returns:
        dict gồm 'items' (list) và 'pagination' (dict)
    """
    viewer_id       = getattr(viewer, 'id', None)
    viewer_is_auth  = bool(viewer_id and getattr(viewer, 'is_authenticated', False))
    viewer_role     = getattr(viewer, 'role', None)

    qs = Song.objects.select_related('artist', 'genre')

    # Phân quyền theo role
    if viewer_is_auth and viewer_role == 'artist':
        # Artist thấy published + draft của chính mình
        qs = qs.filter(
            Q(status=Song.STATUS_PUBLISHED) |
            Q(status=Song.STATUS_DRAFT, artist_id=viewer_id)
        )
    elif viewer_is_auth and viewer_role == 'admin':
        pass  # Admin thấy tất cả
    else:
        qs = qs.filter(status=Song.STATUS_PUBLISHED)

    # Ẩn bài hát của người đã block viewer (Fix R10)
    if viewer_is_auth:
        from accounts.models import BlockList
        blocked_artist_ids = BlockList.objects.filter(
            blocked_id=viewer_id
        ).values_list('blocker_id', flat=True)
        qs = qs.exclude(artist_id__in=blocked_artist_ids)

    # Filters
    if filters.get('q'):
        qs = qs.filter(title__icontains=filters['q'])

    if filters.get('genre'):
        genre = get_genre_by_slug(filters['genre'])
        if genre:
            qs = qs.filter(genre=genre)

    if filters.get('artist_id'):
        qs = qs.filter(artist_id=filters['artist_id'])

    # Ordering
    ordering = filters.get('ordering', '-created_at')
    qs = qs.order_by(ordering)

    # Phân trang
    page      = filters.get('page', 1)
    page_size = filters.get('page_size', 20)
    total     = qs.count()
    start     = (page - 1) * page_size
    end       = start + page_size

    items = [
        song.to_dict(viewer=viewer, include_stats=True)
        for song in qs[start:end]
    ]

    return {
        'items': items,
        'pagination': {
            'page':        page,
            'page_size':   page_size,
            'total':       total,
            'total_pages': math.ceil(total / page_size) if total > 0 else 1,
        },
    }


def list_trending_songs(limit=20) -> list:
    """Danh sách bài hát trending (is_trending=True), sắp xếp theo play_count."""
    songs = (
        Song.objects
        .filter(status=Song.STATUS_PUBLISHED, is_trending=True)
        .select_related('artist', 'genre')
        .order_by('-play_count')[:limit]
    )
    return [s.to_dict(include_stats=True) for s in songs]


def get_song_by_id(song_id) -> Song:
    """
    Lấy Song theo UUID — dùng nội bộ trong services (không check block).
    Raises:
        SongNotFound: nếu không tồn tại
    """
    try:
        return Song.objects.select_related('artist', 'genre').get(id=song_id)
    except Song.DoesNotExist:
        raise SongNotFound()


def get_song_detail(song_id, viewer=None) -> Song:
    """
    Lấy Song để trả về cho client.

    Rules:
    - Song status=hidden → NotFound với mọi người
    - Song status=draft → chỉ owner thấy
    - viewer bị artist block → NotFound (Fix R10)

    Raises:
        SongNotFound
    """
    try:
        song = Song.objects.select_related('artist', 'genre').get(id=song_id)
    except Song.DoesNotExist:
        raise SongNotFound()

    viewer_id      = getattr(viewer, 'id', None)
    viewer_is_auth = bool(viewer_id and getattr(viewer, 'is_authenticated', False))

    # Hidden: không ai thấy (kể cả owner)
    if song.status == Song.STATUS_HIDDEN:
        raise SongNotFound()

    # Draft: chỉ owner thấy
    if song.status == Song.STATUS_DRAFT:
        if not viewer_is_auth or str(viewer_id) != str(song.artist_id):
            raise SongNotFound()

    # Block check (Fix R10)
    if viewer_is_auth and is_blocked(viewer_id, song.artist_id):
        raise SongNotFound()

    return song


def get_song_like_count(song_id, viewer=None) -> dict:
    """Trả về like_count và is_liked của viewer."""
    like_count = Like.objects.filter(song_id=song_id).count()
    is_liked   = False
    viewer_id  = getattr(viewer, 'id', None)
    if viewer_id and getattr(viewer, 'is_authenticated', False):
        is_liked = Like.objects.filter(song_id=song_id, user_id=viewer_id).exists()
    return {'like_count': like_count, 'is_liked': is_liked}


def get_song_rating_stats(song_id, viewer=None) -> dict:
    """Trả về avg_rating, rating_count, my_rating."""
    stats = Rating.objects.filter(song_id=song_id).aggregate(
        avg=Avg('score'), count=Count('id')
    )
    my_rating = None
    viewer_id = getattr(viewer, 'id', None)
    if viewer_id and getattr(viewer, 'is_authenticated', False):
        r = Rating.objects.filter(song_id=song_id, user_id=viewer_id).first()
        my_rating = r.score if r else None
    return {
        'avg_rating':   round(stats['avg'], 1) if stats['avg'] else None,
        'rating_count': stats['count'],
        'my_rating':    my_rating,
    }


# ── Comment ───────────────────────────────────────────────────────────────────

def list_comments(song_id, viewer=None, page=1, page_size=20) -> dict:
    """
    Danh sách bình luận gốc kèm replies.

    Chỉ trả is_hidden=False.
    Replies được load cùng (prefetch).
    """
    qs = (
        Comment.objects
        .filter(song_id=song_id, parent__isnull=True, is_hidden=False)
        .select_related('user')
        .prefetch_related('replies__user', 'replies__comment_likes',
                          'comment_likes')
        .order_by('created_at')
    )

    total = qs.count()
    start = (page - 1) * page_size
    items = [
        c.to_dict(viewer=viewer, include_replies=True)
        for c in qs[start:start + page_size]
    ]
    return {
        'items': items,
        'pagination': {
            'page':        page,
            'page_size':   page_size,
            'total':       total,
            'total_pages': math.ceil(total / page_size) if total > 0 else 1,
        },
    }


def get_comment_by_id(comment_id) -> Comment:
    """
    Lấy Comment theo UUID.
    Raises:
        CommentNotFound: nếu không tồn tại hoặc đã ẩn
    """
    try:
        return Comment.objects.select_related('user', 'song').get(
            id=comment_id, is_hidden=False
        )
    except Comment.DoesNotExist:
        raise CommentNotFound()


# ── ListenHistory ─────────────────────────────────────────────────────────────

def list_listen_history(user, page=1, page_size=20) -> dict:
    """Lịch sử nghe của user, kèm thông tin bài hát."""
    qs = (
        ListenHistory.objects
        .filter(user=user)
        .select_related('song__artist', 'song__genre')
        .order_by('-listened_at')
    )

    total = qs.count()
    start = (page - 1) * page_size
    items = []
    for h in qs[start:start + page_size]:
        items.append({
            'song': {
                'id':           str(h.song_id),
                'title':        h.song.title,
                'artist':       {'display_name': h.song.artist.get_display_name()},
                'cover_image':  h.song.cover_image.url if h.song.cover_image else None,
                'duration':     h.song.duration,
            },
            'listened_at': h.listened_at.isoformat(),
        })

    return {
        'items': items,
        'pagination': {
            'page':        page,
            'page_size':   page_size,
            'total':       total,
            'total_pages': math.ceil(total / page_size) if total > 0 else 1,
        },
    }


# ── Report ────────────────────────────────────────────────────────────────────

def list_reports(filters: dict) -> dict:
    """Danh sách báo cáo cho Admin."""
    qs = Report.objects.select_related('reporter', 'resolved_by')

    if filters.get('status'):
        qs = qs.filter(status=filters['status'])

    if filters.get('target_type'):
        qs = qs.filter(target_type=filters['target_type'])

    page      = int(filters.get('page', 1))
    page_size = int(filters.get('page_size', 20))
    total     = qs.count()
    start     = (page - 1) * page_size

    return {
        'items': [r.to_dict() for r in qs[start:start + page_size]],
        'pagination': {
            'page': page, 'page_size': page_size, 'total': total,
            'total_pages': math.ceil(total / page_size) if total > 0 else 1,
        },
    }


def get_report_by_id(report_id) -> Report:
    """
    Lấy Report theo UUID.
    Raises:
        ReportNotFound
    """
    try:
        return Report.objects.get(id=report_id)
    except Report.DoesNotExist:
        raise ReportNotFound()
```

---

## `music/services.py`

```python
"""
music/services.py
=================
Tầng Ghi cho app music — mọi logic Create/Update/Delete ở đây.

Điểm kỹ thuật quan trọng:
  - record_play(): F() expression atomic + dedup 5 phút (Fix R1, R8)
  - create_song(): upload lên Cloudinary qua Django storage
  - publish_song(): chỉ owner, chỉ từ draft (Fix R9)
"""

import logging
import uuid as uuid_lib
from datetime import timedelta

from django.db.models import F
from django.utils import timezone

from music.models import (
    Genre, Song, Like, Rating,
    Comment, CommentLike, ListenHistory, Report,
)
from music.selectors import get_genre_by_id, get_song_by_id, get_comment_by_id, get_report_by_id
from music.exceptions import (
    NotSongOwner, SongAlreadyPublished, BlockedByArtist,
    GenreHasSongs, NotCommentOwner, InvalidParentComment,
)
from accounts.exceptions import ValidationError, NotFound, PermissionDenied
from accounts.selectors import is_blocked

logger = logging.getLogger(__name__)


# ── Genre ─────────────────────────────────────────────────────────────────────

def create_genre(data: dict) -> Genre:
    """Tạo thể loại mới."""
    from music.models import Genre as G
    if G.objects.filter(name__iexact=data['name']).exists():
        raise ValidationError(
            'Thể loại đã tồn tại',
            fields={'name': ['Tên thể loại này đã tồn tại']},
        )
    genre = G.objects.create(
        name=data['name'],
        description=data.get('description', ''),
    )
    logger.info('Genre created: %s', genre.name)
    return genre


def update_genre(genre: Genre, data: dict) -> Genre:
    """Cập nhật thể loại."""
    from music.models import Genre as G
    if G.objects.filter(name__iexact=data['name']).exclude(id=genre.id).exists():
        raise ValidationError(
            'Thể loại đã tồn tại',
            fields={'name': ['Tên thể loại này đã tồn tại']},
        )
    genre.name        = data['name']
    genre.description = data.get('description', genre.description)
    genre.slug        = ''   # reset để save() tự tính lại
    genre.save()
    return genre


def delete_genre(genre: Genre) -> None:
    """Xóa thể loại — chặn nếu còn bài hát liên kết."""
    if genre.songs.exists():
        raise GenreHasSongs()
    genre.delete()


# ── Song ──────────────────────────────────────────────────────────────────────

def create_song(artist, data: dict, files: dict) -> Song:
    """
    Tạo bài hát mới và upload file lên Cloudinary.

    Files được Django storage (Cloudinary) tự xử lý khi gán vào FileField.
    Path pattern (§12.3): audio/<artist_id>/<uuid>.<ext>
    """
    genre = get_genre_by_id(data['genre_id'])

    song = Song(
        title          = data['title'],
        artist         = artist,
        genre          = genre,
        lyrics         = data.get('lyrics', ''),
        duration       = data['duration'],
        allow_download = data.get('allow_download', False),
        released_at    = data.get('released_at', None),
        status         = Song.STATUS_DRAFT,
    )

    # Gán file → Django storage tự upload lên Cloudinary
    song.audio_file = files['audio_file']
    if 'cover_image' in files:
        song.cover_image = files['cover_image']

    song.save()
    logger.info('Song created: %s (artist=%s)', song.title, artist.username)
    return song


def update_song(song: Song, artist, data: dict, files: dict) -> Song:
    """Cập nhật thông tin bài hát — chỉ owner."""
    if str(song.artist_id) != str(artist.id):
        raise NotSongOwner()

    # Cập nhật từng field nếu có trong data
    for field in ('title', 'lyrics', 'allow_download'):
        if field in data:
            setattr(song, field, data[field])

    if 'genre_id' in data:
        song.genre = get_genre_by_id(data['genre_id'])

    if 'cover_image' in files:
        # Xóa cover cũ trên Cloudinary nếu có
        if song.cover_image:
            try:
                song.cover_image.delete(save=False)
            except Exception:
                pass
        song.cover_image = files['cover_image']

    song.save()
    logger.info('Song updated: %s', song.title)
    return song


def delete_song(song: Song, artist) -> None:
    """Xóa bài hát — chỉ owner."""
    if str(song.artist_id) != str(artist.id):
        raise NotSongOwner()

    # Xóa file trên Cloudinary
    try:
        if song.audio_file:
            song.audio_file.delete(save=False)
        if song.cover_image:
            song.cover_image.delete(save=False)
    except Exception as e:
        logger.warning('Failed to delete Cloudinary files for song %s: %s', song.id, e)

    song.delete()
    logger.info('Song deleted: %s', song.id)


def publish_song(song: Song, artist) -> Song:
    """
    Phát hành bài hát: draft → published.
    Chỉ owner mới publish được (Fix R9).
    """
    if str(song.artist_id) != str(artist.id):
        raise NotSongOwner()

    if song.status != Song.STATUS_DRAFT:
        raise SongAlreadyPublished()

    song.status = Song.STATUS_PUBLISHED
    if not song.released_at:
        song.released_at = timezone.now()
    song.save(update_fields=['status', 'released_at', 'updated_at'])

    logger.info('Song published: %s', song.title)
    return song


def hide_song(song: Song, artist) -> Song:
    """Nghệ sĩ ẩn bài hát của mình."""
    if str(song.artist_id) != str(artist.id):
        raise NotSongOwner()
    song.status = Song.STATUS_HIDDEN
    song.save(update_fields=['status', 'updated_at'])
    return song


def admin_hide_song(song: Song) -> Song:
    """Admin ẩn bài hát vi phạm."""
    song.status = Song.STATUS_HIDDEN
    song.save(update_fields=['status', 'updated_at'])
    return song


def admin_toggle_trending(song: Song) -> Song:
    """Admin bật/tắt trending."""
    song.is_trending = not song.is_trending
    song.save(update_fields=['is_trending', 'updated_at'])
    return song


# ── Play & ListenHistory ──────────────────────────────────────────────────────

def record_play(user, song: Song) -> int:
    """
    Ghi lượt nghe với:
    1. Atomic F() increment (Fix R1) — không race condition
    2. Dedup 5 phút (Fix R8) — không spam counter

    Returns:
        play_count hiện tại (sau khi tăng nếu hợp lệ)
    """
    cutoff = timezone.now() - timedelta(minutes=5)

    # Kiểm tra đã nghe trong 5 phút chưa (Fix R8)
    already_played = ListenHistory.objects.filter(
        user=user,
        song=song,
        listened_at__gte=cutoff,
    ).exists()

    if not already_played:
        # Atomic increment — SQL: UPDATE SET play_count = play_count + 1 (Fix R1)
        Song.objects.filter(id=song.id).update(play_count=F('play_count') + 1)
        ListenHistory.objects.create(user=user, song=song)

        # Log FriendActivity (không block luồng chính nếu lỗi)
        try:
            from social.services import create_friend_activity
            create_friend_activity(user=user, activity_type='playing', song=song)
        except Exception as e:
            logger.debug('FriendActivity log skipped: %s', e)

    # Lấy play_count mới nhất từ DB
    song.refresh_from_db(fields=['play_count'])
    return song.play_count


def clear_listen_history(user) -> int:
    """Xóa toàn bộ lịch sử nghe của user. Trả số bản ghi đã xóa."""
    deleted, _ = ListenHistory.objects.filter(user=user).delete()
    return deleted


# ── Like ──────────────────────────────────────────────────────────────────────

def toggle_like(user, song: Song) -> dict:
    """
    Toggle like/unlike bài hát.

    Returns:
        dict gồm action ('liked'|'unliked') và like_count
    """
    like, created = Like.objects.get_or_create(user=user, song=song)

    if not created:
        # Đã like → unlike
        like.delete()
        action = 'unliked'
    else:
        action = 'liked'

    like_count = Like.objects.filter(song=song).count()
    return {'action': action, 'like_count': like_count}


# ── Rating ────────────────────────────────────────────────────────────────────

def upsert_rating(user, song: Song, score: int) -> dict:
    """
    Upsert rating — mỗi user chỉ có 1 rating/bài.
    Gửi lại sẽ cập nhật score cũ.
    """
    from django.db.models import Avg, Count

    Rating.objects.update_or_create(
        user=user,
        song=song,
        defaults={'score': score},
    )

    stats = Rating.objects.filter(song=song).aggregate(avg=Avg('score'), count=Count('id'))
    return {
        'score':        score,
        'avg_rating':   round(stats['avg'], 1) if stats['avg'] else None,
        'rating_count': stats['count'],
    }


# ── Comment ───────────────────────────────────────────────────────────────────

def create_comment(user, song: Song, data: dict) -> Comment:
    """
    Tạo bình luận mới.

    Rules:
    - Nếu viewer bị artist block → BlockedByArtist (Fix R10)
    - parent_id phải thuộc cùng bài hát và là comment gốc
    """
    # Block check (Fix R10)
    if is_blocked(viewer_id=user.id, target_id=song.artist_id):
        raise BlockedByArtist()

    parent = None
    if data.get('parent_id'):
        try:
            parent = Comment.objects.get(
                id=data['parent_id'],
                song=song,
                is_hidden=False,
            )
        except Comment.DoesNotExist:
            raise InvalidParentComment('Bình luận cha không tồn tại hoặc thuộc bài hát khác')

        # Không cho reply của reply (max 1 cấp)
        if parent.parent_id is not None:
            raise InvalidParentComment('Không thể trả lời bình luận đã là reply')

    comment = Comment.objects.create(
        user    = user,
        song    = song,
        parent  = parent,
        content = data['content'],
    )
    logger.info('Comment created: user=%s, song=%s', user.username, song.id)
    return comment


def delete_comment(comment: Comment, user) -> None:
    """Xóa bình luận — chỉ owner."""
    if str(comment.user_id) != str(user.id):
        raise NotCommentOwner()
    comment.delete()


def admin_hide_comment(comment: Comment) -> Comment:
    """Admin ẩn bình luận vi phạm (soft delete)."""
    comment.is_hidden = True
    comment.save(update_fields=['is_hidden'])
    return comment


def toggle_comment_like(user, comment: Comment) -> dict:
    """Toggle like/unlike bình luận."""
    like, created = CommentLike.objects.get_or_create(user=user, comment=comment)
    if not created:
        like.delete()
        action = 'unliked'
    else:
        action = 'liked'
    like_count = CommentLike.objects.filter(comment=comment).count()
    return {'action': action, 'like_count': like_count}


# ── Report ────────────────────────────────────────────────────────────────────

def create_report(reporter, data: dict) -> Report:
    """Tạo báo cáo vi phạm."""
    report = Report.objects.create(
        reporter    = reporter,
        target_type = data['target_type'],
        target_id   = data['target_id'],
        reason      = data['reason'],
        description = data.get('description', ''),
        status      = Report.STATUS_PENDING,
    )
    logger.info('Report created: %s/%s by %s', data['target_type'], data['target_id'], reporter.username)
    return report


def resolve_report(report: Report, admin, action: str, note: str = '') -> Report:
    """Admin xử lý báo cáo (resolved hoặc dismissed)."""
    if action not in (Report.STATUS_RESOLVED, Report.STATUS_DISMISSED):
        raise ValidationError(
            'action không hợp lệ',
            fields={'action': ['action phải là "resolved" hoặc "dismissed"']},
        )
    report.status        = action
    report.resolved_by   = admin
    report.resolved_note = note
    report.save(update_fields=['status', 'resolved_by', 'resolved_note'])
    return report
```

---

## `music/views.py`

```python
"""
music/views.py
==============
Tầng HTTP cho app music.

Quy ước:
  - views.py KHÔNG import Song, Genre, Comment... để query trực tiếp
  - Mọi query qua selectors.py, mọi ghi qua services.py
  - Exception từ services/selectors được map sang HTTP status
"""

import json
import logging

from django.http import JsonResponse
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect

from accounts.decorators import require_auth, require_artist, require_admin
from accounts.exceptions import (
    ValidationError, PermissionDenied, NotFound,
    AlreadyExists, AppException,
)
from music.exceptions import (
    SongNotFound, GenreNotFound, CommentNotFound,
    NotSongOwner, NotCommentOwner, DownloadNotAllowed,
    BlockedByArtist, GenreHasSongs, SongAlreadyPublished,
    InvalidParentComment, ReportNotFound,
)
from music.validators import (
    validate_genre, validate_song_create, validate_song_update,
    validate_rating, validate_comment, validate_report,
    validate_list_songs_params,
)
from music.selectors import (
    list_genres, get_genre_by_id,
    list_songs, list_trending_songs, get_song_by_id, get_song_detail,
    get_song_like_count, get_song_rating_stats,
    list_comments, get_comment_by_id,
    list_listen_history,
    list_reports, get_report_by_id,
)
from music.services import (
    create_genre, update_genre, delete_genre,
    create_song, update_song, delete_song, publish_song, hide_song,
    admin_hide_song, admin_toggle_trending,
    record_play,
    toggle_like,
    upsert_rating,
    create_comment, delete_comment, admin_hide_comment, toggle_comment_like,
    clear_listen_history,
    create_report, resolve_report,
)

logger = logging.getLogger(__name__)


# ── Helpers ───────────────────────────────────────────────────────────────────

def parse_json_body(request) -> dict:
    """Parse JSON body an toàn."""
    try:
        return json.loads(request.body or '{}')
    except (json.JSONDecodeError, ValueError):
        return {}


def handle_exception(e: Exception) -> JsonResponse:
    """Map exception nghiệp vụ sang HTTP response chuẩn."""
    if isinstance(e, ValidationError):
        return JsonResponse(
            {'success': False, 'error': {'code': 'VALIDATION_ERROR',
                                          'message': e.message, 'fields': e.fields}},
            status=400,
        )
    if isinstance(e, (GenreHasSongs, SongAlreadyPublished, InvalidParentComment)):
        return JsonResponse(
            {'success': False, 'error': {'code': e.error_code, 'message': e.message}},
            status=400,
        )
    if isinstance(e, (NotSongOwner, NotCommentOwner, PermissionDenied,
                      DownloadNotAllowed, BlockedByArtist)):
        return JsonResponse(
            {'success': False, 'error': {'code': e.error_code, 'message': e.message}},
            status=403,
        )
    if isinstance(e, (SongNotFound, GenreNotFound, CommentNotFound,
                      ReportNotFound, NotFound)):
        return JsonResponse(
            {'success': False, 'error': {'code': 'NOT_FOUND', 'message': e.message}},
            status=404,
        )
    if isinstance(e, AlreadyExists):
        return JsonResponse(
            {'success': False, 'error': {'code': 'ALREADY_EXISTS', 'message': e.message}},
            status=409,
        )
    logger.exception('Unhandled exception in music views: %s', e)
    return JsonResponse(
        {'success': False, 'error': {'code': 'SERVER_ERROR', 'message': 'Lỗi server'}},
        status=500,
    )


# ── Genre Views ───────────────────────────────────────────────────────────────

class GenreListView(View):
    """
    GET  /api/v1/music/genres/  — Public
    POST /api/v1/music/genres/  — Admin
    """

    def get(self, request):
        genres = list_genres()
        return JsonResponse({'success': True, 'data': {'items': genres, 'total': len(genres)}})

    @method_decorator(csrf_protect)
    @method_decorator(require_admin)
    def post(self, request):
        try:
            data      = parse_json_body(request)
            validated = validate_genre(data)
            genre     = create_genre(validated)
            return JsonResponse({'success': True, 'data': genre.to_dict()}, status=201)
        except Exception as e:
            return handle_exception(e)


class GenreDetailView(View):
    """
    PUT    /api/v1/music/genres/<id>/  — Admin
    DELETE /api/v1/music/genres/<id>/  — Admin
    """

    @method_decorator(csrf_protect)
    @method_decorator(require_admin)
    def put(self, request, genre_id):
        try:
            data      = parse_json_body(request)
            validated = validate_genre(data)
            genre     = get_genre_by_id(genre_id)
            genre     = update_genre(genre, validated)
            return JsonResponse({'success': True, 'data': genre.to_dict()})
        except Exception as e:
            return handle_exception(e)

    @method_decorator(csrf_protect)
    @method_decorator(require_admin)
    def delete(self, request, genre_id):
        try:
            genre = get_genre_by_id(genre_id)
            delete_genre(genre)
            return JsonResponse({'success': True}, status=204)
        except Exception as e:
            return handle_exception(e)


# ── Song Views ────────────────────────────────────────────────────────────────

class SongListView(View):
    """
    GET  /api/v1/music/songs/  — Public
    POST /api/v1/music/songs/  — Artist
    """

    def get(self, request):
        try:
            filters = validate_list_songs_params(request.GET)
            result  = list_songs(filters, viewer=request.user)
            return JsonResponse({'success': True, 'data': result})
        except Exception as e:
            return handle_exception(e)

    @method_decorator(csrf_protect)
    @method_decorator(require_artist)
    def post(self, request):
        try:
            # multipart/form-data: data từ POST, files từ FILES
            validated = validate_song_create(request.POST, request.FILES)
            song      = create_song(artist=request.user, data=validated, files=request.FILES)
            return JsonResponse({'success': True, 'data': song.to_dict(viewer=request.user)}, status=201)
        except Exception as e:
            return handle_exception(e)


class SongTrendingView(View):
    """GET /api/v1/music/songs/trending/ — Public"""

    def get(self, request):
        songs = list_trending_songs()
        return JsonResponse({'success': True, 'data': {'items': songs, 'total': len(songs)}})


class SongDetailView(View):
    """
    GET    /api/v1/music/songs/<id>/  — Public
    PATCH  /api/v1/music/songs/<id>/  — Artist+Owner
    DELETE /api/v1/music/songs/<id>/  — Artist+Owner
    """

    def get(self, request, song_id):
        try:
            song = get_song_detail(song_id, viewer=request.user)
            return JsonResponse({'success': True, 'data': song.to_dict(viewer=request.user)})
        except Exception as e:
            return handle_exception(e)

    @method_decorator(csrf_protect)
    @method_decorator(require_artist)
    def patch(self, request, song_id):
        try:
            song      = get_song_by_id(song_id)
            validated = validate_song_update(request.POST, request.FILES)
            if not validated:
                return JsonResponse(
                    {'success': False, 'error': {'code': 'VALIDATION_ERROR',
                                                  'message': 'Không có dữ liệu để cập nhật'}},
                    status=400,
                )
            song = update_song(song, request.user, validated, request.FILES)
            return JsonResponse({'success': True, 'data': song.to_dict(viewer=request.user)})
        except Exception as e:
            return handle_exception(e)

    @method_decorator(csrf_protect)
    @method_decorator(require_artist)
    def delete(self, request, song_id):
        try:
            song = get_song_by_id(song_id)
            delete_song(song, request.user)
            return JsonResponse({'success': True}, status=204)
        except Exception as e:
            return handle_exception(e)


class SongPublishView(View):
    """POST /api/v1/music/songs/<id>/publish/ — Artist+Owner (Fix R9)"""

    @method_decorator(csrf_protect)
    @method_decorator(require_artist)
    def post(self, request, song_id):
        try:
            song = get_song_by_id(song_id)
            song = publish_song(song, request.user)
            return JsonResponse({
                'success': True,
                'data': {
                    'id':          str(song.id),
                    'status':      song.status,
                    'released_at': song.released_at.isoformat() if song.released_at else None,
                },
            })
        except Exception as e:
            return handle_exception(e)


class SongHideView(View):
    """POST /api/v1/music/songs/<id>/hide/ — Artist+Owner"""

    @method_decorator(csrf_protect)
    @method_decorator(require_artist)
    def post(self, request, song_id):
        try:
            song = get_song_by_id(song_id)
            song = hide_song(song, request.user)
            return JsonResponse({'success': True, 'data': {'id': str(song.id), 'status': song.status}})
        except Exception as e:
            return handle_exception(e)


class SongPlayView(View):
    """POST /api/v1/music/songs/<id>/play/ — Auth"""

    @method_decorator(require_auth)
    def post(self, request, song_id):
        try:
            song       = get_song_detail(song_id, viewer=request.user)
            play_count = record_play(request.user, song)
            return JsonResponse({'success': True, 'data': {'play_count': play_count}})
        except Exception as e:
            return handle_exception(e)


class SongDownloadView(View):
    """
    GET /api/v1/music/songs/<id>/download/ — Auth (Fix R2)

    Trả Cloudinary signed URL (redirect) khi production,
    hoặc URL file trực tiếp khi dev.
    """

    @method_decorator(require_auth)
    def get(self, request, song_id):
        try:
            song = get_song_detail(song_id, viewer=request.user)

            if song.status != Song.STATUS_PUBLISHED:
                raise SongNotFound()

            if not song.allow_download:
                raise DownloadNotAllowed()

            # Trả URL của file trên Cloudinary
            audio_url = song.audio_file.url if song.audio_file else None
            if not audio_url:
                raise SongNotFound('File audio không tồn tại')

            ext      = song.audio_file.name.split('.')[-1] if '.' in song.audio_file.name else 'mp3'
            filename = f"{song.title}.{ext}"

            return JsonResponse({
                'success': True,
                'data': {
                    'download_url': audio_url,
                    'filename':     filename,
                    'expires_in':   300,  # giây (Cloudinary signed URL)
                },
            })
        except Exception as e:
            return handle_exception(e)


# Thêm import Song ở đây vì SongDownloadView.get dùng Song.STATUS_PUBLISHED
from music.models import Song


# ── Like Views ────────────────────────────────────────────────────────────────

class SongLikeView(View):
    """
    GET  /api/v1/music/songs/<id>/likes/  — Public
    POST /api/v1/music/songs/<id>/like/   — Auth+CSRF
    """

    def get(self, request, song_id):
        try:
            result = get_song_like_count(song_id, viewer=request.user)
            return JsonResponse({'success': True, 'data': result})
        except Exception as e:
            return handle_exception(e)

    @method_decorator(csrf_protect)
    @method_decorator(require_auth)
    def post(self, request, song_id):
        try:
            song   = get_song_detail(song_id, viewer=request.user)
            result = toggle_like(request.user, song)
            return JsonResponse({'success': True, 'data': result})
        except Exception as e:
            return handle_exception(e)


# ── Rating Views ──────────────────────────────────────────────────────────────

class SongRatingView(View):
    """
    GET  /api/v1/music/songs/<id>/rating/  — Public
    POST /api/v1/music/songs/<id>/rate/    — Auth+CSRF
    """

    def get(self, request, song_id):
        try:
            result = get_song_rating_stats(song_id, viewer=request.user)
            return JsonResponse({'success': True, 'data': result})
        except Exception as e:
            return handle_exception(e)

    @method_decorator(csrf_protect)
    @method_decorator(require_auth)
    def post(self, request, song_id):
        try:
            data      = parse_json_body(request)
            validated = validate_rating(data)
            song      = get_song_detail(song_id, viewer=request.user)
            result    = upsert_rating(request.user, song, validated['score'])
            return JsonResponse({'success': True, 'data': result})
        except Exception as e:
            return handle_exception(e)


# ── Comment Views ─────────────────────────────────────────────────────────────

class SongCommentListView(View):
    """
    GET  /api/v1/music/songs/<id>/comments/  — Public
    POST /api/v1/music/songs/<id>/comments/  — Auth+CSRF
    """

    def get(self, request, song_id):
        try:
            page      = int(request.GET.get('page', 1))
            page_size = min(100, int(request.GET.get('page_size', 20)))
            result    = list_comments(song_id, viewer=request.user,
                                       page=page, page_size=page_size)
            return JsonResponse({'success': True, 'data': result})
        except Exception as e:
            return handle_exception(e)

    @method_decorator(csrf_protect)
    @method_decorator(require_auth)
    def post(self, request, song_id):
        try:
            song      = get_song_detail(song_id, viewer=request.user)
            data      = parse_json_body(request)
            validated = validate_comment(data)
            comment   = create_comment(request.user, song, validated)
            return JsonResponse(
                {'success': True, 'data': comment.to_dict(viewer=request.user)},
                status=201,
            )
        except Exception as e:
            return handle_exception(e)


class CommentDetailView(View):
    """DELETE /api/v1/music/comments/<id>/ — Auth+Owner+CSRF"""

    @method_decorator(csrf_protect)
    @method_decorator(require_auth)
    def delete(self, request, comment_id):
        try:
            comment = get_comment_by_id(comment_id)
            delete_comment(comment, request.user)
            return JsonResponse({'success': True}, status=204)
        except Exception as e:
            return handle_exception(e)


class CommentLikeView(View):
    """POST /api/v1/music/comments/<id>/like/ — Auth+CSRF"""

    @method_decorator(csrf_protect)
    @method_decorator(require_auth)
    def post(self, request, comment_id):
        try:
            comment = get_comment_by_id(comment_id)
            result  = toggle_comment_like(request.user, comment)
            return JsonResponse({'success': True, 'data': result})
        except Exception as e:
            return handle_exception(e)


# ── ListenHistory Views ───────────────────────────────────────────────────────

class ListenHistoryView(View):
    """
    GET    /api/v1/music/me/history/  — Auth
    DELETE /api/v1/music/me/history/  — Auth+CSRF
    """

    @method_decorator(require_auth)
    def get(self, request):
        try:
            page      = int(request.GET.get('page', 1))
            page_size = min(100, int(request.GET.get('page_size', 20)))
            result    = list_listen_history(request.user, page=page, page_size=page_size)
            return JsonResponse({'success': True, 'data': result})
        except Exception as e:
            return handle_exception(e)

    @method_decorator(csrf_protect)
    @method_decorator(require_auth)
    def delete(self, request):
        try:
            clear_listen_history(request.user)
            return JsonResponse({'success': True}, status=204)
        except Exception as e:
            return handle_exception(e)


# ── Report Views ──────────────────────────────────────────────────────────────

class ReportCreateView(View):
    """POST /api/v1/music/reports/ — Auth+CSRF"""

    @method_decorator(csrf_protect)
    @method_decorator(require_auth)
    def post(self, request):
        try:
            data      = parse_json_body(request)
            validated = validate_report(data)
            report    = create_report(request.user, validated)
            return JsonResponse({'success': True, 'data': report.to_dict()}, status=201)
        except Exception as e:
            return handle_exception(e)


class AdminReportListView(View):
    """GET /api/v1/music/admin/reports/ — Admin"""

    @method_decorator(require_admin)
    def get(self, request):
        try:
            filters = {
                'status':      request.GET.get('status', ''),
                'target_type': request.GET.get('target_type', ''),
                'page':        request.GET.get('page', 1),
                'page_size':   request.GET.get('page_size', 20),
            }
            result = list_reports(filters)
            return JsonResponse({'success': True, 'data': result})
        except Exception as e:
            return handle_exception(e)


class AdminReportResolveView(View):
    """POST /api/v1/music/admin/reports/<id>/resolve/ — Admin+CSRF"""

    @method_decorator(csrf_protect)
    @method_decorator(require_admin)
    def post(self, request, report_id):
        try:
            data   = parse_json_body(request)
            action = data.get('action', '').strip()
            note   = data.get('note', '').strip()
            report = get_report_by_id(report_id)
            report = resolve_report(report, request.user, action, note)
            return JsonResponse({'success': True, 'data': report.to_dict()})
        except Exception as e:
            return handle_exception(e)


# ── Admin Song/Comment Views ──────────────────────────────────────────────────

class AdminSongTrendingView(View):
    """POST /api/v1/music/admin/songs/<id>/trending/ — Admin+CSRF"""

    @method_decorator(csrf_protect)
    @method_decorator(require_admin)
    def post(self, request, song_id):
        try:
            song = get_song_by_id(song_id)
            song = admin_toggle_trending(song)
            return JsonResponse({
                'success': True,
                'data': {'id': str(song.id), 'is_trending': song.is_trending},
            })
        except Exception as e:
            return handle_exception(e)


class AdminSongHideView(View):
    """POST /api/v1/music/admin/songs/<id>/hide/ — Admin+CSRF"""

    @method_decorator(csrf_protect)
    @method_decorator(require_admin)
    def post(self, request, song_id):
        try:
            song = get_song_by_id(song_id)
            song = admin_hide_song(song)
            return JsonResponse({
                'success': True,
                'data': {'id': str(song.id), 'status': song.status},
            })
        except Exception as e:
            return handle_exception(e)


class AdminCommentHideView(View):
    """POST /api/v1/music/admin/comments/<id>/hide/ — Admin+CSRF"""

    @method_decorator(csrf_protect)
    @method_decorator(require_admin)
    def post(self, request, comment_id):
        try:
            comment = get_comment_by_id(comment_id)
            comment = admin_hide_comment(comment)
            return JsonResponse({
                'success': True,
                'data': {'id': str(comment.id), 'is_hidden': comment.is_hidden},
            })
        except Exception as e:
            return handle_exception(e)
```

---

## `music/urls.py`

```python
"""
music/urls.py
=============
URLs cho app music — prefix: /api/v1/music/
"""

from django.urls import path
from music.views import (
    GenreListView, GenreDetailView,
    SongListView, SongTrendingView, SongDetailView,
    SongPublishView, SongHideView, SongPlayView, SongDownloadView,
    SongLikeView, SongRatingView,
    SongCommentListView, CommentDetailView, CommentLikeView,
    ListenHistoryView,
    ReportCreateView, AdminReportListView, AdminReportResolveView,
    AdminSongTrendingView, AdminSongHideView, AdminCommentHideView,
)

urlpatterns = [
    # ── Genre ──────────────────────────────────────────────────────────
    path('genres/',               GenreListView.as_view(),   name='music-genre-list'),
    path('genres/<uuid:genre_id>/', GenreDetailView.as_view(), name='music-genre-detail'),

    # ── Song list + create ─────────────────────────────────────────────
    path('songs/',                SongListView.as_view(),    name='music-song-list'),
    path('songs/trending/',       SongTrendingView.as_view(), name='music-song-trending'),

    # ── Song detail ────────────────────────────────────────────────────
    path('songs/<uuid:song_id>/',           SongDetailView.as_view(),  name='music-song-detail'),
    path('songs/<uuid:song_id>/publish/',   SongPublishView.as_view(), name='music-song-publish'),
    path('songs/<uuid:song_id>/hide/',      SongHideView.as_view(),    name='music-song-hide'),
    path('songs/<uuid:song_id>/play/',      SongPlayView.as_view(),    name='music-song-play'),
    path('songs/<uuid:song_id>/download/',  SongDownloadView.as_view(), name='music-song-download'),

    # ── Like & Rating ──────────────────────────────────────────────────
    path('songs/<uuid:song_id>/like/',    SongLikeView.as_view(),   name='music-song-like'),
    path('songs/<uuid:song_id>/likes/',   SongLikeView.as_view(),   name='music-song-likes'),
    path('songs/<uuid:song_id>/rate/',    SongRatingView.as_view(), name='music-song-rate'),
    path('songs/<uuid:song_id>/rating/',  SongRatingView.as_view(), name='music-song-rating'),

    # ── Comments ───────────────────────────────────────────────────────
    path('songs/<uuid:song_id>/comments/', SongCommentListView.as_view(), name='music-comment-list'),
    path('comments/<uuid:comment_id>/',    CommentDetailView.as_view(),   name='music-comment-detail'),
    path('comments/<uuid:comment_id>/like/', CommentLikeView.as_view(),   name='music-comment-like'),

    # ── Listen History ─────────────────────────────────────────────────
    path('me/history/', ListenHistoryView.as_view(), name='music-history'),

    # ── Reports ────────────────────────────────────────────────────────
    path('reports/', ReportCreateView.as_view(), name='music-report-create'),

    # ── Admin ──────────────────────────────────────────────────────────
    path('admin/reports/',                          AdminReportListView.as_view(),    name='music-admin-report-list'),
    path('admin/reports/<uuid:report_id>/resolve/', AdminReportResolveView.as_view(), name='music-admin-report-resolve'),
    path('admin/songs/<uuid:song_id>/trending/',    AdminSongTrendingView.as_view(),  name='music-admin-song-trending'),
    path('admin/songs/<uuid:song_id>/hide/',        AdminSongHideView.as_view(),      name='music-admin-song-hide'),
    path('admin/comments/<uuid:comment_id>/hide/',  AdminCommentHideView.as_view(),   name='music-admin-comment-hide'),
]
```

---

## `music/admin.py`

```python
"""music/admin.py"""
from django.contrib import admin
from music.models import Genre, Song, Like, Rating, Comment, CommentLike, ListenHistory, Report


@admin.register(Genre)
class GenreAdmin(admin.ModelAdmin):
    list_display  = ('name', 'slug', 'created_at')
    search_fields = ('name',)
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Song)
class SongAdmin(admin.ModelAdmin):
    list_display  = ('title', 'artist', 'genre', 'status', 'is_trending', 'play_count', 'created_at')
    list_filter   = ('status', 'is_trending', 'genre')
    search_fields = ('title', 'artist__username')
    readonly_fields = ('play_count', 'created_at', 'updated_at')
    ordering      = ('-created_at',)


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display  = ('user', 'song', 'is_hidden', 'created_at')
    list_filter   = ('is_hidden',)
    search_fields = ('content', 'user__username')


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display  = ('reporter', 'target_type', 'reason', 'status', 'created_at')
    list_filter   = ('status', 'target_type', 'reason')
    readonly_fields = ('created_at',)


@admin.register(Like)
class LikeAdmin(admin.ModelAdmin):
    list_display = ('user', 'song', 'created_at')

@admin.register(Rating)
class RatingAdmin(admin.ModelAdmin):
    list_display = ('user', 'song', 'score', 'created_at')

@admin.register(ListenHistory)
class ListenHistoryAdmin(admin.ModelAdmin):
    list_display = ('user', 'song', 'listened_at')
```
