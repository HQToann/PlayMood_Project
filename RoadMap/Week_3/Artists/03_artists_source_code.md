# 03 — Source Code Hoàn Chỉnh App `artists`

**Tuần 4 | Đã verify: 73/73 tests pass riêng app này, 92/92 tests pass baseline + artists**

> Copy từng file vào đúng thư mục `artists/` trong project.
> Sau khi copy xong, xem file `05_artists_configs_and_db_changes.md` để biết các bước apply.

---

## Cấu Trúc File

```
artists/
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

## `artists/apps.py`

```python
"""artists/apps.py"""
from django.apps import AppConfig


class ArtistsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'artists'
    label = 'artists'
    verbose_name = 'Nghe si'
```

---

## `artists/models.py`

```python
"""
artists/models.py
==================
Models cho app artists:
  - ArtistProfile: Ho so nghe si mo rong (stage_name, bio, cover_image rieng)

ArtistProfile la 1-1 voi accounts.User (chi user co role='artist' moi co profile).
Thong ke (play_count, like_count, comment_count...) KHONG luu trong model nay,
ma duoc tinh real-time qua selectors.py tu cac bang Song/Like/Rating/Comment/ListenHistory
da co san trong app music - tranh du lieu thua va out-of-sync.
"""

import uuid
from django.db import models


class ArtistProfile(models.Model):
    """
    Ho so nghe si - mo rong them thong tin rieng cho user co role='artist'.

    Quan he 1-1 voi User: moi nghe si chi co duy nhat 1 ArtistProfile.
    Avatar va bio co ban van dung chung User.avatar/User.bio (Tuan 1),
    ArtistProfile chi them cac truong rieng cho trang nghe si cong khai:
        - stage_name: ten nghe danh (khac display_name ca nhan)
        - cover_image: anh bia rieng cho trang nghe si (khac avatar)
        - social_links: cac duong dan mang xa hoi (JSON-like text don gian)
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    user = models.OneToOneField(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='artist_profile',
        verbose_name='Nguoi dung',
    )

    stage_name = models.CharField(max_length=100, blank=True, default='', verbose_name='Ten nghe danh')
    bio = models.TextField(blank=True, default='', verbose_name='Gioi thieu nghe si')

    # Anh bia rieng cho trang nghe si, path: covers/artists/<uuid>.<ext>
    cover_image = models.ImageField(
        upload_to='covers/artists/',
        blank=True,
        null=True,
        verbose_name='Anh bia',
    )

    website_url = models.CharField(max_length=255, blank=True, default='', verbose_name='Website')
    facebook_url = models.CharField(max_length=255, blank=True, default='', verbose_name='Facebook')
    youtube_url = models.CharField(max_length=255, blank=True, default='', verbose_name='YouTube')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'artists_artist_profile'
        ordering = ['-created_at']
        verbose_name = 'Ho so nghe si'
        verbose_name_plural = 'Ho so nghe si'

    def __str__(self):
        return f'{self.get_display_name()} ({self.user.username})'

    def get_display_name(self):
        """Tra ten nghe danh, fallback ve display_name/username cua User."""
        return self.stage_name or self.user.get_display_name()

    def to_dict(self, viewer=None, include_stats=False):
        """
        Serialize ArtistProfile thanh dict.

        Args:
            viewer:        User dang xem (de quyet dinh is_owner)
            include_stats: co tinh stats hay khong - LUON dung selectors.get_artist_stats()
                          o tang selectors/views de tinh, KHONG tinh trong model nay
                          (tranh model phu thuoc nguoc vao selectors cua app khac)
        """
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
            'cover_image': self.cover_image.url if self.cover_image else None,
            'website_url': self.website_url,
            'facebook_url': self.facebook_url,
            'youtube_url': self.youtube_url,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
        }
        viewer_id = getattr(viewer, 'id', None)
        if viewer_id and getattr(viewer, 'is_authenticated', False):
            data['is_owner'] = str(viewer_id) == str(self.user_id)
        else:
            data['is_owner'] = False
        return data
```

---

## `artists/exceptions.py`

```python
"""
artists/exceptions.py
=======================
Custom exceptions cho nghiep vu app artists.
"""

from accounts.exceptions import AppException


class ArtistProfileNotFound(AppException):
    """Ho so nghe si khong ton tai (user chua phai artist hoac chua tao profile) - HTTP 404."""
    def __init__(self, message='Ho so nghe si khong ton tai'):
        super().__init__(message, error_code='NOT_FOUND')


class ArtistProfileAlreadyExists(AppException):
    """User da co ArtistProfile, khong tao them duoc - HTTP 409."""
    def __init__(self, message='Ho so nghe si da ton tai'):
        super().__init__(message, error_code='ALREADY_EXISTS')


class NotArtistProfileOwner(AppException):
    """Khong phai chu ho so, khong duoc sua - HTTP 403."""
    def __init__(self, message='Ban khong co quyen thuc hien hanh dong nay'):
        super().__init__(message, error_code='PERMISSION_DENIED')


class UserNotArtist(AppException):
    """User chua co role='artist', khong the tao ArtistProfile - HTTP 403."""
    def __init__(self, message='Chi tai khoan nghe si moi co the tao ho so nghe si'):
        super().__init__(message, error_code='ARTIST_ONLY')
```

---

## `artists/validators.py`

```python
"""
artists/validators.py
=======================
Kiem tra du lieu dau vao cho app artists.

Quy uoc (giu nguyen tu Tuan 1-3):
  - CHI kiem tra kieu du lieu, bat buoc, do dai, format
  - KHONG goi service, KHONG truy van DB
  - KHONG raise HTTP exception - chi raise ValidationError tu accounts.exceptions
  - Moi text public phai qua sanitize_text() (Fix R12)
"""

from music_platform.sanitize import sanitize_text, sanitize_url
from accounts.exceptions import ValidationError

STAGE_NAME_MAX = 100
BIO_MAX = 1000

ALLOWED_IMAGE_TYPES = {'image/jpeg', 'image/png', 'image/webp'}
MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5 MB


def validate_artist_profile_create(data: dict) -> dict:
    """
    Validate tao ho so nghe si moi.

    Tat ca field deu optional - artist co the tao profile rong roi cap nhat sau.
    """
    errors = {}
    result = {}

    stage_name = data.get('stage_name', '')
    if len(stage_name) > STAGE_NAME_MAX:
        errors['stage_name'] = [f'Ten nghe danh toi da {STAGE_NAME_MAX} ky tu']
    else:
        result['stage_name'] = sanitize_text(stage_name)

    bio = data.get('bio', '')
    if len(bio) > BIO_MAX:
        errors['bio'] = [f'Gioi thieu toi da {BIO_MAX} ky tu']
    else:
        result['bio'] = sanitize_text(bio)

    for field in ('website_url', 'facebook_url', 'youtube_url'):
        url = data.get(field, '').strip()
        if url:
            try:
                result[field] = sanitize_url(url)
            except ValueError:
                errors[field] = ['URL phai bat dau bang http:// hoac https://']
        else:
            result[field] = ''

    if errors:
        raise ValidationError('Du lieu ho so nghe si khong hop le', fields=errors)

    return result


def validate_artist_profile_update(data: dict) -> dict:
    """
    Validate cap nhat ho so nghe si - partial update.

    Chi field nao gui len moi validate, giong pattern validate_song_update.
    """
    errors = {}
    result = {}

    if 'stage_name' in data:
        stage_name = data['stage_name']
        if len(stage_name) > STAGE_NAME_MAX:
            errors['stage_name'] = [f'Ten nghe danh toi da {STAGE_NAME_MAX} ky tu']
        else:
            result['stage_name'] = sanitize_text(stage_name)

    if 'bio' in data:
        bio = data['bio']
        if len(bio) > BIO_MAX:
            errors['bio'] = [f'Gioi thieu toi da {BIO_MAX} ky tu']
        else:
            result['bio'] = sanitize_text(bio)

    for field in ('website_url', 'facebook_url', 'youtube_url'):
        if field in data:
            url = data[field].strip()
            if url:
                try:
                    result[field] = sanitize_url(url)
                except ValueError:
                    errors[field] = ['URL phai bat dau bang http:// hoac https://']
            else:
                result[field] = ''

    if errors:
        raise ValidationError('Du lieu cap nhat khong hop le', fields=errors)

    return result


def validate_cover_image(files: dict) -> None:
    """
    Validate file anh bia nghe si.

    Raises:
        ValidationError: neu file khong hop le
    """
    if 'cover_image' not in files:
        raise ValidationError(
            'Du lieu khong hop le',
            fields={'cover_image': ['File anh la bat buoc']},
        )

    cover = files['cover_image']
    errors = {}
    if cover.content_type not in ALLOWED_IMAGE_TYPES:
        errors['cover_image'] = ['Chi chap nhan JPG, PNG, WEBP']
    elif cover.size > MAX_IMAGE_SIZE:
        errors['cover_image'] = ['File toi da 5 MB']

    if errors:
        raise ValidationError('File khong hop le', fields=errors)


def validate_list_artists_params(params: dict) -> dict:
    """Validate va lam sach query params khi list nghe si."""
    try:
        page = max(1, int(params.get('page', 1)))
    except (ValueError, TypeError):
        page = 1

    try:
        page_size = min(100, max(1, int(params.get('page_size', 20))))
    except (ValueError, TypeError):
        page_size = 20

    return {
        'q': params.get('q', '').strip(),
        'page': page,
        'page_size': page_size,
    }
```

---

## `artists/selectors.py`

```python
"""
artists/selectors.py
======================
Tang Doc cho app artists - moi truy van DB chi duoc viet o day.

Quy uoc (giu nguyen tu Tuan 1-3):
  - CHI doc du lieu, KHONG ghi
  - Prefix ham: get_*, list_*, count_*, is_*, check_*
  - KHONG raise HTTP exception (raise custom exception nghiep vu neu can)

Diem ky thuat quan trong nhat cua app nay: get_artist_stats() tinh thong ke
TONG HOP tu nhieu bang cua app music (Song, Like, Rating, Comment, ListenHistory)
ma KHONG luu cache trong DB - moi lan goi deu query lai (Fix dam bao stats luon
chinh xac, danh doi mot chut hieu nang cho su don gian va dung dan o giai doan nay).
"""

import math
from django.db.models import Count, Avg, Sum, Q

from artists.models import ArtistProfile
from artists.exceptions import ArtistProfileNotFound
from accounts.models import User
from accounts.selectors import is_blocked
from music.models import Song, Like, Rating, Comment, ListenHistory


def get_artist_profile_by_user_id(user_id) -> ArtistProfile:
    """
    Lay ArtistProfile theo user_id - KHONG kiem tra quyen xem.

    Dung noi bo trong services khi da biet chac can thao tac.

    Raises:
        ArtistProfileNotFound: neu chua co profile
    """
    try:
        return ArtistProfile.objects.select_related('user').get(user_id=user_id)
    except ArtistProfile.DoesNotExist:
        raise ArtistProfileNotFound()


def get_artist_profile_detail(user_id, viewer=None) -> ArtistProfile:
    """
    Lay ArtistProfile de tra ve cho client - CO kiem tra block policy (Fix R10).

    Neu viewer bi target (nghe si) block: tra NotFound (404) - giong pattern
    get_public_profile() trong accounts/selectors.py va get_song_detail()
    trong music/selectors.py, khong de lo thong tin bi block.

    Raises:
        ArtistProfileNotFound: neu khong ton tai hoac viewer bi block
    """
    try:
        profile = ArtistProfile.objects.select_related('user').get(user_id=user_id)
    except ArtistProfile.DoesNotExist:
        raise ArtistProfileNotFound()

    viewer_id = getattr(viewer, 'id', None)
    viewer_is_auth = bool(viewer_id and getattr(viewer, 'is_authenticated', False))
    if viewer_is_auth and is_blocked(viewer_id, profile.user_id):
        raise ArtistProfileNotFound()

    return profile


def check_profile_exists(user_id) -> bool:
    """Kiem tra user da co ArtistProfile chua."""
    return ArtistProfile.objects.filter(user_id=user_id).exists()


def list_artists(filters: dict, viewer=None) -> dict:
    """
    Danh sach nghe si (co ArtistProfile), tim theo stage_name/username, phan trang.

    Block policy: an nghe si da block viewer (Fix R10), tuong tu list_songs()
    trong music/selectors.py.
    """
    qs = ArtistProfile.objects.select_related('user')

    viewer_id = getattr(viewer, 'id', None)
    viewer_is_auth = bool(viewer_id and getattr(viewer, 'is_authenticated', False))
    if viewer_is_auth:
        from accounts.models import BlockList
        blocked_user_ids = BlockList.objects.filter(blocked_id=viewer_id).values_list('blocker_id', flat=True)
        qs = qs.exclude(user_id__in=blocked_user_ids)

    if filters.get('q'):
        qs = qs.filter(
            Q(stage_name__icontains=filters['q']) | Q(user__username__icontains=filters['q'])
        )

    qs = qs.order_by('-created_at')

    page = filters.get('page', 1)
    page_size = filters.get('page_size', 20)
    total = qs.count()
    start = (page - 1) * page_size
    items = [p.to_dict(viewer=viewer) for p in qs[start:start + page_size]]

    return {
        'items': items,
        'pagination': {
            'page': page,
            'page_size': page_size,
            'total': total,
            'total_pages': math.ceil(total / page_size) if total > 0 else 1,
        },
    }


def get_artist_stats(artist_user_id) -> dict:
    """
    Tinh thong ke tong hop cua nghe si - DIEM KY THUAT QUAN TRONG NHAT cua app nay.

    Thong ke duoc tinh TU CAC BANG DA CO SAN trong app music, KHONG luu field
    rieng trong ArtistProfile - dam bao stats luon dung 100% voi du lieu thuc te
    (khong bi out-of-sync nhu khi luu counter cache rieng).

    Cac so lieu:
        total_songs:       So bai hat published cua nghe si
        total_play_count:  Tong play_count cua tat ca bai hat (Sum, khong phai Count)
        total_likes:       Tong so luot Like tren tat ca bai hat cua nghe si
        total_comments:    Tong so Comment (khong tinh comment bi an) tren bai hat
        total_listeners:   So luong user UNIQUE da nghe it nhat 1 bai (Count distinct)
        avg_rating:        Diem trung binh tat ca Rating tren moi bai hat cua nghe si
        rating_count:      Tong so luot danh gia

    Args:
        artist_user_id: UUID cua User (nghe si)

    Returns:
        dict chua toan bo so lieu thong ke, gia tri 0/None neu chua co du lieu
    """
    # Chi tinh tren bai hat published - bai draft/hidden khong tinh vao thong ke cong khai
    songs_qs = Song.objects.filter(artist_id=artist_user_id, status=Song.STATUS_PUBLISHED)

    total_songs = songs_qs.count()

    # Sum play_count cua tat ca bai hat - dung Sum() aggregate, tranh N+1 query
    play_count_agg = songs_qs.aggregate(total=Sum('play_count'))
    total_play_count = play_count_agg['total'] or 0

    # Tong so Like tren toan bo bai hat cua nghe si (qua FK song__artist_id)
    total_likes = Like.objects.filter(song__artist_id=artist_user_id, song__status=Song.STATUS_PUBLISHED).count()

    # Tong so Comment KHONG bi an tren toan bo bai hat cua nghe si
    total_comments = Comment.objects.filter(
        song__artist_id=artist_user_id,
        song__status=Song.STATUS_PUBLISHED,
        is_hidden=False,
    ).count()

    # So luong NGUOI NGHE DUY NHAT (distinct user_id trong ListenHistory)
    total_listeners = ListenHistory.objects.filter(
        song__artist_id=artist_user_id,
        song__status=Song.STATUS_PUBLISHED,
    ).values('user_id').distinct().count()

    # Diem danh gia trung binh + tong so luot danh gia
    rating_agg = Rating.objects.filter(
        song__artist_id=artist_user_id,
        song__status=Song.STATUS_PUBLISHED,
    ).aggregate(avg=Avg('score'), count=Count('id'))

    return {
        'total_songs': total_songs,
        'total_play_count': total_play_count,
        'total_likes': total_likes,
        'total_comments': total_comments,
        'total_listeners': total_listeners,
        'avg_rating': round(rating_agg['avg'], 1) if rating_agg['avg'] else None,
        'rating_count': rating_agg['count'],
    }


def list_artist_top_songs(artist_user_id, limit=10) -> list:
    """
    Top bai hat cua nghe si theo luot nghe - dung cho phan thong ke chi tiet.

    Chi tinh bai hat published, sap xep giam dan theo play_count.
    """
    songs = (
        Song.objects
        .filter(artist_id=artist_user_id, status=Song.STATUS_PUBLISHED)
        .order_by('-play_count')[:limit]
    )
    return [
        {
            'id': str(s.id),
            'title': s.title,
            'play_count': s.play_count,
            'like_count': s.likes.count(),
            'cover_image': s.cover_image.url if s.cover_image else None,
        }
        for s in songs
    ]
```

---

## `artists/services.py`

```python
"""
artists/services.py
=====================
Tang Ghi cho app artists - moi logic Create/Update/Delete o day.

Quy uoc (giu nguyen tu Tuan 1-3):
  - Xu ly toan bo business logic ghi du lieu
  - KHONG tra HTTP response
  - Co the goi selectors de doc, nhung selectors khong goi nguoc lai
  - Raise custom exception tu exceptions.py khi co loi nghiep vu
"""

import logging

from artists.models import ArtistProfile
from artists.selectors import check_profile_exists, get_artist_profile_by_user_id
from artists.exceptions import ArtistProfileAlreadyExists, NotArtistProfileOwner, UserNotArtist

logger = logging.getLogger(__name__)


def create_artist_profile(user, data: dict) -> ArtistProfile:
    """
    Tao ho so nghe si moi cho user.

    Business rules:
        - User phai co role='artist' (kiem tra o view bang @require_artist
          decorator co san tu Tuan 1, service kiem tra lai de phong thu)
        - Moi user chi tao duoc 1 ArtistProfile (OneToOneField + check tuong minh)

    Raises:
        UserNotArtist:             neu user khong co role='artist'
        ArtistProfileAlreadyExists: neu user da co profile
    """
    if user.role != 'artist':
        raise UserNotArtist()

    if check_profile_exists(user.id):
        raise ArtistProfileAlreadyExists()

    profile = ArtistProfile.objects.create(
        user=user,
        stage_name=data.get('stage_name', ''),
        bio=data.get('bio', ''),
        website_url=data.get('website_url', ''),
        facebook_url=data.get('facebook_url', ''),
        youtube_url=data.get('youtube_url', ''),
    )
    logger.info('ArtistProfile created: user=%s', user.username)
    return profile


def update_artist_profile(profile: ArtistProfile, user, data: dict) -> ArtistProfile:
    """
    Cap nhat ho so nghe si - chi owner.

    Raises:
        NotArtistProfileOwner: neu user khong phai chu ho so
    """
    if str(profile.user_id) != str(user.id):
        raise NotArtistProfileOwner()

    for field, value in data.items():
        setattr(profile, field, value)

    profile.save(update_fields=list(data.keys()) + ['updated_at'])
    logger.info('ArtistProfile updated: user=%s', profile.user.username)
    return profile


def update_cover_image(profile: ArtistProfile, user, cover_file) -> ArtistProfile:
    """
    Cap nhat anh bia nghe si - chi owner.

    File upload thang len Cloudinary qua DEFAULT_FILE_STORAGE.
    Path: covers/artists/<uuid>.<ext>

    Raises:
        NotArtistProfileOwner: neu user khong phai chu ho so
    """
    if str(profile.user_id) != str(user.id):
        raise NotArtistProfileOwner()

    # Xoa anh bia cu tren Cloudinary neu co, tranh file mo coi
    if profile.cover_image:
        try:
            profile.cover_image.delete(save=False)
        except Exception as e:
            logger.warning('Failed to delete old cover for artist %s: %s', profile.user_id, e)

    profile.cover_image = cover_file
    profile.save(update_fields=['cover_image', 'updated_at'])
    logger.info('ArtistProfile cover updated: user=%s', profile.user.username)
    return profile


def get_or_create_my_profile(user) -> ArtistProfile:
    """
    Lay ArtistProfile cua chinh user dang dang nhap, tu dong tao rong neu chua co.

    Dung cho endpoint GET /me/ cua artist - tranh bat artist phai goi POST
    truoc khi xem duoc trang ca nhan cua chinh ho.

    Raises:
        UserNotArtist: neu user khong co role='artist'
    """
    if user.role != 'artist':
        raise UserNotArtist()

    if check_profile_exists(user.id):
        return get_artist_profile_by_user_id(user.id)

    profile = ArtistProfile.objects.create(user=user)
    logger.info('ArtistProfile auto-created on first access: user=%s', user.username)
    return profile
```

---

## `artists/views.py`

```python
"""
artists/views.py
==================
Tang HTTP cho app artists.

Quy uoc (giu nguyen tu Tuan 1-3):
  - views.py KHONG import ArtistProfile, Song, Like... de query truc tiep
  - Moi query qua selectors.py, moi ghi qua services.py
  - Exception tu services/selectors duoc map sang HTTP status qua handle_exception()
"""

import json
import logging

from django.http import JsonResponse
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect

from accounts.decorators import require_auth, require_artist
from accounts.exceptions import ValidationError, PermissionDenied, NotFound, AlreadyExists

from artists.exceptions import (
    ArtistProfileNotFound, ArtistProfileAlreadyExists, NotArtistProfileOwner, UserNotArtist,
)
from artists.validators import (
    validate_artist_profile_create, validate_artist_profile_update,
    validate_cover_image, validate_list_artists_params,
)
from artists.selectors import (
    get_artist_profile_by_user_id, get_artist_profile_detail, list_artists,
    get_artist_stats, list_artist_top_songs,
)
from artists.services import (
    create_artist_profile, update_artist_profile, update_cover_image,
    get_or_create_my_profile,
)

logger = logging.getLogger(__name__)


def parse_json_body(request) -> dict:
    """Parse JSON body an toan - tra {} neu body rong hoac loi parse."""
    try:
        return json.loads(request.body or '{}')
    except (json.JSONDecodeError, ValueError):
        return {}


def handle_exception(e: Exception) -> JsonResponse:
    """Map exception nghiep vu sang HTTP response chuan. Dung chung cho moi view trong app nay."""
    if isinstance(e, ValidationError):
        return JsonResponse(
            {'success': False, 'error': {'code': 'VALIDATION_ERROR', 'message': e.message, 'fields': e.fields}},
            status=400,
        )
    if isinstance(e, (NotArtistProfileOwner, PermissionDenied, UserNotArtist)):
        return JsonResponse(
            {'success': False, 'error': {'code': e.error_code, 'message': e.message}},
            status=403,
        )
    if isinstance(e, (ArtistProfileNotFound, NotFound)):
        return JsonResponse(
            {'success': False, 'error': {'code': 'NOT_FOUND', 'message': e.message}},
            status=404,
        )
    if isinstance(e, (ArtistProfileAlreadyExists, AlreadyExists)):
        return JsonResponse(
            {'success': False, 'error': {'code': 'ALREADY_EXISTS', 'message': e.message}},
            status=409,
        )
    logger.exception('Unhandled exception in artists views: %s', e)
    return JsonResponse(
        {'success': False, 'error': {'code': 'SERVER_ERROR', 'message': 'Loi server'}},
        status=500,
    )


class ArtistListView(View):
    """GET /api/v1/artists/ - Danh sach nghe si (Public)"""

    def get(self, request):
        try:
            filters = validate_list_artists_params(request.GET)
            result = list_artists(filters, viewer=request.user)
            return JsonResponse({'success': True, 'data': result})
        except Exception as e:
            return handle_exception(e)


class MyArtistProfileView(View):
    """
    GET  /api/v1/artists/me/  - Xem ho so cua chinh minh (Artist), tu tao rong neu chua co
    POST /api/v1/artists/me/  - Tao ho so nghe si (Artist+CSRF)
    """

    @method_decorator(require_artist)
    def get(self, request):
        try:
            profile = get_or_create_my_profile(request.user)
            return JsonResponse({'success': True, 'data': profile.to_dict(viewer=request.user)})
        except Exception as e:
            return handle_exception(e)

    @method_decorator(csrf_protect)
    @method_decorator(require_artist)
    def post(self, request):
        try:
            data = parse_json_body(request)
            validated = validate_artist_profile_create(data)
            profile = create_artist_profile(request.user, validated)
            return JsonResponse({'success': True, 'data': profile.to_dict(viewer=request.user)}, status=201)
        except Exception as e:
            return handle_exception(e)

    @method_decorator(csrf_protect)
    @method_decorator(require_artist)
    def patch(self, request):
        try:
            profile = get_artist_profile_by_user_id(request.user.id)
            data = parse_json_body(request)
            validated = validate_artist_profile_update(data)
            if not validated:
                return JsonResponse(
                    {'success': False, 'error': {'code': 'VALIDATION_ERROR', 'message': 'Khong co du lieu de cap nhat'}},
                    status=400,
                )
            profile = update_artist_profile(profile, request.user, validated)
            return JsonResponse({'success': True, 'data': profile.to_dict(viewer=request.user)})
        except Exception as e:
            return handle_exception(e)


class ArtistCoverUploadView(View):
    """POST /api/v1/artists/me/cover/ - Upload anh bia (Artist+Owner+CSRF)"""

    @method_decorator(csrf_protect)
    @method_decorator(require_artist)
    def post(self, request):
        try:
            validate_cover_image(request.FILES)
            profile = get_artist_profile_by_user_id(request.user.id)
            profile = update_cover_image(profile, request.user, request.FILES['cover_image'])
            return JsonResponse({
                'success': True,
                'data': {'cover_image': profile.cover_image.url if profile.cover_image else None},
            })
        except Exception as e:
            return handle_exception(e)


class MyArtistStatsView(View):
    """GET /api/v1/artists/me/stats/ - Thong ke cua chinh minh (Artist)"""

    @method_decorator(require_artist)
    def get(self, request):
        try:
            stats = get_artist_stats(request.user.id)
            top_songs = list_artist_top_songs(request.user.id, limit=10)
            return JsonResponse({'success': True, 'data': {**stats, 'top_songs': top_songs}})
        except Exception as e:
            return handle_exception(e)


class ArtistDetailView(View):
    """GET /api/v1/artists/<user_id>/ - Xem ho so nghe si cong khai (Public)"""

    def get(self, request, user_id):
        try:
            profile = get_artist_profile_detail(user_id, viewer=request.user)
            return JsonResponse({'success': True, 'data': profile.to_dict(viewer=request.user)})
        except Exception as e:
            return handle_exception(e)


class ArtistStatsView(View):
    """GET /api/v1/artists/<user_id>/stats/ - Thong ke cong khai cua mot nghe si (Public)"""

    def get(self, request, user_id):
        try:
            # get_artist_profile_detail tu raise ArtistProfileNotFound neu khong ton tai/bi block
            get_artist_profile_detail(user_id, viewer=request.user)
            stats = get_artist_stats(user_id)
            top_songs = list_artist_top_songs(user_id, limit=10)
            return JsonResponse({'success': True, 'data': {**stats, 'top_songs': top_songs}})
        except Exception as e:
            return handle_exception(e)
```

---

## `artists/urls.py`

```python
"""
artists/urls.py
=================
URLs cho app artists - prefix: /api/v1/artists/
"""

from django.urls import path
from artists.views import (
    ArtistListView, MyArtistProfileView, ArtistCoverUploadView,
    MyArtistStatsView, ArtistDetailView, ArtistStatsView,
)

urlpatterns = [
    path('', ArtistListView.as_view(), name='artist-list'),
    path('me/', MyArtistProfileView.as_view(), name='artist-me'),
    path('me/cover/', ArtistCoverUploadView.as_view(), name='artist-me-cover'),
    path('me/stats/', MyArtistStatsView.as_view(), name='artist-me-stats'),
    path('<uuid:user_id>/', ArtistDetailView.as_view(), name='artist-detail'),
    path('<uuid:user_id>/stats/', ArtistStatsView.as_view(), name='artist-stats'),
]
```

---

## `artists/admin.py`

```python
"""artists/admin.py"""
from django.contrib import admin
from artists.models import ArtistProfile


@admin.register(ArtistProfile)
class ArtistProfileAdmin(admin.ModelAdmin):
    list_display = ('get_display_name', 'user', 'stage_name', 'created_at')
    search_fields = ('stage_name', 'user__username')
    readonly_fields = ('created_at', 'updated_at')
```

---

## `artists/tests.py`

```python
"""
artists/tests.py
==================
Unit tests cho app artists - Tuan 4.

Chay tests:
    python manage.py test artists --verbosity=2
    python manage.py test accounts music playlists artists --verbosity=2   (toan bo)

Coverage:
  - Models:      ArtistProfile.to_dict(), get_display_name() fallback
  - Validators:  profile create/update, cover image, sanitize XSS, sanitize URL
  - Selectors:   get_artist_profile_detail (block policy), list_artists,
                 get_artist_stats (DIEM TRONG TAM: tinh dung tu nhieu bang music)
  - Services:    create/update profile, chi owner, chi role=artist
  - Views:       toan bo endpoints - HTTP status, phan quyen role=artist + owner
  - Edge cases:  block policy an profile/stats, stats = 0 khi chua co du lieu,
                 stats chi tinh tren bai PUBLISHED (khong tinh draft/hidden)
"""

import json
import uuid

from django.test import TestCase, Client
from django.core.files.uploadedfile import SimpleUploadedFile

from accounts.models import User, BlockList
from music.models import Genre, Song, Like, Rating, Comment, ListenHistory
from artists.models import ArtistProfile
from artists.validators import (
    validate_artist_profile_create, validate_artist_profile_update,
    validate_list_artists_params,
)
from artists.selectors import (
    get_artist_profile_by_user_id, get_artist_profile_detail, list_artists,
    check_profile_exists, get_artist_stats, list_artist_top_songs,
)
from artists.services import (
    create_artist_profile, update_artist_profile, get_or_create_my_profile,
)
from artists.exceptions import (
    ArtistProfileNotFound, ArtistProfileAlreadyExists, NotArtistProfileOwner, UserNotArtist,
)
from accounts.exceptions import ValidationError


# ── Helpers ───────────────────────────────────────────────────────────────────

def make_user(username, email, password='Test1234', role='user', **kwargs):
    return User.objects.create_user(username=username, email=email, password=password, role=role, **kwargs)


def make_audio_file(name=None):
    if name is None:
        name = f'{uuid.uuid4().hex}.mp3'
    return SimpleUploadedFile(name, b'\x00' * 1024, content_type='audio/mpeg')


def make_image_file(name='cover.jpg', content_type='image/jpeg', size_bytes=512):
    return SimpleUploadedFile(name, b'\x00' * size_bytes, content_type=content_type)


def make_genre(name='Pop'):
    return Genre.objects.create(name=name)


def make_song(artist, genre=None, title='Test Song', status=Song.STATUS_PUBLISHED, **kwargs):
    if genre is None:
        genre = make_genre(f'Genre-{uuid.uuid4().hex[:6]}')
    defaults = {'title': title, 'artist': artist, 'genre': genre, 'duration': 200, 'status': status, 'audio_file': make_audio_file()}
    defaults.update(kwargs)
    return Song.objects.create(**defaults)


def make_artist_profile(user, stage_name='', **kwargs):
    return ArtistProfile.objects.create(user=user, stage_name=stage_name, **kwargs)


# ═══════════════════════════════════════════════════════════════════════════════
# MODEL TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class ArtistProfileModelTest(TestCase):

    def setUp(self):
        self.artist = make_user('modelartist', 'modelartist@test.com', role='artist')

    def test_profile_creation(self):
        profile = make_artist_profile(self.artist, stage_name='DJ Test')
        self.assertEqual(profile.stage_name, 'DJ Test')
        self.assertEqual(profile.user, self.artist)

    def test_get_display_name_uses_stage_name(self):
        profile = make_artist_profile(self.artist, stage_name='Stage Name Here')
        self.assertEqual(profile.get_display_name(), 'Stage Name Here')

    def test_get_display_name_fallback_to_user(self):
        profile = make_artist_profile(self.artist, stage_name='')
        self.assertEqual(profile.get_display_name(), self.artist.get_display_name())

    def test_to_dict_basic_fields(self):
        profile = make_artist_profile(self.artist, stage_name='Dict Test', bio='Bio here')
        d = profile.to_dict()
        self.assertEqual(d['stage_name'], 'Dict Test')
        self.assertEqual(d['bio'], 'Bio here')
        self.assertEqual(d['user']['username'], self.artist.username)

    def test_to_dict_is_owner_true_for_owner(self):
        profile = make_artist_profile(self.artist)
        d = profile.to_dict(viewer=self.artist)
        self.assertTrue(d['is_owner'])

    def test_to_dict_is_owner_false_for_others(self):
        profile = make_artist_profile(self.artist)
        other = make_user('modelother', 'modelother@test.com')
        d = profile.to_dict(viewer=other)
        self.assertFalse(d['is_owner'])

    def test_one_to_one_constraint(self):
        make_artist_profile(self.artist)
        with self.assertRaises(Exception):
            ArtistProfile.objects.create(user=self.artist)


# ═══════════════════════════════════════════════════════════════════════════════
# VALIDATOR TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class ValidateArtistProfileCreateTest(TestCase):

    def test_valid_data_all_fields(self):
        result = validate_artist_profile_create({
            'stage_name': 'DJ Cool', 'bio': 'I make music',
            'website_url': 'https://example.com', 'facebook_url': '', 'youtube_url': '',
        })
        self.assertEqual(result['stage_name'], 'DJ Cool')
        self.assertEqual(result['website_url'], 'https://example.com')

    def test_empty_data_all_optional(self):
        result = validate_artist_profile_create({})
        self.assertEqual(result['stage_name'], '')
        self.assertEqual(result['bio'], '')

    def test_stage_name_too_long(self):
        with self.assertRaises(ValidationError) as ctx:
            validate_artist_profile_create({'stage_name': 'x' * 101})
        self.assertIn('stage_name', ctx.exception.fields)

    def test_bio_too_long(self):
        with self.assertRaises(ValidationError) as ctx:
            validate_artist_profile_create({'bio': 'x' * 1001})
        self.assertIn('bio', ctx.exception.fields)

    def test_stage_name_xss_sanitized(self):
        result = validate_artist_profile_create({'stage_name': '<script>alert(1)</script>DJ Cool'})
        self.assertEqual(result['stage_name'], 'DJ Cool')

    def test_bio_xss_sanitized(self):
        result = validate_artist_profile_create({'bio': '<b>bold</b>bio text'})
        self.assertEqual(result['bio'], 'boldbio text')

    def test_invalid_website_url_raises(self):
        with self.assertRaises(ValidationError) as ctx:
            validate_artist_profile_create({'website_url': 'javascript:alert(1)'})
        self.assertIn('website_url', ctx.exception.fields)

    def test_valid_facebook_url(self):
        result = validate_artist_profile_create({'facebook_url': 'https://facebook.com/test'})
        self.assertEqual(result['facebook_url'], 'https://facebook.com/test')


class ValidateArtistProfileUpdateTest(TestCase):

    def test_partial_update_stage_name_only(self):
        result = validate_artist_profile_update({'stage_name': 'New Name'})
        self.assertEqual(result, {'stage_name': 'New Name'})

    def test_no_fields_returns_empty_dict(self):
        result = validate_artist_profile_update({})
        self.assertEqual(result, {})

    def test_bio_sanitized_on_update(self):
        result = validate_artist_profile_update({'bio': '<i>x</i>updated bio'})
        self.assertEqual(result['bio'], 'xupdated bio')

    def test_invalid_youtube_url_on_update(self):
        with self.assertRaises(ValidationError) as ctx:
            validate_artist_profile_update({'youtube_url': 'not-a-url'})
        self.assertIn('youtube_url', ctx.exception.fields)


class ValidateListArtistsParamsTest(TestCase):

    def test_defaults(self):
        result = validate_list_artists_params({})
        self.assertEqual(result['page'], 1)
        self.assertEqual(result['page_size'], 20)

    def test_page_size_capped_at_100(self):
        result = validate_list_artists_params({'page_size': '999'})
        self.assertEqual(result['page_size'], 100)


# ═══════════════════════════════════════════════════════════════════════════════
# SELECTOR TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class ArtistProfileSelectorTest(TestCase):

    def setUp(self):
        self.artist = make_user('selartist', 'selartist@test.com', role='artist')
        self.viewer = make_user('selviewer', 'selviewer@test.com')

    def test_get_artist_profile_by_user_id_found(self):
        profile = make_artist_profile(self.artist)
        result = get_artist_profile_by_user_id(self.artist.id)
        self.assertEqual(result.id, profile.id)

    def test_get_artist_profile_by_user_id_not_found(self):
        with self.assertRaises(ArtistProfileNotFound):
            get_artist_profile_by_user_id(uuid.uuid4())

    def test_check_profile_exists_true(self):
        make_artist_profile(self.artist)
        self.assertTrue(check_profile_exists(self.artist.id))

    def test_check_profile_exists_false(self):
        self.assertFalse(check_profile_exists(self.artist.id))

    def test_get_artist_profile_detail_visible_to_anyone(self):
        from django.contrib.auth.models import AnonymousUser
        make_artist_profile(self.artist)
        result = get_artist_profile_detail(self.artist.id, viewer=AnonymousUser())
        self.assertEqual(result.user_id, self.artist.id)

    def test_get_artist_profile_detail_blocked_viewer_404(self):
        """Fix R10: viewer bi nghe si block -> NotFound khi xem profile."""
        make_artist_profile(self.artist)
        BlockList.objects.create(blocker=self.artist, blocked=self.viewer)
        with self.assertRaises(ArtistProfileNotFound):
            get_artist_profile_detail(self.artist.id, viewer=self.viewer)

    def test_list_artists_filter_by_query(self):
        artist2 = make_user('selartist2', 'selartist2@test.com', role='artist')
        make_artist_profile(self.artist, stage_name='Chill Master')
        make_artist_profile(artist2, stage_name='Rock Star')
        result = list_artists({'q': 'chill', 'page': 1, 'page_size': 20}, viewer=self.viewer)
        self.assertEqual(len(result['items']), 1)

    def test_list_artists_excludes_blocked(self):
        make_artist_profile(self.artist, stage_name='Blocked Artist')
        BlockList.objects.create(blocker=self.artist, blocked=self.viewer)
        result = list_artists({'page': 1, 'page_size': 20, 'q': ''}, viewer=self.viewer)
        names = [a['stage_name'] for a in result['items']]
        self.assertNotIn('Blocked Artist', names)

    def test_list_artists_pagination(self):
        for i in range(5):
            u = make_user(f'pagartist{i}', f'pagartist{i}@test.com', role='artist')
            make_artist_profile(u, stage_name=f'Artist {i}')
        result = list_artists({'page': 1, 'page_size': 2, 'q': ''}, viewer=self.viewer)
        self.assertEqual(len(result['items']), 2)
        self.assertEqual(result['pagination']['total'], 5)


class ArtistStatsSelectorTest(TestCase):
    """
    DIEM TRONG TAM cua Tuan 4: kiem tra get_artist_stats() tinh dung tu
    nhieu bang khac nhau cua app music (Song, Like, Rating, Comment, ListenHistory).
    """

    def setUp(self):
        self.artist = make_user('statsartist', 'statsartist@test.com', role='artist')
        self.genre = make_genre('StatsGenre')
        self.listener1 = make_user('listener1', 'listener1@test.com')
        self.listener2 = make_user('listener2', 'listener2@test.com')

    def test_stats_empty_when_no_songs(self):
        """Nghe si chua co bai hat nao -> tat ca stats deu = 0/None."""
        stats = get_artist_stats(self.artist.id)
        self.assertEqual(stats['total_songs'], 0)
        self.assertEqual(stats['total_play_count'], 0)
        self.assertEqual(stats['total_likes'], 0)
        self.assertEqual(stats['total_comments'], 0)
        self.assertEqual(stats['total_listeners'], 0)
        self.assertIsNone(stats['avg_rating'])
        self.assertEqual(stats['rating_count'], 0)

    def test_total_songs_counts_only_published(self):
        """Bai draft/hidden KHONG duoc tinh vao total_songs."""
        make_song(self.artist, self.genre, status=Song.STATUS_PUBLISHED, title='Pub1')
        make_song(self.artist, self.genre, status=Song.STATUS_PUBLISHED, title='Pub2')
        make_song(self.artist, self.genre, status=Song.STATUS_DRAFT, title='Draft1')
        make_song(self.artist, self.genre, status=Song.STATUS_HIDDEN, title='Hidden1')
        stats = get_artist_stats(self.artist.id)
        self.assertEqual(stats['total_songs'], 2)

    def test_total_play_count_sums_across_songs(self):
        """total_play_count phai la TONG play_count cua tat ca bai, dung Sum khong phai Count."""
        song1 = make_song(self.artist, self.genre, play_count=100)
        song2 = make_song(self.artist, self.genre, play_count=250)
        stats = get_artist_stats(self.artist.id)
        self.assertEqual(stats['total_play_count'], 350)

    def test_total_play_count_excludes_draft_songs(self):
        """play_count cua bai draft khong duoc tinh vao tong (du co play_count > 0)."""
        make_song(self.artist, self.genre, status=Song.STATUS_PUBLISHED, play_count=100)
        make_song(self.artist, self.genre, status=Song.STATUS_DRAFT, play_count=999)
        stats = get_artist_stats(self.artist.id)
        self.assertEqual(stats['total_play_count'], 100)

    def test_total_likes_across_multiple_songs(self):
        song1 = make_song(self.artist, self.genre)
        song2 = make_song(self.artist, self.genre)
        Like.objects.create(user=self.listener1, song=song1)
        Like.objects.create(user=self.listener2, song=song1)
        Like.objects.create(user=self.listener1, song=song2)
        stats = get_artist_stats(self.artist.id)
        self.assertEqual(stats['total_likes'], 3)

    def test_total_comments_excludes_hidden(self):
        song = make_song(self.artist, self.genre)
        Comment.objects.create(user=self.listener1, song=song, content='Visible 1')
        Comment.objects.create(user=self.listener1, song=song, content='Visible 2')
        Comment.objects.create(user=self.listener1, song=song, content='Hidden', is_hidden=True)
        stats = get_artist_stats(self.artist.id)
        self.assertEqual(stats['total_comments'], 2)

    def test_total_listeners_counts_unique_users(self):
        """Mot user nghe nhieu lan/nhieu bai chi tinh 1 lan trong total_listeners."""
        song1 = make_song(self.artist, self.genre)
        song2 = make_song(self.artist, self.genre)
        ListenHistory.objects.create(user=self.listener1, song=song1)
        ListenHistory.objects.create(user=self.listener1, song=song2)  # listener1 nghe 2 bai
        ListenHistory.objects.create(user=self.listener2, song=song1)
        stats = get_artist_stats(self.artist.id)
        self.assertEqual(stats['total_listeners'], 2)  # chi 2 nguoi DUY NHAT, khong phai 3

    def test_avg_rating_calculated_correctly(self):
        song1 = make_song(self.artist, self.genre)
        song2 = make_song(self.artist, self.genre)
        Rating.objects.create(user=self.listener1, song=song1, score=5)
        Rating.objects.create(user=self.listener2, song=song2, score=3)
        stats = get_artist_stats(self.artist.id)
        self.assertEqual(stats['avg_rating'], 4.0)
        self.assertEqual(stats['rating_count'], 2)

    def test_stats_isolated_per_artist(self):
        """Stats cua nghe si A khong bi anh huong boi du lieu cua nghe si B."""
        other_artist = make_user('otherstatsartist', 'otherstatsartist@test.com', role='artist')
        song_a = make_song(self.artist, self.genre, play_count=50)
        song_b = make_song(other_artist, self.genre, play_count=999)
        stats_a = get_artist_stats(self.artist.id)
        self.assertEqual(stats_a['total_play_count'], 50)

    def test_list_artist_top_songs_ordered_by_play_count(self):
        make_song(self.artist, self.genre, title='Low', play_count=10)
        make_song(self.artist, self.genre, title='High', play_count=500)
        make_song(self.artist, self.genre, title='Mid', play_count=100)
        top = list_artist_top_songs(self.artist.id, limit=10)
        titles = [s['title'] for s in top]
        self.assertEqual(titles, ['High', 'Mid', 'Low'])

    def test_list_artist_top_songs_excludes_draft(self):
        make_song(self.artist, self.genre, title='Published', status=Song.STATUS_PUBLISHED, play_count=10)
        make_song(self.artist, self.genre, title='Draft', status=Song.STATUS_DRAFT, play_count=999)
        top = list_artist_top_songs(self.artist.id, limit=10)
        titles = [s['title'] for s in top]
        self.assertEqual(titles, ['Published'])

    def test_list_artist_top_songs_respects_limit(self):
        for i in range(5):
            make_song(self.artist, self.genre, title=f'Song {i}', play_count=i * 10)
        top = list_artist_top_songs(self.artist.id, limit=3)
        self.assertEqual(len(top), 3)


# ═══════════════════════════════════════════════════════════════════════════════
# SERVICE TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class ArtistProfileServiceTest(TestCase):

    def setUp(self):
        self.artist = make_user('svcartist', 'svcartist@test.com', role='artist')
        self.regular_user = make_user('svcregular', 'svcregular@test.com', role='user')
        self.other_artist = make_user('svcother', 'svcother@test.com', role='artist')

    def test_create_profile_success(self):
        profile = create_artist_profile(self.artist, {'stage_name': 'New Artist', 'bio': ''})
        self.assertEqual(profile.user, self.artist)
        self.assertEqual(profile.stage_name, 'New Artist')

    def test_create_profile_not_artist_role_raises(self):
        """Chi role='artist' moi tao duoc ArtistProfile."""
        with self.assertRaises(UserNotArtist):
            create_artist_profile(self.regular_user, {'stage_name': 'Fake'})

    def test_create_profile_duplicate_raises(self):
        create_artist_profile(self.artist, {'stage_name': 'First'})
        with self.assertRaises(ArtistProfileAlreadyExists):
            create_artist_profile(self.artist, {'stage_name': 'Second'})

    def test_update_profile_by_owner(self):
        profile = create_artist_profile(self.artist, {'stage_name': 'Old'})
        updated = update_artist_profile(profile, self.artist, {'stage_name': 'New'})
        self.assertEqual(updated.stage_name, 'New')

    def test_update_profile_not_owner_raises(self):
        profile = create_artist_profile(self.artist, {'stage_name': 'Mine'})
        with self.assertRaises(NotArtistProfileOwner):
            update_artist_profile(profile, self.other_artist, {'stage_name': 'Hacked'})

    def test_get_or_create_my_profile_creates_if_not_exists(self):
        profile = get_or_create_my_profile(self.artist)
        self.assertEqual(profile.user, self.artist)
        self.assertTrue(check_profile_exists(self.artist.id))

    def test_get_or_create_my_profile_returns_existing(self):
        original = create_artist_profile(self.artist, {'stage_name': 'Existing'})
        fetched = get_or_create_my_profile(self.artist)
        self.assertEqual(fetched.id, original.id)
        self.assertEqual(fetched.stage_name, 'Existing')

    def test_get_or_create_my_profile_not_artist_raises(self):
        with self.assertRaises(UserNotArtist):
            get_or_create_my_profile(self.regular_user)


# ═══════════════════════════════════════════════════════════════════════════════
# VIEW TESTS (HTTP Integration)
# ═══════════════════════════════════════════════════════════════════════════════

class ArtistListViewTest(TestCase):

    def setUp(self):
        self.client = Client(enforce_csrf_checks=False)

    def test_list_artists_public_no_auth_needed(self):
        artist = make_user('listviewartist', 'listviewartist@test.com', role='artist')
        make_artist_profile(artist, stage_name='Public Artist')
        response = self.client.get('/api/v1/artists/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()['data']['items']), 1)


class MyArtistProfileViewTest(TestCase):

    def setUp(self):
        self.client = Client(enforce_csrf_checks=False)
        self.artist = make_user('mvartist', 'mvartist@test.com', role='artist')
        self.regular_user = make_user('mvregular', 'mvregular@test.com', role='user')

    def test_get_me_requires_artist_role(self):
        """User thuong (khong phai artist) bi chan voi 403 ARTIST_ONLY."""
        self.client.force_login(self.regular_user)
        response = self.client.get('/api/v1/artists/me/')
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()['error']['code'], 'ARTIST_ONLY')

    def test_get_me_requires_auth(self):
        response = self.client.get('/api/v1/artists/me/')
        self.assertEqual(response.status_code, 401)

    def test_get_me_auto_creates_profile(self):
        """Lan dau goi GET /me/ se tu tao profile rong, khong can POST truoc."""
        self.client.force_login(self.artist)
        response = self.client.get('/api/v1/artists/me/')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(check_profile_exists(self.artist.id))

    def test_post_create_profile_success(self):
        self.client.force_login(self.artist)
        response = self.client.post(
            '/api/v1/artists/me/',
            data=json.dumps({'stage_name': 'My Stage Name', 'bio': 'My bio'}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()['data']['stage_name'], 'My Stage Name')

    def test_post_create_profile_not_artist_403(self):
        self.client.force_login(self.regular_user)
        response = self.client.post(
            '/api/v1/artists/me/',
            data=json.dumps({'stage_name': 'Fake'}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 403)

    def test_post_create_duplicate_409(self):
        self.client.force_login(self.artist)
        self.client.post('/api/v1/artists/me/', data=json.dumps({'stage_name': 'First'}), content_type='application/json')
        response = self.client.post('/api/v1/artists/me/', data=json.dumps({'stage_name': 'Second'}), content_type='application/json')
        self.assertEqual(response.status_code, 409)

    def test_patch_update_profile_success(self):
        self.client.force_login(self.artist)
        self.client.post('/api/v1/artists/me/', data=json.dumps({'stage_name': 'Original'}), content_type='application/json')
        response = self.client.patch(
            '/api/v1/artists/me/',
            data=json.dumps({'stage_name': 'Updated Name'}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['data']['stage_name'], 'Updated Name')

    def test_patch_no_data_400(self):
        self.client.force_login(self.artist)
        self.client.post('/api/v1/artists/me/', data=json.dumps({}), content_type='application/json')
        response = self.client.patch('/api/v1/artists/me/', data=json.dumps({}), content_type='application/json')
        self.assertEqual(response.status_code, 400)


class ArtistCoverUploadViewTest(TestCase):

    def setUp(self):
        self.client = Client(enforce_csrf_checks=False)
        self.artist = make_user('cvartist', 'cvartist@test.com', role='artist')
        self.regular_user = make_user('cvregular', 'cvregular@test.com', role='user')

    def test_upload_cover_as_artist(self):
        self.client.force_login(self.artist)
        self.client.post('/api/v1/artists/me/', data=json.dumps({}), content_type='application/json')
        response = self.client.post('/api/v1/artists/me/cover/', data={'cover_image': make_image_file()})
        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(response.json()['data']['cover_image'])

    def test_upload_cover_not_artist_403(self):
        self.client.force_login(self.regular_user)
        response = self.client.post('/api/v1/artists/me/cover/', data={'cover_image': make_image_file()})
        self.assertEqual(response.status_code, 403)

    def test_upload_cover_invalid_mime_400(self):
        self.client.force_login(self.artist)
        self.client.post('/api/v1/artists/me/', data=json.dumps({}), content_type='application/json')
        response = self.client.post(
            '/api/v1/artists/me/cover/',
            data={'cover_image': SimpleUploadedFile('f.txt', b'data', content_type='text/plain')},
        )
        self.assertEqual(response.status_code, 400)

    def test_upload_cover_no_profile_yet_404(self):
        """Chua tao profile (GET /me/ chua duoc goi) thi upload cover phai 404."""
        self.client.force_login(self.artist)
        response = self.client.post('/api/v1/artists/me/cover/', data={'cover_image': make_image_file()})
        self.assertEqual(response.status_code, 404)


class ArtistDetailViewTest(TestCase):

    def setUp(self):
        self.client = Client(enforce_csrf_checks=False)
        self.artist = make_user('dvartist', 'dvartist@test.com', role='artist')
        self.viewer = make_user('dvviewer', 'dvviewer@test.com')

    def test_get_artist_detail_public(self):
        make_artist_profile(self.artist, stage_name='Public View')
        response = self.client.get(f'/api/v1/artists/{self.artist.id}/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['data']['stage_name'], 'Public View')

    def test_get_artist_detail_not_found(self):
        response = self.client.get(f'/api/v1/artists/{uuid.uuid4()}/')
        self.assertEqual(response.status_code, 404)

    def test_get_artist_detail_blocked_viewer_404(self):
        """Fix R10 qua HTTP: viewer bi nghe si block -> 404 khi xem trang ca nhan."""
        make_artist_profile(self.artist, stage_name='Blocker')
        BlockList.objects.create(blocker=self.artist, blocked=self.viewer)
        self.client.force_login(self.viewer)
        response = self.client.get(f'/api/v1/artists/{self.artist.id}/')
        self.assertEqual(response.status_code, 404)


class ArtistStatsViewTest(TestCase):
    """Test stats qua HTTP - dam bao endpoint cong khai va endpoint /me/ deu tra dung."""

    def setUp(self):
        self.client = Client(enforce_csrf_checks=False)
        self.artist = make_user('svartist', 'svartist@test.com', role='artist')
        self.viewer = make_user('svviewer', 'svviewer@test.com')
        self.genre = make_genre('StatsViewGenre')

    def test_my_stats_requires_artist_role(self):
        regular = make_user('svregular', 'svregular@test.com', role='user')
        self.client.force_login(regular)
        response = self.client.get('/api/v1/artists/me/stats/')
        self.assertEqual(response.status_code, 403)

    def test_my_stats_requires_auth(self):
        response = self.client.get('/api/v1/artists/me/stats/')
        self.assertEqual(response.status_code, 401)

    def test_my_stats_returns_correct_numbers(self):
        song = make_song(self.artist, self.genre, play_count=42)
        Like.objects.create(user=self.viewer, song=song)
        self.client.force_login(self.artist)
        response = self.client.get('/api/v1/artists/me/stats/')
        self.assertEqual(response.status_code, 200)
        data = response.json()['data']
        self.assertEqual(data['total_songs'], 1)
        self.assertEqual(data['total_play_count'], 42)
        self.assertEqual(data['total_likes'], 1)
        self.assertIn('top_songs', data)

    def test_public_stats_endpoint_no_auth_needed(self):
        make_artist_profile(self.artist)
        make_song(self.artist, self.genre, play_count=100)
        response = self.client.get(f'/api/v1/artists/{self.artist.id}/stats/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['data']['total_play_count'], 100)

    def test_public_stats_artist_not_found_404(self):
        response = self.client.get(f'/api/v1/artists/{uuid.uuid4()}/stats/')
        self.assertEqual(response.status_code, 404)

    def test_public_stats_blocked_viewer_404(self):
        make_artist_profile(self.artist)
        BlockList.objects.create(blocker=self.artist, blocked=self.viewer)
        self.client.force_login(self.viewer)
        response = self.client.get(f'/api/v1/artists/{self.artist.id}/stats/')
        self.assertEqual(response.status_code, 404)


# ═══════════════════════════════════════════════════════════════════════════════
# END-TO-END FLOW TEST
# ═══════════════════════════════════════════════════════════════════════════════

class EndToEndArtistFlowTest(TestCase):
    """Test toan bo luong: tao profile -> upload cover -> upload bai hat -> xem stats."""

    def setUp(self):
        self.client = Client(enforce_csrf_checks=False)
        self.artist = make_user('e2eartist', 'e2eartist@test.com', role='artist')
        self.listener = make_user('e2elistener', 'e2elistener@test.com')

    def test_full_artist_lifecycle(self):
        # 1. Artist tao ho so
        self.client.force_login(self.artist)
        r1 = self.client.post(
            '/api/v1/artists/me/',
            data=json.dumps({'stage_name': 'E2E Star', 'bio': 'E2E test artist'}),
            content_type='application/json',
        )
        self.assertEqual(r1.status_code, 201)

        # 2. Upload anh bia
        r2 = self.client.post('/api/v1/artists/me/cover/', data={'cover_image': make_image_file()})
        self.assertEqual(r2.status_code, 200)

        # 3. Xem stats - ban dau tat ca = 0
        r3 = self.client.get('/api/v1/artists/me/stats/')
        self.assertEqual(r3.json()['data']['total_songs'], 0)

        # 4. Tao bai hat va publish (qua service music truc tiep de don gian hoa test)
        genre = make_genre('E2E Genre')
        song = make_song(self.artist, genre, title='E2E Song', play_count=0)

        # 5. Listener nghe + like + rate + comment
        self.client.force_login(self.listener)
        ListenHistory.objects.create(user=self.listener, song=song)
        Like.objects.create(user=self.listener, song=song)
        Rating.objects.create(user=self.listener, song=song, score=5)
        Comment.objects.create(user=self.listener, song=song, content='Great!')
        Song.objects.filter(id=song.id).update(play_count=1)

        # 6. Xem lai stats cua artist - phai phan anh dung du lieu moi
        self.client.force_login(self.artist)
        r6 = self.client.get('/api/v1/artists/me/stats/')
        data = r6.json()['data']
        self.assertEqual(data['total_songs'], 1)
        self.assertEqual(data['total_play_count'], 1)
        self.assertEqual(data['total_likes'], 1)
        self.assertEqual(data['total_comments'], 1)
        self.assertEqual(data['total_listeners'], 1)
        self.assertEqual(data['avg_rating'], 5.0)
        self.assertEqual(len(data['top_songs']), 1)
        self.assertEqual(data['top_songs'][0]['title'], 'E2E Song')

        # 7. Nguoi khac (anonymous) xem trang nghe si cong khai - thay dung profile + stats
        self.client.logout()
        r7 = self.client.get(f'/api/v1/artists/{self.artist.id}/')
        self.assertEqual(r7.status_code, 200)
        self.assertEqual(r7.json()['data']['stage_name'], 'E2E Star')

        r8 = self.client.get(f'/api/v1/artists/{self.artist.id}/stats/')
        self.assertEqual(r8.status_code, 200)
        self.assertEqual(r8.json()['data']['total_likes'], 1)
```

---

*Tổng cộng: 10 files — 1498 dòng code, đã chạy test xác nhận PASS 100%.*
