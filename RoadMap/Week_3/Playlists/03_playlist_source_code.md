# 03 — Source Code Hoàn Chỉnh App `playlists`

**Tuần 3 | Đã verify: 118/118 tests pass riêng app này, 361/361 tests pass toàn hệ thống**

> Copy từng file vào đúng thư mục `playlists/` trong project.
> Sau khi copy xong, xem file `05_playlist_configs_and_db_changes.md` để biết các bước apply.

---

## Cấu Trúc File

```
playlists/
├── __init__.py
├── apps.py
├── models.py
├── exceptions.py
├── validators.py
├── selectors.py
├── services.py
├── views.py
├── urls.py
├── admin.py
└── tests.py
```

---

## `playlists/apps.py`

```python
"""playlists/apps.py"""
from django.apps import AppConfig


class PlaylistsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name  = 'playlists'
    label = 'playlists'
    verbose_name = 'Danh sách phát'
```

---

## `playlists/models.py`

```python
"""
playlists/models.py
====================
Models cho app playlists:
  - Playlist:      Danh sách phát do người dùng tạo
  - PlaylistSong:  Bảng trung gian Playlist <-> Song, có thứ tự (order)

Tất cả PK là UUIDField theo quy ước chung của hệ thống (§12.1).
"""

import uuid
from django.db import models


class Playlist(models.Model):
    """
    Playlist do người dùng tạo.

    Quan hệ:
        - owner: FK -> accounts.User (chủ sở hữu)
        - songs: M2M qua PlaylistSong (có order)

    Quyền truy cập:
        - is_public=True  -> ai cũng xem được (Public)
        - is_public=False -> chỉ owner xem được (Auth+Owner)
    """

    id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    owner       = models.ForeignKey(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='playlists',
        verbose_name='Chủ sở hữu',
        db_index=True,
    )

    title       = models.CharField(max_length=200, verbose_name='Tên playlist')
    description = models.TextField(blank=True, default='', verbose_name='Mô tả')

    # Ảnh bìa lưu trên Cloudinary, path: covers/playlists/<uuid>.<ext> (§12.3)
    cover_image = models.ImageField(
        upload_to='covers/playlists/',
        blank=True,
        null=True,
        verbose_name='Ảnh bìa',
    )

    is_public   = models.BooleanField(default=True, verbose_name='Công khai', db_index=True)

    created_at  = models.DateTimeField(auto_now_add=True, verbose_name='Ngày tạo')
    updated_at  = models.DateTimeField(auto_now=True, verbose_name='Cập nhật lần cuối')

    class Meta:
        db_table     = 'playlists_playlist'
        ordering     = ['-created_at']
        verbose_name = 'Playlist'
        verbose_name_plural = 'Playlist'

    def __str__(self):
        return f'{self.title} ({self.owner.username})'

    def to_dict(self, viewer=None, include_song_count=True):
        """
        Serialize Playlist thành dict.

        Args:
            viewer:             User đang xem (dùng để quyết định is_owner)
            include_song_count: có tính song_count hay không (tốn 1 query COUNT)
        """
        data = {
            'id':          str(self.id),
            'title':       self.title,
            'description': self.description,
            'cover_image': self.cover_image.url if self.cover_image else None,
            'is_public':   self.is_public,
            'owner': {
                'id':           str(self.owner_id),
                'username':     self.owner.username,
                'display_name': self.owner.get_display_name(),
                'avatar':       self.owner.avatar.url if self.owner.avatar else None,
            },
            'created_at':  self.created_at.isoformat(),
            'updated_at':  self.updated_at.isoformat(),
        }
        if include_song_count:
            data['song_count'] = self.playlist_songs.count()

        viewer_id = getattr(viewer, 'id', None)
        if viewer_id and getattr(viewer, 'is_authenticated', False):
            data['is_owner'] = str(viewer_id) == str(self.owner_id)
        else:
            data['is_owner'] = False
        return data


class PlaylistSong(models.Model):
    """
    Bảng trung gian Playlist <-> Song, lưu thứ tự bài hát trong playlist.

    unique_together đảm bảo 1 bài hát không bị thêm trùng vào cùng 1 playlist.
    order dùng để client hiển thị đúng thứ tự và hỗ trợ reorder.
    """

    id        = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    playlist  = models.ForeignKey(
        Playlist,
        on_delete=models.CASCADE,
        related_name='playlist_songs',
        verbose_name='Playlist',
    )
    song      = models.ForeignKey(
        'music.Song',
        on_delete=models.CASCADE,
        related_name='in_playlists',
        verbose_name='Bài hát',
    )

    order     = models.PositiveIntegerField(default=0, verbose_name='Thứ tự')
    added_at  = models.DateTimeField(auto_now_add=True, verbose_name='Ngày thêm')

    class Meta:
        db_table        = 'playlists_playlist_song'
        ordering        = ['order', 'added_at']
        unique_together = [('playlist', 'song')]
        verbose_name    = 'Bài hát trong Playlist'
        verbose_name_plural = 'Bài hát trong Playlist'

    def __str__(self):
        return f'{self.playlist.title} -> {self.song.title} (#{self.order})'

    def to_dict(self):
        return {
            'id':    str(self.id),
            'song': {
                'id':          str(self.song_id),
                'title':       self.song.title,
                'artist': {
                    'id':           str(self.song.artist_id),
                    'username':     self.song.artist.username,
                    'display_name': self.song.artist.get_display_name(),
                },
                'cover_image': self.song.cover_image.url if self.song.cover_image else None,
                'duration':    self.song.duration,
                'status':      self.song.status,
            },
            'order':    self.order,
            'added_at': self.added_at.isoformat(),
        }
```

---

## `playlists/exceptions.py`

```python
"""
playlists/exceptions.py
========================
Custom exceptions cho nghiệp vụ app playlists.

Quy ước: kế thừa AppException từ accounts.exceptions để toàn hệ thống
dùng chung 1 cơ chế error_code + message.
"""

from accounts.exceptions import AppException


class PlaylistNotFound(AppException):
    """Playlist không tồn tại hoặc không có quyền xem (riêng tư) — HTTP 404."""
    def __init__(self, message='Playlist không tồn tại'):
        super().__init__(message, error_code='NOT_FOUND')


class NotPlaylistOwner(AppException):
    """Không phải chủ playlist — HTTP 403."""
    def __init__(self, message='Bạn không có quyền thực hiện hành động này với playlist này'):
        super().__init__(message, error_code='PERMISSION_DENIED')


class SongAlreadyInPlaylist(AppException):
    """Bài hát đã có trong playlist — HTTP 409."""
    def __init__(self, message='Bài hát này đã có trong playlist'):
        super().__init__(message, error_code='ALREADY_EXISTS')


class SongNotInPlaylist(AppException):
    """Bài hát không có trong playlist — HTTP 404."""
    def __init__(self, message='Bài hát không có trong playlist này'):
        super().__init__(message, error_code='NOT_FOUND')


class InvalidReorderData(AppException):
    """Dữ liệu reorder không hợp lệ (thiếu bài, sai ID...) — HTTP 400."""
    def __init__(self, message='Dữ liệu sắp xếp lại không hợp lệ'):
        super().__init__(message, error_code='VALIDATION_ERROR')
```

---

## `playlists/validators.py`

```python
"""
playlists/validators.py
=========================
Kiểm tra dữ liệu đầu vào cho app playlists.

Quy ước (§1.2):
  - CHỈ kiểm tra kiểu dữ liệu, bắt buộc, độ dài, format
  - KHÔNG gọi service, KHÔNG truy vấn DB
  - KHÔNG raise HTTP exception — chỉ raise ValidationError từ accounts.exceptions
"""

import uuid
from accounts.utils import sanitize_text
from accounts.exceptions import ValidationError

TITLE_MAX_LENGTH       = 200
DESCRIPTION_MAX_LENGTH = 1000

ALLOWED_IMAGE_TYPES = {'image/jpeg', 'image/png', 'image/webp'}
MAX_IMAGE_SIZE      = 5 * 1024 * 1024  # 5 MB


def validate_playlist_create(data: dict) -> dict:
    """
    Validate tạo playlist mới.

    Args:
        data: dict từ request.body (JSON), kỳ vọng có: title, description?, is_public?

    Returns:
        dict đã validate và sanitize

    Raises:
        ValidationError: nếu title rỗng hoặc quá dài
    """
    errors = {}

    title = data.get('title', '').strip()
    if not title:
        errors['title'] = ['Tên playlist là bắt buộc']
    elif len(title) > TITLE_MAX_LENGTH:
        errors['title'] = [f'Tên playlist tối đa {TITLE_MAX_LENGTH} ký tự']

    description = data.get('description', '')
    if len(description) > DESCRIPTION_MAX_LENGTH:
        errors['description'] = [f'Mô tả tối đa {DESCRIPTION_MAX_LENGTH} ký tự']

    is_public = data.get('is_public', True)
    if not isinstance(is_public, bool):
        if isinstance(is_public, str):
            is_public = is_public.lower() in ('true', '1', 'yes')
        else:
            is_public = bool(is_public)

    if errors:
        raise ValidationError('Dữ liệu playlist không hợp lệ', fields=errors)

    return {
        'title':       sanitize_text(title),
        'description': sanitize_text(description),
        'is_public':   is_public,
    }


def validate_playlist_update(data: dict) -> dict:
    """
    Validate cập nhật playlist — partial update (chỉ field nào gửi lên mới validate).

    Returns:
        dict chỉ chứa các field hợp lệ được gửi lên
    """
    errors = {}
    result = {}

    if 'title' in data:
        title = data['title'].strip()
        if not title:
            errors['title'] = ['Tên playlist không được để trống']
        elif len(title) > TITLE_MAX_LENGTH:
            errors['title'] = [f'Tên playlist tối đa {TITLE_MAX_LENGTH} ký tự']
        else:
            result['title'] = sanitize_text(title)

    if 'description' in data:
        description = data['description']
        if len(description) > DESCRIPTION_MAX_LENGTH:
            errors['description'] = [f'Mô tả tối đa {DESCRIPTION_MAX_LENGTH} ký tự']
        else:
            result['description'] = sanitize_text(description)

    if errors:
        raise ValidationError('Dữ liệu cập nhật không hợp lệ', fields=errors)

    return result


def validate_visibility(data: dict) -> dict:
    """Validate đặt công khai / riêng tư."""
    is_public = data.get('is_public')
    if is_public is None or not isinstance(is_public, bool):
        raise ValidationError(
            'Dữ liệu không hợp lệ',
            fields={'is_public': ['Giá trị phải là true hoặc false']},
        )
    return {'is_public': is_public}


def validate_add_song(data: dict) -> dict:
    """
    Validate thêm bài hát vào playlist.

    Raises:
        ValidationError: nếu thiếu song_id hoặc sai định dạng UUID
    """
    song_id = data.get('song_id', '')
    if not song_id:
        raise ValidationError(
            'Dữ liệu không hợp lệ',
            fields={'song_id': ['song_id là bắt buộc']},
        )
    try:
        song_id = uuid.UUID(str(song_id))
    except (ValueError, AttributeError):
        raise ValidationError(
            'Dữ liệu không hợp lệ',
            fields={'song_id': ['song_id không đúng định dạng UUID']},
        )
    return {'song_id': song_id}


def validate_reorder(data: dict) -> dict:
    """
    Validate dữ liệu sắp xếp lại thứ tự bài hát.

    Kỳ vọng: { "song_ids": ["uuid1", "uuid2", ...] }
    Chỉ validate format — kiểm tra song_ids có khớp với playlist hay không
    sẽ được service xử lý (cần query DB).
    """
    song_ids = data.get('song_ids', None)

    if song_ids is None or not isinstance(song_ids, list):
        raise ValidationError(
            'Dữ liệu không hợp lệ',
            fields={'song_ids': ['song_ids phải là một danh sách UUID']},
        )

    if len(song_ids) == 0:
        raise ValidationError(
            'Dữ liệu không hợp lệ',
            fields={'song_ids': ['song_ids không được rỗng']},
        )

    parsed_ids = []
    for sid in song_ids:
        try:
            parsed_ids.append(uuid.UUID(str(sid)))
        except (ValueError, AttributeError, TypeError):
            raise ValidationError(
                'Dữ liệu không hợp lệ',
                fields={'song_ids': [f'"{sid}" không đúng định dạng UUID']},
            )

    # Không cho phép trùng lặp trong danh sách gửi lên
    if len(parsed_ids) != len(set(parsed_ids)):
        raise ValidationError(
            'Dữ liệu không hợp lệ',
            fields={'song_ids': ['song_ids chứa giá trị trùng lặp']},
        )

    return {'song_ids': parsed_ids}


def validate_cover_image(files: dict) -> None:
    """
    Validate file ảnh bìa playlist.

    Raises:
        ValidationError: nếu file không hợp lệ
    """
    if 'cover_image' not in files:
        raise ValidationError(
            'Dữ liệu không hợp lệ',
            fields={'cover_image': ['File ảnh là bắt buộc']},
        )

    cover = files['cover_image']
    errors = {}
    if cover.content_type not in ALLOWED_IMAGE_TYPES:
        errors['cover_image'] = ['Chỉ chấp nhận JPG, PNG, WEBP']
    elif cover.size > MAX_IMAGE_SIZE:
        errors['cover_image'] = ['File tối đa 5 MB']

    if errors:
        raise ValidationError('File không hợp lệ', fields=errors)


def validate_list_playlists_params(params: dict) -> dict:
    """Validate và làm sạch query params khi list playlist."""
    try:
        page = max(1, int(params.get('page', 1)))
    except (ValueError, TypeError):
        page = 1

    try:
        page_size = min(100, max(1, int(params.get('page_size', 20))))
    except (ValueError, TypeError):
        page_size = 20

    return {
        'q':         params.get('q', '').strip(),
        'page':      page,
        'page_size': page_size,
    }
```

---

## `playlists/selectors.py`

```python
"""
playlists/selectors.py
========================
Tầng Đọc cho app playlists — mọi truy vấn DB chỉ được viết ở đây.

Quy ước (§1.2):
  - CHỈ đọc dữ liệu, KHÔNG ghi
  - Prefix hàm: get_*, list_*, count_*, is_*, check_*
  - KHÔNG raise HTTP exception (raise custom exception nghiệp vụ nếu cần)
"""

import math
from django.db.models import Q

from playlists.models import Playlist, PlaylistSong
from playlists.exceptions import PlaylistNotFound, SongNotInPlaylist


def get_playlist_by_id(playlist_id) -> Playlist:
    """
    Lấy Playlist theo UUID — KHÔNG kiểm tra quyền xem.

    Dùng nội bộ trong services khi đã biết chắc cần thao tác bất kể quyền
    (ví dụ: owner đang sửa playlist của chính họ).

    Raises:
        PlaylistNotFound: nếu không tồn tại
    """
    try:
        return Playlist.objects.select_related('owner').get(id=playlist_id)
    except Playlist.DoesNotExist:
        raise PlaylistNotFound()


def get_playlist_detail(playlist_id, viewer=None) -> Playlist:
    """
    Lấy Playlist để trả về cho client — CÓ kiểm tra quyền xem.

    Business rules:
        - is_public=True  -> ai cũng xem được
        - is_public=False -> chỉ owner xem được, người khác nhận 404
                              (không để lộ rằng playlist này có tồn tại)

    Raises:
        PlaylistNotFound: nếu không tồn tại hoặc không có quyền xem
    """
    try:
        playlist = Playlist.objects.select_related('owner').get(id=playlist_id)
    except Playlist.DoesNotExist:
        raise PlaylistNotFound()

    if not playlist.is_public:
        viewer_id      = getattr(viewer, 'id', None)
        viewer_is_auth = bool(viewer_id and getattr(viewer, 'is_authenticated', False))
        if not viewer_is_auth or str(viewer_id) != str(playlist.owner_id):
            raise PlaylistNotFound()

    return playlist


def list_my_playlists(owner, filters: dict) -> dict:
    """
    Danh sách playlist của chính owner (gồm cả public + private), có phân trang.

    Args:
        owner:   User đang đăng nhập
        filters: dict từ validate_list_playlists_params()
    """
    qs = Playlist.objects.filter(owner=owner).select_related('owner')

    if filters.get('q'):
        qs = qs.filter(title__icontains=filters['q'])

    qs = qs.order_by('-created_at')

    page      = filters.get('page', 1)
    page_size = filters.get('page_size', 20)
    total     = qs.count()
    start     = (page - 1) * page_size
    end       = start + page_size

    items = [p.to_dict(viewer=owner) for p in qs[start:end]]

    return {
        'items': items,
        'pagination': {
            'page':        page,
            'page_size':   page_size,
            'total':       total,
            'total_pages': math.ceil(total / page_size) if total > 0 else 1,
        },
    }


def list_public_playlists(filters: dict, viewer=None) -> dict:
    """
    Danh sách playlist công khai (dùng cho khám phá / search), có phân trang.
    """
    qs = Playlist.objects.filter(is_public=True).select_related('owner')

    if filters.get('q'):
        qs = qs.filter(title__icontains=filters['q'])

    qs = qs.order_by('-created_at')

    page      = filters.get('page', 1)
    page_size = filters.get('page_size', 20)
    total     = qs.count()
    start     = (page - 1) * page_size
    end       = start + page_size

    items = [p.to_dict(viewer=viewer) for p in qs[start:end]]

    return {
        'items': items,
        'pagination': {
            'page':        page,
            'page_size':   page_size,
            'total':       total,
            'total_pages': math.ceil(total / page_size) if total > 0 else 1,
        },
    }


def list_playlist_songs(playlist_id, viewer=None, page=1, page_size=50) -> dict:
    """
    Danh sách bài hát trong playlist, sắp xếp theo order.

    Business rule: gọi sau khi đã pass quyền xem qua get_playlist_detail()
    ở tầng view — selector này không tự check lại quyền (tránh query trùng).
    """
    qs = (
        PlaylistSong.objects
        .filter(playlist_id=playlist_id)
        .select_related('song', 'song__artist')
        .order_by('order', 'added_at')
    )

    total = qs.count()
    start = (page - 1) * page_size
    items = [ps.to_dict() for ps in qs[start:start + page_size]]

    return {
        'items': items,
        'pagination': {
            'page':        page,
            'page_size':   page_size,
            'total':       total,
            'total_pages': math.ceil(total / page_size) if total > 0 else 1,
        },
    }


def get_playlist_song(playlist_id, song_id) -> PlaylistSong:
    """
    Lấy bản ghi PlaylistSong theo playlist + song.

    Raises:
        SongNotInPlaylist: nếu bài hát không có trong playlist
    """
    try:
        return PlaylistSong.objects.select_related('song').get(
            playlist_id=playlist_id, song_id=song_id
        )
    except PlaylistSong.DoesNotExist:
        raise SongNotInPlaylist()


def check_song_in_playlist(playlist_id, song_id) -> bool:
    """Kiểm tra bài hát đã có trong playlist hay chưa."""
    return PlaylistSong.objects.filter(playlist_id=playlist_id, song_id=song_id).exists()


def get_max_order(playlist_id) -> int:
    """Lấy order lớn nhất hiện tại trong playlist — dùng để thêm bài mới vào cuối."""
    last = PlaylistSong.objects.filter(playlist_id=playlist_id).order_by('-order').first()
    return last.order if last else 0


def list_playlist_song_ids(playlist_id) -> list:
    """Trả về list các song_id (str) hiện có trong playlist, theo order."""
    return list(
        PlaylistSong.objects
        .filter(playlist_id=playlist_id)
        .order_by('order')
        .values_list('song_id', flat=True)
    )
```

---

## `playlists/services.py`

```python
"""
playlists/services.py
=======================
Tầng Ghi cho app playlists — mọi logic Create/Update/Delete ở đây.

Quy ước (§1.2):
  - Xử lý toàn bộ business logic ghi dữ liệu
  - KHÔNG trả HTTP response
  - Có thể gọi selectors để đọc, nhưng selectors không gọi ngược lại services
  - Raise custom exception từ exceptions.py khi có lỗi nghiệp vụ
  - Tên hàm bắt đầu bằng động từ: create_, update_, delete_, add_, remove_, reorder_
"""

import logging

from django.db import transaction

from playlists.models import Playlist, PlaylistSong
from playlists.selectors import (
    get_max_order, check_song_in_playlist, get_playlist_song,
    list_playlist_song_ids,
)
from playlists.exceptions import (
    NotPlaylistOwner, SongAlreadyInPlaylist, InvalidReorderData,
)
from music.selectors import get_song_by_id

logger = logging.getLogger(__name__)


# ── Playlist CRUD ───────────────────────────────────────────────────────────────

def create_playlist(owner, data: dict) -> Playlist:
    """
    Tạo playlist mới.

    Args:
        owner: User tạo playlist (chủ sở hữu)
        data:  dict đã validate từ validators.validate_playlist_create()

    Returns:
        Playlist mới đã được lưu vào DB
    """
    playlist = Playlist.objects.create(
        owner       = owner,
        title       = data['title'],
        description = data.get('description', ''),
        is_public   = data.get('is_public', True),
    )
    logger.info('Playlist created: %s (owner=%s)', playlist.title, owner.username)
    return playlist


def update_playlist(playlist: Playlist, user, data: dict) -> Playlist:
    """
    Cập nhật thông tin playlist (title, description) — chỉ owner.

    Raises:
        NotPlaylistOwner: nếu user không phải owner
    """
    if str(playlist.owner_id) != str(user.id):
        raise NotPlaylistOwner()

    for field, value in data.items():
        setattr(playlist, field, value)

    playlist.save(update_fields=list(data.keys()) + ['updated_at'])
    logger.info('Playlist updated: %s', playlist.title)
    return playlist


def update_cover_image(playlist: Playlist, user, cover_file) -> Playlist:
    """
    Cập nhật ảnh bìa playlist — chỉ owner.

    File được upload thẳng lên Cloudinary qua DEFAULT_FILE_STORAGE.
    Path: covers/playlists/<uuid>.<ext>

    Raises:
        NotPlaylistOwner: nếu user không phải owner
    """
    if str(playlist.owner_id) != str(user.id):
        raise NotPlaylistOwner()

    # Xóa ảnh cũ trên Cloudinary nếu có, tránh file mồ côi
    if playlist.cover_image:
        try:
            playlist.cover_image.delete(save=False)
        except Exception as e:
            logger.warning('Failed to delete old cover for playlist %s: %s', playlist.id, e)

    playlist.cover_image = cover_file
    playlist.save(update_fields=['cover_image', 'updated_at'])
    logger.info('Playlist cover updated: %s', playlist.title)
    return playlist


def update_visibility(playlist: Playlist, user, is_public: bool) -> Playlist:
    """
    Đặt playlist công khai / riêng tư — chỉ owner.

    Raises:
        NotPlaylistOwner: nếu user không phải owner
    """
    if str(playlist.owner_id) != str(user.id):
        raise NotPlaylistOwner()

    playlist.is_public = is_public
    playlist.save(update_fields=['is_public', 'updated_at'])
    logger.info('Playlist visibility updated: %s -> is_public=%s', playlist.title, is_public)
    return playlist


def delete_playlist(playlist: Playlist, user) -> None:
    """
    Xóa playlist — chỉ owner. Cascade sẽ tự xóa toàn bộ PlaylistSong liên quan.

    Raises:
        NotPlaylistOwner: nếu user không phải owner
    """
    if str(playlist.owner_id) != str(user.id):
        raise NotPlaylistOwner()

    title = playlist.title
    playlist.delete()
    logger.info('Playlist deleted: %s', title)


# ── Quản lý bài hát trong Playlist ──────────────────────────────────────────────

def add_song_to_playlist(playlist: Playlist, user, song_id) -> PlaylistSong:
    """
    Thêm bài hát vào playlist — chỉ owner.

    Bài hát mới luôn được thêm vào CUỐI danh sách (order = max_order + 1).

    Raises:
        NotPlaylistOwner:      nếu user không phải owner
        SongNotFound:          nếu song_id không tồn tại (raise từ music.selectors)
        SongAlreadyInPlaylist: nếu bài hát đã có trong playlist
    """
    if str(playlist.owner_id) != str(user.id):
        raise NotPlaylistOwner()

    # Xác nhận bài hát tồn tại — get_song_by_id tự raise SongNotFound nếu không có
    song = get_song_by_id(song_id)

    if check_song_in_playlist(playlist.id, song.id):
        raise SongAlreadyInPlaylist()

    next_order = get_max_order(playlist.id) + 1

    playlist_song = PlaylistSong.objects.create(
        playlist = playlist,
        song     = song,
        order    = next_order,
    )
    logger.info('Song added to playlist: %s -> %s (#%s)', song.title, playlist.title, next_order)
    return playlist_song


def remove_song_from_playlist(playlist: Playlist, user, song_id) -> None:
    """
    Xóa bài hát khỏi playlist — chỉ owner.

    Raises:
        NotPlaylistOwner:  nếu user không phải owner
        SongNotInPlaylist: nếu bài hát không có trong playlist
    """
    if str(playlist.owner_id) != str(user.id):
        raise NotPlaylistOwner()

    playlist_song = get_playlist_song(playlist.id, song_id)
    playlist_song.delete()
    logger.info('Song removed from playlist: %s', playlist.title)


@transaction.atomic
def reorder_playlist_songs(playlist: Playlist, user, song_ids: list) -> None:
    """
    Sắp xếp lại thứ tự bài hát trong playlist — chỉ owner.

    Business rule quan trọng:
        song_ids gửi lên PHẢI khớp chính xác (cùng tập hợp) với các bài hát
        hiện có trong playlist — không thiếu, không dư, không có ID lạ.
        Nếu không khớp -> InvalidReorderData (Fix tránh dữ liệu rác/đồng bộ sai).

    Dùng @transaction.atomic để đảm bảo toàn bộ update order là 1 đơn vị —
    nếu có lỗi giữa chừng, rollback toàn bộ, không để playlist ở trạng thái
    thứ tự nửa cũ nửa mới.

    Raises:
        NotPlaylistOwner:   nếu user không phải owner
        InvalidReorderData: nếu song_ids không khớp với playlist hiện tại
    """
    if str(playlist.owner_id) != str(user.id):
        raise NotPlaylistOwner()

    current_ids = set(str(sid) for sid in list_playlist_song_ids(playlist.id))
    incoming_ids = set(str(sid) for sid in song_ids)

    if current_ids != incoming_ids:
        raise InvalidReorderData(
            'Danh sách song_ids phải khớp chính xác với các bài hát hiện có trong playlist'
        )

    # Cập nhật order theo đúng vị trí trong danh sách gửi lên
    playlist_songs = {
        str(ps.song_id): ps
        for ps in PlaylistSong.objects.filter(playlist=playlist)
    }
    for new_order, sid in enumerate(song_ids, start=1):
        ps = playlist_songs[str(sid)]
        ps.order = new_order

    PlaylistSong.objects.bulk_update(playlist_songs.values(), ['order'])
    logger.info('Playlist reordered: %s (%d songs)', playlist.title, len(song_ids))
```

---

## `playlists/views.py`

```python
"""
playlists/views.py
====================
Tầng HTTP cho app playlists.

Quy ước (§1.2):
  - views.py KHÔNG import Playlist, PlaylistSong... để query trực tiếp
  - Mọi query qua selectors.py, mọi ghi qua services.py
  - Exception từ services/selectors được map sang HTTP status qua handle_exception()
"""

import json
import logging

from django.http import JsonResponse
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect

from accounts.decorators import require_auth
from accounts.exceptions import ValidationError, PermissionDenied, NotFound, AlreadyExists
from music.exceptions import SongNotFound

from playlists.exceptions import (
    PlaylistNotFound, NotPlaylistOwner, SongAlreadyInPlaylist,
    SongNotInPlaylist, InvalidReorderData,
)
from playlists.validators import (
    validate_playlist_create, validate_playlist_update, validate_visibility,
    validate_add_song, validate_reorder, validate_cover_image,
    validate_list_playlists_params,
)
from playlists.selectors import (
    list_my_playlists, get_playlist_by_id, get_playlist_detail, list_playlist_songs,
)
from playlists.services import (
    create_playlist, update_playlist, update_cover_image, update_visibility,
    delete_playlist, add_song_to_playlist, remove_song_from_playlist,
    reorder_playlist_songs,
)

logger = logging.getLogger(__name__)


def parse_json_body(request) -> dict:
    """Parse JSON body an toàn — trả {} nếu body rỗng hoặc lỗi parse."""
    try:
        return json.loads(request.body or '{}')
    except (json.JSONDecodeError, ValueError):
        return {}


def handle_exception(e: Exception) -> JsonResponse:
    """
    Map exception nghiệp vụ sang HTTP response chuẩn.
    Dùng chung cho mọi view trong app này.
    """
    if isinstance(e, ValidationError):
        return JsonResponse(
            {'success': False, 'error': {'code': 'VALIDATION_ERROR',
                                          'message': e.message, 'fields': e.fields}},
            status=400,
        )
    if isinstance(e, InvalidReorderData):
        return JsonResponse(
            {'success': False, 'error': {'code': e.error_code, 'message': e.message}},
            status=400,
        )
    if isinstance(e, (NotPlaylistOwner, PermissionDenied)):
        return JsonResponse(
            {'success': False, 'error': {'code': e.error_code, 'message': e.message}},
            status=403,
        )
    if isinstance(e, (PlaylistNotFound, SongNotFound, SongNotInPlaylist, NotFound)):
        return JsonResponse(
            {'success': False, 'error': {'code': 'NOT_FOUND', 'message': e.message}},
            status=404,
        )
    if isinstance(e, (SongAlreadyInPlaylist, AlreadyExists)):
        return JsonResponse(
            {'success': False, 'error': {'code': 'ALREADY_EXISTS', 'message': e.message}},
            status=409,
        )

    logger.exception('Unhandled exception in playlists views: %s', e)
    return JsonResponse(
        {'success': False, 'error': {'code': 'SERVER_ERROR', 'message': 'Lỗi server'}},
        status=500,
    )


# ── Playlist Views ───────────────────────────────────────────────────────────────

class PlaylistListView(View):
    """
    GET  /api/v1/playlists/  — Danh sách playlist CỦA TÔI (Auth)
    POST /api/v1/playlists/  — Tạo playlist mới (Auth+CSRF)
    """

    @method_decorator(require_auth)
    def get(self, request):
        try:
            filters = validate_list_playlists_params(request.GET)
            result  = list_my_playlists(request.user, filters)
            return JsonResponse({'success': True, 'data': result})
        except Exception as e:
            return handle_exception(e)

    @method_decorator(csrf_protect)
    @method_decorator(require_auth)
    def post(self, request):
        try:
            data      = parse_json_body(request)
            validated = validate_playlist_create(data)
            playlist  = create_playlist(request.user, validated)
            return JsonResponse(
                {'success': True, 'data': playlist.to_dict(viewer=request.user)},
                status=201,
            )
        except Exception as e:
            return handle_exception(e)


class PlaylistDetailView(View):
    """
    GET    /api/v1/playlists/<id>/  — Chi tiết playlist (Public nếu is_public, Owner nếu private)
    PATCH  /api/v1/playlists/<id>/  — Cập nhật title/description (Auth+Owner+CSRF)
    DELETE /api/v1/playlists/<id>/  — Xóa playlist (Auth+Owner+CSRF)
    """

    def get(self, request, playlist_id):
        try:
            playlist = get_playlist_detail(playlist_id, viewer=request.user)
            return JsonResponse({'success': True, 'data': playlist.to_dict(viewer=request.user)})
        except Exception as e:
            return handle_exception(e)

    @method_decorator(csrf_protect)
    @method_decorator(require_auth)
    def patch(self, request, playlist_id):
        try:
            playlist  = get_playlist_by_id(playlist_id)
            data      = parse_json_body(request)
            validated = validate_playlist_update(data)
            if not validated:
                return JsonResponse(
                    {'success': False, 'error': {'code': 'VALIDATION_ERROR',
                                                  'message': 'Không có dữ liệu để cập nhật'}},
                    status=400,
                )
            playlist = update_playlist(playlist, request.user, validated)
            return JsonResponse({'success': True, 'data': playlist.to_dict(viewer=request.user)})
        except Exception as e:
            return handle_exception(e)

    @method_decorator(csrf_protect)
    @method_decorator(require_auth)
    def delete(self, request, playlist_id):
        try:
            playlist = get_playlist_by_id(playlist_id)
            delete_playlist(playlist, request.user)
            return JsonResponse({'success': True}, status=204)
        except Exception as e:
            return handle_exception(e)


class PlaylistCoverUploadView(View):
    """POST /api/v1/playlists/<id>/cover/ — Upload ảnh bìa (Auth+Owner+CSRF)"""

    @method_decorator(csrf_protect)
    @method_decorator(require_auth)
    def post(self, request, playlist_id):
        try:
            validate_cover_image(request.FILES)
            playlist = get_playlist_by_id(playlist_id)
            playlist = update_cover_image(playlist, request.user, request.FILES['cover_image'])
            return JsonResponse({
                'success': True,
                'data': {'cover_image': playlist.cover_image.url if playlist.cover_image else None},
            })
        except Exception as e:
            return handle_exception(e)


class PlaylistVisibilityView(View):
    """PATCH /api/v1/playlists/<id>/visibility/ — Đặt public/private (Auth+Owner+CSRF)"""

    @method_decorator(csrf_protect)
    @method_decorator(require_auth)
    def patch(self, request, playlist_id):
        try:
            data      = parse_json_body(request)
            validated = validate_visibility(data)
            playlist  = get_playlist_by_id(playlist_id)
            playlist  = update_visibility(playlist, request.user, validated['is_public'])
            return JsonResponse({'success': True, 'data': {'is_public': playlist.is_public}})
        except Exception as e:
            return handle_exception(e)


# ── Playlist Songs Views ─────────────────────────────────────────────────────────

class PlaylistSongListView(View):
    """
    GET  /api/v1/playlists/<id>/songs/  — Danh sách bài hát (Public nếu is_public, Owner nếu private)
    POST /api/v1/playlists/<id>/songs/  — Thêm bài hát (Auth+Owner+CSRF)
    """

    def get(self, request, playlist_id):
        try:
            # get_playlist_detail tự raise PlaylistNotFound nếu không có quyền xem
            get_playlist_detail(playlist_id, viewer=request.user)

            page      = int(request.GET.get('page', 1))
            page_size = min(100, int(request.GET.get('page_size', 50)))
            result    = list_playlist_songs(playlist_id, viewer=request.user,
                                             page=page, page_size=page_size)
            return JsonResponse({'success': True, 'data': result})
        except Exception as e:
            return handle_exception(e)

    @method_decorator(csrf_protect)
    @method_decorator(require_auth)
    def post(self, request, playlist_id):
        try:
            data            = parse_json_body(request)
            validated       = validate_add_song(data)
            playlist        = get_playlist_by_id(playlist_id)
            playlist_song   = add_song_to_playlist(playlist, request.user, validated['song_id'])
            return JsonResponse(
                {'success': True, 'data': playlist_song.to_dict()},
                status=201,
            )
        except Exception as e:
            return handle_exception(e)


class PlaylistSongDetailView(View):
    """DELETE /api/v1/playlists/<id>/songs/<song_id>/ — Xóa bài hát (Auth+Owner+CSRF)"""

    @method_decorator(csrf_protect)
    @method_decorator(require_auth)
    def delete(self, request, playlist_id, song_id):
        try:
            playlist = get_playlist_by_id(playlist_id)
            remove_song_from_playlist(playlist, request.user, song_id)
            return JsonResponse({'success': True}, status=204)
        except Exception as e:
            return handle_exception(e)


class PlaylistSongReorderView(View):
    """PATCH /api/v1/playlists/<id>/songs/reorder/ — Sắp xếp lại thứ tự (Auth+Owner+CSRF)"""

    @method_decorator(csrf_protect)
    @method_decorator(require_auth)
    def patch(self, request, playlist_id):
        try:
            data      = parse_json_body(request)
            validated = validate_reorder(data)
            playlist  = get_playlist_by_id(playlist_id)
            reorder_playlist_songs(playlist, request.user, validated['song_ids'])
            return JsonResponse({'success': True, 'message': 'Đã cập nhật thứ tự'})
        except Exception as e:
            return handle_exception(e)
```

---

## `playlists/urls.py`

```python
"""
playlists/urls.py
===================
URLs cho app playlists — prefix: /api/v1/playlists/
"""

from django.urls import path
from playlists.views import (
    PlaylistListView, PlaylistDetailView, PlaylistCoverUploadView,
    PlaylistVisibilityView,
    PlaylistSongListView, PlaylistSongDetailView, PlaylistSongReorderView,
)

urlpatterns = [
    # Playlist CRUD
    path('',                                   PlaylistListView.as_view(),          name='playlist-list'),
    path('<uuid:playlist_id>/',                PlaylistDetailView.as_view(),        name='playlist-detail'),
    path('<uuid:playlist_id>/cover/',          PlaylistCoverUploadView.as_view(),   name='playlist-cover'),
    path('<uuid:playlist_id>/visibility/',     PlaylistVisibilityView.as_view(),    name='playlist-visibility'),

    # Playlist Songs
    path('<uuid:playlist_id>/songs/',                  PlaylistSongListView.as_view(),    name='playlist-song-list'),
    path('<uuid:playlist_id>/songs/reorder/',          PlaylistSongReorderView.as_view(), name='playlist-song-reorder'),
    path('<uuid:playlist_id>/songs/<uuid:song_id>/',   PlaylistSongDetailView.as_view(),  name='playlist-song-detail'),
]
```

---

## `playlists/admin.py`

```python
"""playlists/admin.py"""
from django.contrib import admin
from playlists.models import Playlist, PlaylistSong


class PlaylistSongInline(admin.TabularInline):
    model = PlaylistSong
    extra = 0
    fields = ('song', 'order', 'added_at')
    readonly_fields = ('added_at',)


@admin.register(Playlist)
class PlaylistAdmin(admin.ModelAdmin):
    list_display  = ('title', 'owner', 'is_public', 'created_at')
    list_filter   = ('is_public',)
    search_fields = ('title', 'owner__username')
    readonly_fields = ('created_at', 'updated_at')
    inlines = [PlaylistSongInline]


@admin.register(PlaylistSong)
class PlaylistSongAdmin(admin.ModelAdmin):
    list_display  = ('playlist', 'song', 'order', 'added_at')
    search_fields = ('playlist__title', 'song__title')
```

---

## `playlists/tests.py`

```python
"""
playlists/tests.py
=====================
Unit tests cho app playlists - Tuan 3.

Chay tests:
    python manage.py test playlists --verbosity=2
    python manage.py test accounts music playlists --verbosity=2   (toan bo)

Coverage:
  - Models:      Playlist.to_dict(), PlaylistSong.to_dict()
  - Validators:  playlist create/update, visibility, add_song, reorder, cover image
  - Selectors:   get_playlist_detail (public/private), list_my_playlists,
                 list_playlist_songs, check_song_in_playlist
  - Services:    create/update/delete playlist, add/remove song, reorder (atomic)
  - Views:       toan bo endpoints - HTTP status, phan quyen owner
  - Edge cases:  private playlist 404 cho nguoi khac, reorder sai du lieu,
                 them bai trung, xoa bai khong ton tai
"""

import json
import uuid

from django.test import TestCase, Client
from django.core.files.uploadedfile import SimpleUploadedFile

from accounts.models import User
from music.models import Genre, Song
from playlists.models import Playlist, PlaylistSong
from playlists.validators import (
    validate_playlist_create, validate_playlist_update, validate_visibility,
    validate_add_song, validate_reorder, validate_list_playlists_params,
)
from playlists.selectors import (
    get_playlist_by_id, get_playlist_detail, list_my_playlists,
    list_public_playlists, list_playlist_songs, get_playlist_song,
    check_song_in_playlist, get_max_order, list_playlist_song_ids,
)
from playlists.services import (
    create_playlist, update_playlist, update_visibility, delete_playlist,
    add_song_to_playlist, remove_song_from_playlist, reorder_playlist_songs,
)
from playlists.exceptions import (
    PlaylistNotFound, NotPlaylistOwner, SongAlreadyInPlaylist,
    SongNotInPlaylist, InvalidReorderData,
)
from music.exceptions import SongNotFound
from accounts.exceptions import ValidationError


# ── Helpers ───────────────────────────────────────────────────────────────────

def make_user(username, email, password='Test1234', role='user', **kwargs):
    return User.objects.create_user(
        username=username, email=email, password=password, role=role, **kwargs
    )


def make_audio_file(name=None):
    if name is None:
        name = f'{uuid.uuid4().hex}.mp3'
    return SimpleUploadedFile(name, b'\x00' * 1024, content_type='audio/mpeg')


def make_image_file(name='cover.jpg', content_type='image/jpeg', size_bytes=512):
    return SimpleUploadedFile(name, b'\x00' * size_bytes, content_type=content_type)


def make_genre(name='Pop'):
    return Genre.objects.create(name=name, description=f'{name} description')


def make_song(artist, genre=None, title='Test Song', status=Song.STATUS_PUBLISHED, **kwargs):
    if genre is None:
        genre = make_genre(f'Genre-{uuid.uuid4().hex[:6]}')
    defaults = {
        'title':      title,
        'artist':     artist,
        'genre':      genre,
        'duration':   200,
        'status':     status,
        'audio_file': make_audio_file(),
    }
    defaults.update(kwargs)
    return Song.objects.create(**defaults)


def make_playlist(owner, title='My Playlist', is_public=True, **kwargs):
    return Playlist.objects.create(owner=owner, title=title, is_public=is_public, **kwargs)


# ═══════════════════════════════════════════════════════════════════════════════
# MODEL TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class PlaylistModelTest(TestCase):

    def setUp(self):
        self.owner = make_user('plowner', 'plowner@test.com')

    def test_playlist_creation(self):
        playlist = make_playlist(self.owner, title='Chill Vibes')
        self.assertEqual(playlist.title, 'Chill Vibes')
        self.assertTrue(playlist.is_public)

    def test_default_is_public_true(self):
        playlist = Playlist.objects.create(owner=self.owner, title='Default Test')
        self.assertTrue(playlist.is_public)

    def test_to_dict_basic_fields(self):
        playlist = make_playlist(self.owner, title='Dict Test')
        d = playlist.to_dict()
        self.assertEqual(d['title'], 'Dict Test')
        self.assertEqual(d['owner']['username'], self.owner.username)
        self.assertEqual(d['song_count'], 0)

    def test_to_dict_is_owner_true_for_owner(self):
        playlist = make_playlist(self.owner)
        d = playlist.to_dict(viewer=self.owner)
        self.assertTrue(d['is_owner'])

    def test_to_dict_is_owner_false_for_others(self):
        playlist = make_playlist(self.owner)
        other = make_user('otherviewer', 'otherviewer@test.com')
        d = playlist.to_dict(viewer=other)
        self.assertFalse(d['is_owner'])

    def test_to_dict_is_owner_false_for_anonymous(self):
        from django.contrib.auth.models import AnonymousUser
        playlist = make_playlist(self.owner)
        d = playlist.to_dict(viewer=AnonymousUser())
        self.assertFalse(d['is_owner'])

    def test_to_dict_song_count_accurate(self):
        artist = make_user('plmodelartist', 'plmodelartist@test.com', role='artist')
        playlist = make_playlist(self.owner)
        song1 = make_song(artist, title='Song 1')
        song2 = make_song(artist, title='Song 2')
        PlaylistSong.objects.create(playlist=playlist, song=song1, order=1)
        PlaylistSong.objects.create(playlist=playlist, song=song2, order=2)
        d = playlist.to_dict()
        self.assertEqual(d['song_count'], 2)


class PlaylistSongModelTest(TestCase):

    def setUp(self):
        self.owner  = make_user('psowner', 'psowner@test.com')
        self.artist = make_user('psartist', 'psartist@test.com', role='artist')
        self.playlist = make_playlist(self.owner)
        self.song   = make_song(self.artist, title='PS Song')

    def test_playlist_song_creation(self):
        ps = PlaylistSong.objects.create(playlist=self.playlist, song=self.song, order=1)
        self.assertEqual(ps.order, 1)

    def test_to_dict_contains_song_info(self):
        ps = PlaylistSong.objects.create(playlist=self.playlist, song=self.song, order=1)
        d = ps.to_dict()
        self.assertEqual(d['song']['title'], 'PS Song')
        self.assertEqual(d['order'], 1)

    def test_unique_together_prevents_duplicate(self):
        PlaylistSong.objects.create(playlist=self.playlist, song=self.song, order=1)
        with self.assertRaises(Exception):
            PlaylistSong.objects.create(playlist=self.playlist, song=self.song, order=2)


# ═══════════════════════════════════════════════════════════════════════════════
# VALIDATOR TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class ValidatePlaylistCreateTest(TestCase):

    def test_valid_data(self):
        result = validate_playlist_create({'title': 'My Playlist', 'description': 'desc', 'is_public': True})
        self.assertEqual(result['title'], 'My Playlist')
        self.assertTrue(result['is_public'])

    def test_missing_title(self):
        with self.assertRaises(ValidationError) as ctx:
            validate_playlist_create({'description': 'desc'})
        self.assertIn('title', ctx.exception.fields)

    def test_title_too_long(self):
        with self.assertRaises(ValidationError) as ctx:
            validate_playlist_create({'title': 'x' * 201})
        self.assertIn('title', ctx.exception.fields)

    def test_description_too_long(self):
        with self.assertRaises(ValidationError) as ctx:
            validate_playlist_create({'title': 'OK', 'description': 'x' * 1001})
        self.assertIn('description', ctx.exception.fields)

    def test_default_is_public_true_when_missing(self):
        result = validate_playlist_create({'title': 'No visibility field'})
        self.assertTrue(result['is_public'])

    def test_is_public_string_true(self):
        result = validate_playlist_create({'title': 'X', 'is_public': 'true'})
        self.assertTrue(result['is_public'])

    def test_is_public_false(self):
        result = validate_playlist_create({'title': 'Private', 'is_public': False})
        self.assertFalse(result['is_public'])

    def test_title_xss_sanitized(self):
        result = validate_playlist_create({'title': '<script>alert(1)</script>My List'})
        self.assertEqual(result['title'], 'My List')

    def test_description_xss_sanitized(self):
        result = validate_playlist_create({'title': 'X', 'description': '<b>bold</b>desc'})
        self.assertEqual(result['description'], 'bolddesc')


class ValidatePlaylistUpdateTest(TestCase):

    def test_partial_update_title_only(self):
        result = validate_playlist_update({'title': 'New Title'})
        self.assertEqual(result, {'title': 'New Title'})

    def test_empty_title_raises(self):
        with self.assertRaises(ValidationError):
            validate_playlist_update({'title': ''})

    def test_no_fields_returns_empty_dict(self):
        result = validate_playlist_update({})
        self.assertEqual(result, {})

    def test_description_sanitized(self):
        result = validate_playlist_update({'description': '<i>x</i>desc'})
        self.assertEqual(result['description'], 'xdesc')


class ValidateVisibilityTest(TestCase):

    def test_valid_true(self):
        result = validate_visibility({'is_public': True})
        self.assertTrue(result['is_public'])

    def test_valid_false(self):
        result = validate_visibility({'is_public': False})
        self.assertFalse(result['is_public'])

    def test_missing_raises(self):
        with self.assertRaises(ValidationError):
            validate_visibility({})

    def test_non_bool_raises(self):
        with self.assertRaises(ValidationError):
            validate_visibility({'is_public': 'yes'})


class ValidateAddSongTest(TestCase):

    def test_valid_song_id(self):
        sid = str(uuid.uuid4())
        result = validate_add_song({'song_id': sid})
        self.assertEqual(str(result['song_id']), sid)

    def test_missing_song_id_raises(self):
        with self.assertRaises(ValidationError) as ctx:
            validate_add_song({})
        self.assertIn('song_id', ctx.exception.fields)

    def test_invalid_uuid_format_raises(self):
        with self.assertRaises(ValidationError) as ctx:
            validate_add_song({'song_id': 'not-a-uuid'})
        self.assertIn('song_id', ctx.exception.fields)


class ValidateReorderTest(TestCase):

    def test_valid_song_ids_list(self):
        ids = [str(uuid.uuid4()), str(uuid.uuid4())]
        result = validate_reorder({'song_ids': ids})
        self.assertEqual(len(result['song_ids']), 2)

    def test_missing_song_ids_raises(self):
        with self.assertRaises(ValidationError):
            validate_reorder({})

    def test_not_a_list_raises(self):
        with self.assertRaises(ValidationError):
            validate_reorder({'song_ids': 'not-a-list'})

    def test_empty_list_raises(self):
        with self.assertRaises(ValidationError):
            validate_reorder({'song_ids': []})

    def test_invalid_uuid_in_list_raises(self):
        with self.assertRaises(ValidationError):
            validate_reorder({'song_ids': [str(uuid.uuid4()), 'bad-uuid']})

    def test_duplicate_ids_raises(self):
        sid = str(uuid.uuid4())
        with self.assertRaises(ValidationError):
            validate_reorder({'song_ids': [sid, sid]})


class ValidateListPlaylistsParamsTest(TestCase):

    def test_defaults(self):
        result = validate_list_playlists_params({})
        self.assertEqual(result['page'], 1)
        self.assertEqual(result['page_size'], 20)

    def test_page_size_capped_at_100(self):
        result = validate_list_playlists_params({'page_size': '500'})
        self.assertEqual(result['page_size'], 100)

    def test_negative_page_corrected(self):
        result = validate_list_playlists_params({'page': '-3'})
        self.assertEqual(result['page'], 1)


# ═══════════════════════════════════════════════════════════════════════════════
# SELECTOR TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class PlaylistSelectorTest(TestCase):

    def setUp(self):
        self.owner  = make_user('selowner', 'selowner@test.com')
        self.viewer = make_user('selviewer', 'selviewer@test.com')
        self.artist = make_user('selartist', 'selartist@test.com', role='artist')

    def test_get_playlist_by_id_found(self):
        playlist = make_playlist(self.owner)
        result = get_playlist_by_id(playlist.id)
        self.assertEqual(result.id, playlist.id)

    def test_get_playlist_by_id_not_found(self):
        with self.assertRaises(PlaylistNotFound):
            get_playlist_by_id(uuid.uuid4())

    def test_get_playlist_detail_public_visible_to_anyone(self):
        from django.contrib.auth.models import AnonymousUser
        playlist = make_playlist(self.owner, is_public=True)
        result = get_playlist_detail(playlist.id, viewer=AnonymousUser())
        self.assertEqual(result.id, playlist.id)

    def test_get_playlist_detail_private_visible_to_owner(self):
        playlist = make_playlist(self.owner, is_public=False)
        result = get_playlist_detail(playlist.id, viewer=self.owner)
        self.assertEqual(result.id, playlist.id)

    def test_get_playlist_detail_private_hidden_from_others(self):
        playlist = make_playlist(self.owner, is_public=False)
        with self.assertRaises(PlaylistNotFound):
            get_playlist_detail(playlist.id, viewer=self.viewer)

    def test_get_playlist_detail_private_hidden_from_anonymous(self):
        from django.contrib.auth.models import AnonymousUser
        playlist = make_playlist(self.owner, is_public=False)
        with self.assertRaises(PlaylistNotFound):
            get_playlist_detail(playlist.id, viewer=AnonymousUser())

    def test_list_my_playlists_includes_private(self):
        make_playlist(self.owner, title='Public One', is_public=True)
        make_playlist(self.owner, title='Private One', is_public=False)
        result = list_my_playlists(self.owner, {'page': 1, 'page_size': 20, 'q': ''})
        titles = [p['title'] for p in result['items']]
        self.assertIn('Public One', titles)
        self.assertIn('Private One', titles)

    def test_list_my_playlists_excludes_other_users(self):
        make_playlist(self.owner, title='Mine')
        make_playlist(self.viewer, title='NotMine')
        result = list_my_playlists(self.owner, {'page': 1, 'page_size': 20, 'q': ''})
        titles = [p['title'] for p in result['items']]
        self.assertIn('Mine', titles)
        self.assertNotIn('NotMine', titles)

    def test_list_my_playlists_filter_by_query(self):
        make_playlist(self.owner, title='Chill Vibes')
        make_playlist(self.owner, title='Workout Mix')
        result = list_my_playlists(self.owner, {'page': 1, 'page_size': 20, 'q': 'chill'})
        self.assertEqual(len(result['items']), 1)

    def test_list_my_playlists_pagination(self):
        for i in range(5):
            make_playlist(self.owner, title=f'Playlist {i}')
        result = list_my_playlists(self.owner, {'page': 1, 'page_size': 2, 'q': ''})
        self.assertEqual(len(result['items']), 2)
        self.assertEqual(result['pagination']['total'], 5)
        self.assertEqual(result['pagination']['total_pages'], 3)

    def test_list_public_playlists_excludes_private(self):
        make_playlist(self.owner, title='Pub', is_public=True)
        make_playlist(self.owner, title='Priv', is_public=False)
        result = list_public_playlists({'page': 1, 'page_size': 20, 'q': ''})
        titles = [p['title'] for p in result['items']]
        self.assertIn('Pub', titles)
        self.assertNotIn('Priv', titles)

    def test_list_playlist_songs_ordered(self):
        playlist = make_playlist(self.owner)
        s1 = make_song(self.artist, title='First')
        s2 = make_song(self.artist, title='Second')
        PlaylistSong.objects.create(playlist=playlist, song=s2, order=2)
        PlaylistSong.objects.create(playlist=playlist, song=s1, order=1)
        result = list_playlist_songs(playlist.id)
        titles = [item['song']['title'] for item in result['items']]
        self.assertEqual(titles, ['First', 'Second'])

    def test_get_playlist_song_found(self):
        playlist = make_playlist(self.owner)
        song = make_song(self.artist)
        PlaylistSong.objects.create(playlist=playlist, song=song, order=1)
        result = get_playlist_song(playlist.id, song.id)
        self.assertEqual(result.song_id, song.id)

    def test_get_playlist_song_not_found(self):
        playlist = make_playlist(self.owner)
        with self.assertRaises(SongNotInPlaylist):
            get_playlist_song(playlist.id, uuid.uuid4())

    def test_check_song_in_playlist_true(self):
        playlist = make_playlist(self.owner)
        song = make_song(self.artist)
        PlaylistSong.objects.create(playlist=playlist, song=song, order=1)
        self.assertTrue(check_song_in_playlist(playlist.id, song.id))

    def test_check_song_in_playlist_false(self):
        playlist = make_playlist(self.owner)
        song = make_song(self.artist)
        self.assertFalse(check_song_in_playlist(playlist.id, song.id))

    def test_get_max_order_empty_playlist(self):
        playlist = make_playlist(self.owner)
        self.assertEqual(get_max_order(playlist.id), 0)

    def test_get_max_order_with_songs(self):
        playlist = make_playlist(self.owner)
        song1 = make_song(self.artist, title='S1')
        song2 = make_song(self.artist, title='S2')
        PlaylistSong.objects.create(playlist=playlist, song=song1, order=3)
        PlaylistSong.objects.create(playlist=playlist, song=song2, order=7)
        self.assertEqual(get_max_order(playlist.id), 7)

    def test_list_playlist_song_ids(self):
        playlist = make_playlist(self.owner)
        song1 = make_song(self.artist, title='S1')
        song2 = make_song(self.artist, title='S2')
        PlaylistSong.objects.create(playlist=playlist, song=song1, order=1)
        PlaylistSong.objects.create(playlist=playlist, song=song2, order=2)
        ids = list_playlist_song_ids(playlist.id)
        self.assertEqual(set(ids), {song1.id, song2.id})


# ═══════════════════════════════════════════════════════════════════════════════
# SERVICE TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class PlaylistServiceTest(TestCase):

    def setUp(self):
        self.owner = make_user('svcowner', 'svcowner@test.com')
        self.other = make_user('svcother', 'svcother@test.com')

    def test_create_playlist_success(self):
        playlist = create_playlist(self.owner, {'title': 'New List', 'description': '', 'is_public': True})
        self.assertEqual(playlist.title, 'New List')
        self.assertEqual(playlist.owner, self.owner)

    def test_update_playlist_by_owner(self):
        playlist = make_playlist(self.owner, title='Old')
        updated = update_playlist(playlist, self.owner, {'title': 'New'})
        self.assertEqual(updated.title, 'New')

    def test_update_playlist_not_owner_raises(self):
        playlist = make_playlist(self.owner)
        with self.assertRaises(NotPlaylistOwner):
            update_playlist(playlist, self.other, {'title': 'Hacked'})

    def test_update_visibility_by_owner(self):
        playlist = make_playlist(self.owner, is_public=True)
        updated = update_visibility(playlist, self.owner, False)
        self.assertFalse(updated.is_public)

    def test_update_visibility_not_owner_raises(self):
        playlist = make_playlist(self.owner)
        with self.assertRaises(NotPlaylistOwner):
            update_visibility(playlist, self.other, False)

    def test_delete_playlist_by_owner(self):
        playlist = make_playlist(self.owner)
        delete_playlist(playlist, self.owner)
        self.assertFalse(Playlist.objects.filter(id=playlist.id).exists())

    def test_delete_playlist_not_owner_raises(self):
        playlist = make_playlist(self.owner)
        with self.assertRaises(NotPlaylistOwner):
            delete_playlist(playlist, self.other)

    def test_delete_playlist_cascades_playlist_songs(self):
        artist = make_user('cascadeartist', 'cascadeartist@test.com', role='artist')
        playlist = make_playlist(self.owner)
        song = make_song(artist)
        ps = PlaylistSong.objects.create(playlist=playlist, song=song, order=1)
        delete_playlist(playlist, self.owner)
        self.assertFalse(PlaylistSong.objects.filter(id=ps.id).exists())


class AddRemoveSongServiceTest(TestCase):

    def setUp(self):
        self.owner  = make_user('arowner', 'arowner@test.com')
        self.other  = make_user('arother', 'arother@test.com')
        self.artist = make_user('arartist', 'arartist@test.com', role='artist')
        self.playlist = make_playlist(self.owner)
        self.song   = make_song(self.artist, title='Addable Song')

    def test_add_song_success(self):
        ps = add_song_to_playlist(self.playlist, self.owner, self.song.id)
        self.assertEqual(ps.song_id, self.song.id)
        self.assertEqual(ps.order, 1)

    def test_add_song_not_owner_raises(self):
        with self.assertRaises(NotPlaylistOwner):
            add_song_to_playlist(self.playlist, self.other, self.song.id)

    def test_add_song_nonexistent_raises_song_not_found(self):
        with self.assertRaises(SongNotFound):
            add_song_to_playlist(self.playlist, self.owner, uuid.uuid4())

    def test_add_song_duplicate_raises(self):
        add_song_to_playlist(self.playlist, self.owner, self.song.id)
        with self.assertRaises(SongAlreadyInPlaylist):
            add_song_to_playlist(self.playlist, self.owner, self.song.id)

    def test_add_multiple_songs_incremental_order(self):
        song2 = make_song(self.artist, title='Second Song')
        ps1 = add_song_to_playlist(self.playlist, self.owner, self.song.id)
        ps2 = add_song_to_playlist(self.playlist, self.owner, song2.id)
        self.assertEqual(ps1.order, 1)
        self.assertEqual(ps2.order, 2)

    def test_remove_song_success(self):
        add_song_to_playlist(self.playlist, self.owner, self.song.id)
        remove_song_from_playlist(self.playlist, self.owner, self.song.id)
        self.assertFalse(check_song_in_playlist(self.playlist.id, self.song.id))

    def test_remove_song_not_owner_raises(self):
        add_song_to_playlist(self.playlist, self.owner, self.song.id)
        with self.assertRaises(NotPlaylistOwner):
            remove_song_from_playlist(self.playlist, self.other, self.song.id)

    def test_remove_song_not_in_playlist_raises(self):
        with self.assertRaises(SongNotInPlaylist):
            remove_song_from_playlist(self.playlist, self.owner, self.song.id)


class ReorderServiceTest(TestCase):

    def setUp(self):
        self.owner  = make_user('reowner', 'reowner@test.com')
        self.other  = make_user('reother', 'reother@test.com')
        self.artist = make_user('reartist', 'reartist@test.com', role='artist')
        self.playlist = make_playlist(self.owner)
        self.song1 = make_song(self.artist, title='Song A')
        self.song2 = make_song(self.artist, title='Song B')
        self.song3 = make_song(self.artist, title='Song C')
        add_song_to_playlist(self.playlist, self.owner, self.song1.id)
        add_song_to_playlist(self.playlist, self.owner, self.song2.id)
        add_song_to_playlist(self.playlist, self.owner, self.song3.id)

    def test_reorder_success(self):
        new_order = [self.song3.id, self.song1.id, self.song2.id]
        reorder_playlist_songs(self.playlist, self.owner, new_order)
        ids = list_playlist_song_ids(self.playlist.id)
        self.assertEqual(ids, [self.song3.id, self.song1.id, self.song2.id])

    def test_reorder_not_owner_raises(self):
        new_order = [self.song1.id, self.song2.id, self.song3.id]
        with self.assertRaises(NotPlaylistOwner):
            reorder_playlist_songs(self.playlist, self.other, new_order)

    def test_reorder_missing_song_raises(self):
        """Thiếu 1 bài trong danh sách gửi lên -> InvalidReorderData."""
        incomplete = [self.song1.id, self.song2.id]
        with self.assertRaises(InvalidReorderData):
            reorder_playlist_songs(self.playlist, self.owner, incomplete)

    def test_reorder_extra_unknown_song_raises(self):
        """Có ID lạ không thuộc playlist -> InvalidReorderData."""
        extra = [self.song1.id, self.song2.id, self.song3.id, uuid.uuid4()]
        with self.assertRaises(InvalidReorderData):
            reorder_playlist_songs(self.playlist, self.owner, extra)

    def test_reorder_preserves_count(self):
        new_order = [self.song2.id, self.song3.id, self.song1.id]
        reorder_playlist_songs(self.playlist, self.owner, new_order)
        self.assertEqual(PlaylistSong.objects.filter(playlist=self.playlist).count(), 3)


# ═══════════════════════════════════════════════════════════════════════════════
# VIEW TESTS (HTTP Integration)
# ═══════════════════════════════════════════════════════════════════════════════

class PlaylistListViewTest(TestCase):

    def setUp(self):
        self.client = Client(enforce_csrf_checks=False)
        self.owner  = make_user('lvowner', 'lvowner@test.com')

    def test_list_requires_auth(self):
        response = self.client.get('/api/v1/playlists/')
        self.assertEqual(response.status_code, 401)

    def test_list_my_playlists(self):
        make_playlist(self.owner, title='Mine')
        self.client.force_login(self.owner)
        response = self.client.get('/api/v1/playlists/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()['data']['items']), 1)

    def test_create_playlist_success(self):
        self.client.force_login(self.owner)
        response = self.client.post(
            '/api/v1/playlists/',
            data=json.dumps({'title': 'New Playlist', 'description': 'desc', 'is_public': True}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 201)
        data = response.json()['data']
        self.assertEqual(data['title'], 'New Playlist')
        self.assertTrue(data['is_owner'])

    def test_create_playlist_requires_auth(self):
        response = self.client.post(
            '/api/v1/playlists/',
            data=json.dumps({'title': 'X'}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 401)

    def test_create_playlist_validation_error(self):
        self.client.force_login(self.owner)
        response = self.client.post(
            '/api/v1/playlists/',
            data=json.dumps({'title': ''}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['error']['code'], 'VALIDATION_ERROR')


class PlaylistDetailViewTest(TestCase):

    def setUp(self):
        self.client = Client(enforce_csrf_checks=False)
        self.owner  = make_user('dvowner', 'dvowner@test.com')
        self.other  = make_user('dvother', 'dvother@test.com')

    def test_get_public_playlist_no_auth_needed(self):
        playlist = make_playlist(self.owner, is_public=True)
        response = self.client.get(f'/api/v1/playlists/{playlist.id}/')
        self.assertEqual(response.status_code, 200)

    def test_get_private_playlist_by_owner(self):
        playlist = make_playlist(self.owner, is_public=False)
        self.client.force_login(self.owner)
        response = self.client.get(f'/api/v1/playlists/{playlist.id}/')
        self.assertEqual(response.status_code, 200)

    def test_get_private_playlist_by_other_404(self):
        playlist = make_playlist(self.owner, is_public=False)
        self.client.force_login(self.other)
        response = self.client.get(f'/api/v1/playlists/{playlist.id}/')
        self.assertEqual(response.status_code, 404)

    def test_get_private_playlist_anonymous_404(self):
        playlist = make_playlist(self.owner, is_public=False)
        response = self.client.get(f'/api/v1/playlists/{playlist.id}/')
        self.assertEqual(response.status_code, 404)

    def test_get_nonexistent_playlist_404(self):
        response = self.client.get(f'/api/v1/playlists/{uuid.uuid4()}/')
        self.assertEqual(response.status_code, 404)

    def test_patch_playlist_as_owner(self):
        playlist = make_playlist(self.owner, title='Original')
        self.client.force_login(self.owner)
        response = self.client.patch(
            f'/api/v1/playlists/{playlist.id}/',
            data=json.dumps({'title': 'Updated'}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['data']['title'], 'Updated')

    def test_patch_playlist_not_owner_403(self):
        """Test phan quyen quan trong: chi owner moi duoc sua."""
        playlist = make_playlist(self.owner)
        self.client.force_login(self.other)
        response = self.client.patch(
            f'/api/v1/playlists/{playlist.id}/',
            data=json.dumps({'title': 'Hacked Title'}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()['error']['code'], 'PERMISSION_DENIED')

    def test_patch_playlist_requires_auth(self):
        playlist = make_playlist(self.owner)
        response = self.client.patch(
            f'/api/v1/playlists/{playlist.id}/',
            data=json.dumps({'title': 'X'}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 401)

    def test_patch_playlist_no_data_400(self):
        playlist = make_playlist(self.owner)
        self.client.force_login(self.owner)
        response = self.client.patch(
            f'/api/v1/playlists/{playlist.id}/',
            data=json.dumps({}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)

    def test_delete_playlist_as_owner(self):
        playlist = make_playlist(self.owner)
        self.client.force_login(self.owner)
        response = self.client.delete(f'/api/v1/playlists/{playlist.id}/')
        self.assertEqual(response.status_code, 204)
        self.assertFalse(Playlist.objects.filter(id=playlist.id).exists())

    def test_delete_playlist_not_owner_403(self):
        """Test phan quyen quan trong: chi owner moi duoc xoa."""
        playlist = make_playlist(self.owner)
        self.client.force_login(self.other)
        response = self.client.delete(f'/api/v1/playlists/{playlist.id}/')
        self.assertEqual(response.status_code, 403)
        self.assertTrue(Playlist.objects.filter(id=playlist.id).exists())

    def test_delete_playlist_requires_auth(self):
        playlist = make_playlist(self.owner)
        response = self.client.delete(f'/api/v1/playlists/{playlist.id}/')
        self.assertEqual(response.status_code, 401)


class PlaylistVisibilityViewTest(TestCase):

    def setUp(self):
        self.client = Client(enforce_csrf_checks=False)
        self.owner = make_user('vvowner', 'vvowner@test.com')
        self.other = make_user('vvother', 'vvother@test.com')

    def test_set_private_as_owner(self):
        playlist = make_playlist(self.owner, is_public=True)
        self.client.force_login(self.owner)
        response = self.client.patch(
            f'/api/v1/playlists/{playlist.id}/visibility/',
            data=json.dumps({'is_public': False}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()['data']['is_public'])

    def test_set_visibility_not_owner_403(self):
        playlist = make_playlist(self.owner, is_public=True)
        self.client.force_login(self.other)
        response = self.client.patch(
            f'/api/v1/playlists/{playlist.id}/visibility/',
            data=json.dumps({'is_public': False}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 403)

    def test_set_visibility_invalid_value_400(self):
        playlist = make_playlist(self.owner)
        self.client.force_login(self.owner)
        response = self.client.patch(
            f'/api/v1/playlists/{playlist.id}/visibility/',
            data=json.dumps({'is_public': 'not-a-bool'}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)


class PlaylistSongViewTest(TestCase):

    def setUp(self):
        self.client = Client(enforce_csrf_checks=False)
        self.owner  = make_user('psvowner', 'psvowner@test.com')
        self.other  = make_user('psvother', 'psvother@test.com')
        self.artist = make_user('psvartist', 'psvartist@test.com', role='artist')
        self.playlist = make_playlist(self.owner)
        self.song   = make_song(self.artist, title='Addable')

    def test_add_song_as_owner(self):
        self.client.force_login(self.owner)
        response = self.client.post(
            f'/api/v1/playlists/{self.playlist.id}/songs/',
            data=json.dumps({'song_id': str(self.song.id)}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()['data']['song']['title'], 'Addable')

    def test_add_song_not_owner_403(self):
        """Test phan quyen: chi owner moi them duoc bai hat."""
        self.client.force_login(self.other)
        response = self.client.post(
            f'/api/v1/playlists/{self.playlist.id}/songs/',
            data=json.dumps({'song_id': str(self.song.id)}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 403)

    def test_add_song_requires_auth(self):
        response = self.client.post(
            f'/api/v1/playlists/{self.playlist.id}/songs/',
            data=json.dumps({'song_id': str(self.song.id)}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 401)

    def test_add_song_duplicate_409(self):
        self.client.force_login(self.owner)
        self.client.post(
            f'/api/v1/playlists/{self.playlist.id}/songs/',
            data=json.dumps({'song_id': str(self.song.id)}),
            content_type='application/json',
        )
        response = self.client.post(
            f'/api/v1/playlists/{self.playlist.id}/songs/',
            data=json.dumps({'song_id': str(self.song.id)}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 409)

    def test_add_nonexistent_song_404(self):
        self.client.force_login(self.owner)
        response = self.client.post(
            f'/api/v1/playlists/{self.playlist.id}/songs/',
            data=json.dumps({'song_id': str(uuid.uuid4())}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 404)

    def test_list_songs_in_public_playlist_no_auth(self):
        add_song_to_playlist(self.playlist, self.owner, self.song.id)
        response = self.client.get(f'/api/v1/playlists/{self.playlist.id}/songs/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()['data']['items']), 1)

    def test_list_songs_in_private_playlist_blocked_for_others(self):
        private_pl = make_playlist(self.owner, is_public=False)
        add_song_to_playlist(private_pl, self.owner, self.song.id)
        self.client.force_login(self.other)
        response = self.client.get(f'/api/v1/playlists/{private_pl.id}/songs/')
        self.assertEqual(response.status_code, 404)

    def test_remove_song_as_owner(self):
        add_song_to_playlist(self.playlist, self.owner, self.song.id)
        self.client.force_login(self.owner)
        response = self.client.delete(
            f'/api/v1/playlists/{self.playlist.id}/songs/{self.song.id}/'
        )
        self.assertEqual(response.status_code, 204)
        self.assertFalse(check_song_in_playlist(self.playlist.id, self.song.id))

    def test_remove_song_not_owner_403(self):
        """Test phan quyen: chi owner moi xoa duoc bai hat."""
        add_song_to_playlist(self.playlist, self.owner, self.song.id)
        self.client.force_login(self.other)
        response = self.client.delete(
            f'/api/v1/playlists/{self.playlist.id}/songs/{self.song.id}/'
        )
        self.assertEqual(response.status_code, 403)

    def test_remove_song_not_in_playlist_404(self):
        self.client.force_login(self.owner)
        response = self.client.delete(
            f'/api/v1/playlists/{self.playlist.id}/songs/{self.song.id}/'
        )
        self.assertEqual(response.status_code, 404)


class PlaylistReorderViewTest(TestCase):

    def setUp(self):
        self.client = Client(enforce_csrf_checks=False)
        self.owner  = make_user('rvowner', 'rvowner@test.com')
        self.other  = make_user('rvother', 'rvother@test.com')
        self.artist = make_user('rvartist', 'rvartist@test.com', role='artist')
        self.playlist = make_playlist(self.owner)
        self.song1 = make_song(self.artist, title='A')
        self.song2 = make_song(self.artist, title='B')
        add_song_to_playlist(self.playlist, self.owner, self.song1.id)
        add_song_to_playlist(self.playlist, self.owner, self.song2.id)

    def test_reorder_as_owner(self):
        self.client.force_login(self.owner)
        response = self.client.patch(
            f'/api/v1/playlists/{self.playlist.id}/songs/reorder/',
            data=json.dumps({'song_ids': [str(self.song2.id), str(self.song1.id)]}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        ids = list_playlist_song_ids(self.playlist.id)
        self.assertEqual(ids, [self.song2.id, self.song1.id])

    def test_reorder_not_owner_403(self):
        """Test phan quyen: chi owner moi sap xep lai duoc."""
        self.client.force_login(self.other)
        response = self.client.patch(
            f'/api/v1/playlists/{self.playlist.id}/songs/reorder/',
            data=json.dumps({'song_ids': [str(self.song1.id), str(self.song2.id)]}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 403)

    def test_reorder_mismatched_ids_400(self):
        self.client.force_login(self.owner)
        response = self.client.patch(
            f'/api/v1/playlists/{self.playlist.id}/songs/reorder/',
            data=json.dumps({'song_ids': [str(self.song1.id)]}),  # thieu song2
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)

    def test_reorder_requires_auth(self):
        response = self.client.patch(
            f'/api/v1/playlists/{self.playlist.id}/songs/reorder/',
            data=json.dumps({'song_ids': [str(self.song1.id), str(self.song2.id)]}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 401)


class PlaylistCoverUploadViewTest(TestCase):

    def setUp(self):
        self.client = Client(enforce_csrf_checks=False)
        self.owner = make_user('cvowner', 'cvowner@test.com')
        self.other = make_user('cvother', 'cvother@test.com')

    def test_upload_cover_as_owner(self):
        playlist = make_playlist(self.owner)
        self.client.force_login(self.owner)
        response = self.client.post(
            f'/api/v1/playlists/{playlist.id}/cover/',
            data={'cover_image': make_image_file()},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(response.json()['data']['cover_image'])

    def test_upload_cover_not_owner_403(self):
        playlist = make_playlist(self.owner)
        self.client.force_login(self.other)
        response = self.client.post(
            f'/api/v1/playlists/{playlist.id}/cover/',
            data={'cover_image': make_image_file()},
        )
        self.assertEqual(response.status_code, 403)

    def test_upload_cover_invalid_mime_400(self):
        playlist = make_playlist(self.owner)
        self.client.force_login(self.owner)
        response = self.client.post(
            f'/api/v1/playlists/{playlist.id}/cover/',
            data={'cover_image': SimpleUploadedFile('f.txt', b'data', content_type='text/plain')},
        )
        self.assertEqual(response.status_code, 400)

    def test_upload_cover_missing_file_400(self):
        playlist = make_playlist(self.owner)
        self.client.force_login(self.owner)
        response = self.client.post(f'/api/v1/playlists/{playlist.id}/cover/', data={})
        self.assertEqual(response.status_code, 400)


# ═══════════════════════════════════════════════════════════════════════════════
# END-TO-END FLOW TEST
# ═══════════════════════════════════════════════════════════════════════════════

class EndToEndPlaylistFlowTest(TestCase):
    """Test toan bo luong: tao playlist -> them bai -> reorder -> doi visibility -> xoa."""

    def setUp(self):
        self.client = Client(enforce_csrf_checks=False)
        self.owner  = make_user('e2eplowner', 'e2eplowner@test.com')
        self.viewer = make_user('e2eplviewer', 'e2eplviewer@test.com')
        self.artist = make_user('e2eplartist', 'e2eplartist@test.com', role='artist')

    def test_full_playlist_lifecycle(self):
        # 1. Tạo 3 bài hát published để thêm vào playlist
        genre = make_genre('E2E Playlist Genre')
        song1 = make_song(self.artist, genre, title='Track 1')
        song2 = make_song(self.artist, genre, title='Track 2')
        song3 = make_song(self.artist, genre, title='Track 3')

        # 2. Owner tạo playlist (public)
        self.client.force_login(self.owner)
        r1 = self.client.post(
            '/api/v1/playlists/',
            data=json.dumps({'title': 'E2E Playlist', 'description': 'Test flow', 'is_public': True}),
            content_type='application/json',
        )
        self.assertEqual(r1.status_code, 201)
        playlist_id = r1.json()['data']['id']

        # 3. Thêm 3 bài hát vào playlist
        for song in (song1, song2, song3):
            r = self.client.post(
                f'/api/v1/playlists/{playlist_id}/songs/',
                data=json.dumps({'song_id': str(song.id)}),
                content_type='application/json',
            )
            self.assertEqual(r.status_code, 201)

        # 4. Viewer khác (chưa đăng nhập cần) xem playlist công khai -> thấy đủ 3 bài
        self.client.logout()
        r4 = self.client.get(f'/api/v1/playlists/{playlist_id}/songs/')
        self.assertEqual(r4.status_code, 200)
        self.assertEqual(len(r4.json()['data']['items']), 3)
        titles = [item['song']['title'] for item in r4.json()['data']['items']]
        self.assertEqual(titles, ['Track 1', 'Track 2', 'Track 3'])

        # 5. Owner sắp xếp lại thứ tự: 3 -> 1 -> 2
        self.client.force_login(self.owner)
        r5 = self.client.patch(
            f'/api/v1/playlists/{playlist_id}/songs/reorder/',
            data=json.dumps({'song_ids': [str(song3.id), str(song1.id), str(song2.id)]}),
            content_type='application/json',
        )
        self.assertEqual(r5.status_code, 200)

        # 6. Xác nhận thứ tự đã đổi
        r6 = self.client.get(f'/api/v1/playlists/{playlist_id}/songs/')
        titles_after = [item['song']['title'] for item in r6.json()['data']['items']]
        self.assertEqual(titles_after, ['Track 3', 'Track 1', 'Track 2'])

        # 7. Owner xóa 1 bài khỏi playlist
        r7 = self.client.delete(f'/api/v1/playlists/{playlist_id}/songs/{song2.id}/')
        self.assertEqual(r7.status_code, 204)

        # 8. Xác nhận còn lại 2 bài
        r8 = self.client.get(f'/api/v1/playlists/{playlist_id}/songs/')
        self.assertEqual(len(r8.json()['data']['items']), 2)

        # 9. Owner đặt playlist thành private
        r9 = self.client.patch(
            f'/api/v1/playlists/{playlist_id}/visibility/',
            data=json.dumps({'is_public': False}),
            content_type='application/json',
        )
        self.assertEqual(r9.status_code, 200)
        self.assertFalse(r9.json()['data']['is_public'])

        # 10. Viewer khác không còn xem được playlist (404)
        self.client.force_login(self.viewer)
        r10 = self.client.get(f'/api/v1/playlists/{playlist_id}/')
        self.assertEqual(r10.status_code, 404)

        # 11. Viewer khác không thể thêm bài vào playlist (403, vì không phải owner)
        r11 = self.client.post(
            f'/api/v1/playlists/{playlist_id}/songs/',
            data=json.dumps({'song_id': str(song3.id)}),
            content_type='application/json',
        )
        self.assertEqual(r11.status_code, 403)

        # 12. Owner vẫn xem và xóa được playlist của chính mình
        self.client.force_login(self.owner)
        r12 = self.client.get(f'/api/v1/playlists/{playlist_id}/')
        self.assertEqual(r12.status_code, 200)

        r13 = self.client.delete(f'/api/v1/playlists/{playlist_id}/')
        self.assertEqual(r13.status_code, 204)

        # 14. Playlist không còn tồn tại
        r14 = self.client.get(f'/api/v1/playlists/{playlist_id}/')
        self.assertEqual(r14.status_code, 404)
```

---

*Tổng cộng: 10 files — 2211 dòng code, đã chạy test xác nhận PASS 100%.*
