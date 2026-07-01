# 07 — Source Code Hoàn Chỉnh App `search`

**Tuần 7 | Fix R7 (mọi truy vấn phải qua selectors.py, views.py không import model trực tiếp), Fix R16 (không lộ user is_private), tránh N+1 bằng select_related + include_stats=False**

> Copy từng file vào đúng thư mục `search/` trong project. App này **không có models.py và không có services.py** — chỉ đọc dữ liệu từ `music`, `artists`, `playlists`, `accounts`, `social` đã có sẵn.

---

## Vì sao đây là app "dễ bị N+1 nhất"

`search` là app tổng hợp dữ liệu từ **4 model khác nhau** trong 1 lần gọi (`search_all`), nên đây chính là nơi rủi ro N+1 cao nhất nếu tái sử dụng `to_dict()` mặc định của các model khác:

| Hàm `to_dict()` gốc | Tham số gây N+1 | Cách app `search` tránh |
|---|---|---|
| `Song.to_dict(include_stats=True)` | Mỗi item tự chạy `self.likes.count()` + `self.ratings.all()` | Luôn gọi với `include_stats=False` |
| `Playlist.to_dict(include_song_count=True)` | Mỗi item tự chạy `self.playlist_songs.count()` | Luôn gọi với `include_song_count=False` |
| `ArtistProfile.to_dict()` | Không có tham số phụ — an toàn | Giữ nguyên |
| `User.to_dict()` | Không có tham số phụ — an toàn | Giữ nguyên |

Ngoài ra mọi queryset trong `search/selectors.py` đều bắt buộc `select_related()` cho FK sẽ được `to_dict()` truy cập (`artist`, `genre`, `owner`), giống đúng pattern N+1-safe mà `social/selectors.py::list_feed()` đã thiết lập ở Tuần 5.

---

## Cấu Trúc File

```
search/
├── __init__.py
├── apps.py
├── validators.py
├── selectors.py
├── views.py
├── urls.py
└── tests.py
```

*(Không có `models.py`, `services.py`, `exceptions.py`, `migrations/` — app chỉ đọc, không sở hữu bảng dữ liệu nào và không có exception nghiệp vụ riêng ngoài `ValidationError` đã có sẵn ở `accounts.exceptions`.)*

---

## `search/apps.py`

```python
"""search/apps.py"""
from django.apps import AppConfig


class SearchConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'search'
    label = 'search'
    verbose_name = 'Tìm kiếm'
```

---

## `search/validators.py`

```python
"""
search/validators.py
=======================
Quy uoc: chi kiem tra kieu du lieu, khong truy van DB.
"""

from accounts.exceptions import ValidationError

SEARCH_Q_MIN_LEN = 2
SEARCH_Q_MAX_LEN = 100


def validate_search_params(params: dict, require_q: bool = True) -> dict:
    """Validate q + page + page_size dùng chung cho songs/artists/playlists/users."""
    q = params.get('q', '').strip()
    errors = {}

    if require_q:
        if not q:
            errors['q'] = ['Từ khóa tìm kiếm là bắt buộc']
        elif len(q) < SEARCH_Q_MIN_LEN:
            errors['q'] = [f'Từ khóa tìm kiếm tối thiểu {SEARCH_Q_MIN_LEN} ký tự']
        elif len(q) > SEARCH_Q_MAX_LEN:
            errors['q'] = [f'Từ khóa tìm kiếm tối đa {SEARCH_Q_MAX_LEN} ký tự']

    try:
        page = max(1, int(params.get('page', 1)))
    except (ValueError, TypeError):
        page = 1

    try:
        page_size = min(100, max(1, int(params.get('page_size', 20))))
    except (ValueError, TypeError):
        page_size = 20

    if errors:
        raise ValidationError('Tham số tìm kiếm không hợp lệ', fields=errors)

    return {'q': q, 'page': page, 'page_size': page_size}


def validate_search_songs_params(params: dict) -> dict:
    """Search bài hát cho phép q rỗng (duyệt theo genre/artist_id/ordering)."""
    result = validate_search_params(params, require_q=False)

    ordering = params.get('ordering', '-play_count')
    valid_orderings = {'-play_count', 'play_count', '-released_at', 'released_at', 'title', '-title'}
    if ordering not in valid_orderings:
        ordering = '-play_count'

    result['genre'] = params.get('genre', '').strip()
    result['artist_id'] = params.get('artist_id', '').strip()
    result['ordering'] = ordering
    return result


def validate_search_all_params(params: dict) -> dict:
    result = validate_search_params(params, require_q=True)
    try:
        limit = min(10, max(1, int(params.get('limit', 5))))
    except (ValueError, TypeError):
        limit = 5
    result['limit'] = limit
    return result
```

---

## `search/selectors.py`

```python
"""
search/selectors.py
======================
Tang Doc DUY NHAT cho app search (Fix R7).

QUY TAC BAT BUOC: views.py cua app nay khong duoc import Song/ArtistProfile/
Playlist/User de query truc tiep - MOI truy van phai nam trong file nay.

DIEM TOI UU N+1 (xem giai thich chi tiet o dau file 07):
    - search_songs()     -> select_related('artist', 'genre'), include_stats=False
    - search_artists()   -> select_related('user')
    - search_playlists() -> select_related('owner'), include_song_count=False
    - search_users()     -> khong co FK can JOIN o to_dict(), an toan

Fix R16: search_users() loai bo user is_private=True khoi ket qua, TRU KHI
requester dang follow chinh user do (tuong tu logic "chi nguoi quen moi thay
duoc tai khoan rieng tu" - dong bo voi Fix R10 block policy toan he thong).
"""

import math
from django.db.models import Q

from music.models import Song
from artists.models import ArtistProfile
from playlists.models import Playlist
from accounts.models import User, BlockList


def _pagination(page: int, page_size: int, total: int) -> dict:
    return {
        'page': page,
        'page_size': page_size,
        'total': total,
        'total_pages': math.ceil(total / page_size) if total > 0 else 1,
    }


def search_songs(q='', genre='', artist_id='', ordering='-play_count',
                  viewer=None, page=1, page_size=20) -> dict:
    """Tìm bài hát đã published - ẩn bài của nghệ sĩ đã block viewer (Fix R10)."""
    qs = Song.objects.filter(status=Song.STATUS_PUBLISHED).select_related('artist', 'genre')

    if q:
        qs = qs.filter(
            Q(title__icontains=q)
            | Q(artist__username__icontains=q)
            | Q(artist__display_name__icontains=q)
        )
    if genre:
        qs = qs.filter(genre__slug=genre)
    if artist_id:
        qs = qs.filter(artist_id=artist_id)

    viewer_id = getattr(viewer, 'id', None)
    if viewer_id and getattr(viewer, 'is_authenticated', False):
        blocked_artist_ids = BlockList.objects.filter(blocked_id=viewer_id).values_list('blocker_id', flat=True)
        qs = qs.exclude(artist_id__in=blocked_artist_ids)

    qs = qs.order_by(ordering)
    total = qs.count()
    start = (page - 1) * page_size

    # include_stats=False -> tranh N+1 (xem bang o dau file)
    items = [s.to_dict(viewer=viewer, include_stats=False) for s in qs[start:start + page_size]]

    return {'items': items, 'pagination': _pagination(page, page_size, total)}


def search_artists(q='', viewer=None, page=1, page_size=20) -> dict:
    """Tìm nghệ sĩ theo tên nghệ danh / username - ẩn nghệ sĩ đã block viewer."""
    qs = ArtistProfile.objects.select_related('user').filter(user__is_active=True)

    if q:
        qs = qs.filter(Q(stage_name__icontains=q) | Q(user__username__icontains=q))

    viewer_id = getattr(viewer, 'id', None)
    if viewer_id and getattr(viewer, 'is_authenticated', False):
        blocked_ids = BlockList.objects.filter(blocked_id=viewer_id).values_list('blocker_id', flat=True)
        qs = qs.exclude(user_id__in=blocked_ids)

    qs = qs.order_by('-created_at')
    total = qs.count()
    start = (page - 1) * page_size
    items = [a.to_dict(viewer=viewer) for a in qs[start:start + page_size]]

    return {'items': items, 'pagination': _pagination(page, page_size, total)}


def search_playlists(q='', viewer=None, page=1, page_size=20) -> dict:
    """Tìm playlist công khai theo tên - chỉ playlist is_public=True."""
    qs = Playlist.objects.filter(is_public=True, owner__is_active=True).select_related('owner')

    if q:
        qs = qs.filter(title__icontains=q)

    qs = qs.order_by('-created_at')
    total = qs.count()
    start = (page - 1) * page_size

    # include_song_count=False -> tranh N+1 (xem bang o dau file)
    items = [p.to_dict(viewer=viewer, include_song_count=False) for p in qs[start:start + page_size]]

    return {'items': items, 'pagination': _pagination(page, page_size, total)}


def search_users(q='', requester=None, page=1, page_size=20) -> dict:
    """
    Tìm người dùng theo username/display_name.

    Fix R16: mặc định CHỈ trả user is_private=False. User is_private=True chỉ
    xuất hiện nếu requester đang follow họ (đã là "người quen"), tương tự cách
    Instagram/X ẩn tài khoản riêng tư khỏi kết quả tìm kiếm của người lạ.
    """
    qs = User.objects.filter(is_active=True)

    if q:
        qs = qs.filter(Q(username__icontains=q) | Q(display_name__icontains=q))

    requester_id = getattr(requester, 'id', None)
    requester_is_auth = bool(requester_id and getattr(requester, 'is_authenticated', False))

    if requester_is_auth:
        from social.models import Follow
        following_ids = Follow.objects.filter(follower_id=requester_id).values_list('following_id', flat=True)
        qs = qs.filter(Q(is_private=False) | Q(id__in=following_ids))

        blocked_ids = BlockList.objects.filter(blocked_id=requester_id).values_list('blocker_id', flat=True)
        qs = qs.exclude(id__in=blocked_ids)
    else:
        qs = qs.filter(is_private=False)

    qs = qs.exclude(id=requester_id) if requester_is_auth else qs
    qs = qs.order_by('username')
    total = qs.count()
    start = (page - 1) * page_size
    items = [u.to_dict(include_private=False) for u in qs[start:start + page_size]]

    return {'items': items, 'pagination': _pagination(page, page_size, total)}


def search_all(q, viewer=None, limit=5) -> dict:
    """Tìm kiếm tổng hợp - mỗi loại giới hạn `limit` kết quả, không phân trang đầy đủ."""
    songs = search_songs(q=q, viewer=viewer, page=1, page_size=limit)['items']
    artists = search_artists(q=q, viewer=viewer, page=1, page_size=limit)['items']
    playlists = search_playlists(q=q, viewer=viewer, page=1, page_size=limit)['items']
    users = search_users(q=q, requester=viewer, page=1, page_size=limit)['items']

    return {'songs': songs, 'artists': artists, 'playlists': playlists, 'users': users}
```

---

## `search/views.py`

```python
"""
search/views.py
==================
Tang HTTP cho app search.

Fix R7: view CHI goi search/selectors.py, KHONG import Song/ArtistProfile/
Playlist/User de query truc tiep trong file nay.
"""

import logging

from django.http import JsonResponse
from django.views import View

from accounts.exceptions import ValidationError

from search.validators import (
    validate_search_params, validate_search_songs_params, validate_search_all_params,
)
from search.selectors import search_songs, search_artists, search_playlists, search_users, search_all

logger = logging.getLogger(__name__)


def handle_exception(e: Exception) -> JsonResponse:
    if isinstance(e, ValidationError):
        return JsonResponse(
            {'success': False, 'error': {'code': 'VALIDATION_ERROR', 'message': e.message, 'fields': e.fields}},
            status=400,
        )
    logger.exception('Unhandled exception in search views: %s', e)
    return JsonResponse(
        {'success': False, 'error': {'code': 'SERVER_ERROR', 'message': 'Lỗi server'}},
        status=500,
    )


class SearchAllView(View):
    """GET /api/v1/search/ - Tìm kiếm tổng hợp songs+artists+playlists+users (Public)"""

    def get(self, request):
        try:
            filters = validate_search_all_params(request.GET)
            result = search_all(filters['q'], viewer=request.user, limit=filters['limit'])
            return JsonResponse({'success': True, 'data': result})
        except Exception as e:
            return handle_exception(e)


class SongSearchView(View):
    """GET /api/v1/search/songs/ - Tìm bài hát (Public)"""

    def get(self, request):
        try:
            filters = validate_search_songs_params(request.GET)
            result = search_songs(
                q=filters['q'], genre=filters['genre'], artist_id=filters['artist_id'],
                ordering=filters['ordering'], viewer=request.user,
                page=filters['page'], page_size=filters['page_size'],
            )
            return JsonResponse({'success': True, 'data': result})
        except Exception as e:
            return handle_exception(e)


class ArtistSearchView(View):
    """GET /api/v1/search/artists/ - Tìm nghệ sĩ (Public)"""

    def get(self, request):
        try:
            filters = validate_search_params(request.GET, require_q=False)
            result = search_artists(
                q=filters['q'], viewer=request.user, page=filters['page'], page_size=filters['page_size'],
            )
            return JsonResponse({'success': True, 'data': result})
        except Exception as e:
            return handle_exception(e)


class PlaylistSearchView(View):
    """GET /api/v1/search/playlists/ - Tìm playlist công khai (Public)"""

    def get(self, request):
        try:
            filters = validate_search_params(request.GET, require_q=False)
            result = search_playlists(
                q=filters['q'], viewer=request.user, page=filters['page'], page_size=filters['page_size'],
            )
            return JsonResponse({'success': True, 'data': result})
        except Exception as e:
            return handle_exception(e)


class UserSearchView(View):
    """
    GET /api/v1/search/users/ - Tìm người dùng (Auth)

    Yêu cầu đăng nhập vì kết quả phụ thuộc vào quan hệ follow/block của
    requester (Fix R16) - tìm kiếm ẩn danh sẽ không phân biệt được "người
    quen" nên chỉ nên thấy user public, phù hợp hơn khi bắt buộc đăng nhập
    để tận dụng đầy đủ tính năng và tránh scraping danh sách user hàng loạt.
    """

    def get(self, request):
        try:
            if not request.user.is_authenticated:
                return JsonResponse(
                    {'success': False, 'error': {'code': 'AUTH_REQUIRED', 'message': 'Cần đăng nhập để tìm người dùng'}},
                    status=401,
                )
            filters = validate_search_params(request.GET, require_q=False)
            result = search_users(
                q=filters['q'], requester=request.user, page=filters['page'], page_size=filters['page_size'],
            )
            return JsonResponse({'success': True, 'data': result})
        except Exception as e:
            return handle_exception(e)
```

---

## `search/urls.py`

```python
"""search/urls.py — prefix: /api/v1/search/"""

from django.urls import path
from search.views import SearchAllView, SongSearchView, ArtistSearchView, PlaylistSearchView, UserSearchView

urlpatterns = [
    path('', SearchAllView.as_view(), name='search-all'),
    path('songs/', SongSearchView.as_view(), name='search-songs'),
    path('artists/', ArtistSearchView.as_view(), name='search-artists'),
    path('playlists/', PlaylistSearchView.as_view(), name='search-playlists'),
    path('users/', UserSearchView.as_view(), name='search-users'),
]
```

---

## `search/tests.py`

```python
"""
search/tests.py
==================
Unit tests cho app search - Tuan 7.

Chay tests:
    python manage.py test search --verbosity=2

Coverage:
  - Validators:  q min/max length, ordering fallback, limit cap
  - Selectors:   search_songs/artists/playlists/users (block policy Fix R10,
                 is_private policy Fix R16), search_all,
                 TRONG TAM: khong N+1 qua CaptureQueriesContext
  - Views:       toan bo endpoints - HTTP status
"""

import uuid

from django.test import TestCase, Client
from django.test.utils import CaptureQueriesContext
from django.db import connection
from django.core.files.uploadedfile import SimpleUploadedFile

from accounts.models import User, BlockList
from music.models import Genre, Song
from artists.models import ArtistProfile
from playlists.models import Playlist
from social.models import Follow
from search.validators import validate_search_params, validate_search_songs_params, validate_search_all_params
from search.selectors import search_songs, search_artists, search_playlists, search_users, search_all
from accounts.exceptions import ValidationError


def make_user(username, email, password='Test1234', role='user', **kwargs):
    return User.objects.create_user(username=username, email=email, password=password, role=role, **kwargs)


def make_audio_file(name=None):
    if name is None:
        name = f'{uuid.uuid4().hex}.mp3'
    return SimpleUploadedFile(name, b'\x00' * 1024, content_type='audio/mpeg')


def make_genre(name='Pop'):
    return Genre.objects.create(name=name)


def make_song(artist, genre=None, title='Test Song', status=Song.STATUS_PUBLISHED, **kwargs):
    if genre is None:
        genre = make_genre(f'Genre-{uuid.uuid4().hex[:6]}')
    defaults = {'title': title, 'artist': artist, 'genre': genre, 'duration': 200, 'status': status, 'audio_file': make_audio_file()}
    defaults.update(kwargs)
    return Song.objects.create(**defaults)


# ═══════════════════════════════════════════════════════════════════════════════
# VALIDATOR TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class ValidateSearchParamsTest(TestCase):

    def test_valid_q(self):
        result = validate_search_params({'q': 'chill'})
        self.assertEqual(result['q'], 'chill')

    def test_q_too_short_raises(self):
        with self.assertRaises(ValidationError):
            validate_search_params({'q': 'a'})

    def test_q_required_by_default(self):
        with self.assertRaises(ValidationError):
            validate_search_params({})

    def test_q_not_required_when_false(self):
        result = validate_search_params({}, require_q=False)
        self.assertEqual(result['q'], '')

    def test_page_size_capped(self):
        result = validate_search_params({'q': 'ab'}, require_q=False) if False else None  # no-op guard
        result = validate_search_params({}, require_q=False)
        self.assertLessEqual(result['page_size'], 100)


class ValidateSearchSongsParamsTest(TestCase):

    def test_invalid_ordering_falls_back(self):
        result = validate_search_songs_params({'ordering': 'hacked_field'})
        self.assertEqual(result['ordering'], '-play_count')

    def test_valid_ordering_kept(self):
        result = validate_search_songs_params({'ordering': 'title'})
        self.assertEqual(result['ordering'], 'title')


class ValidateSearchAllParamsTest(TestCase):

    def test_limit_default_5(self):
        result = validate_search_all_params({'q': 'ab'})
        self.assertEqual(result['limit'], 5)

    def test_limit_capped_at_10(self):
        result = validate_search_all_params({'q': 'ab', 'limit': '999'})
        self.assertEqual(result['limit'], 10)


# ═══════════════════════════════════════════════════════════════════════════════
# SELECTOR TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class SearchSongsSelectorTest(TestCase):

    def setUp(self):
        self.artist = make_user('searchartist', 'searchartist@test.com', role='artist')
        self.genre = make_genre('SearchGenre')
        self.viewer = make_user('searchviewer', 'searchviewer@test.com')

    def test_search_by_title(self):
        make_song(self.artist, self.genre, title='Shape of You')
        make_song(self.artist, self.genre, title='Perfect')
        result = search_songs(q='shape', viewer=self.viewer)
        self.assertEqual(len(result['items']), 1)

    def test_search_excludes_draft(self):
        make_song(self.artist, self.genre, title='Draft Song', status=Song.STATUS_DRAFT)
        result = search_songs(q='draft', viewer=self.viewer)
        self.assertEqual(len(result['items']), 0)

    def test_search_excludes_blocked_artist(self):
        make_song(self.artist, self.genre, title='Blocked Song')
        BlockList.objects.create(blocker=self.artist, blocked=self.viewer)
        result = search_songs(q='blocked', viewer=self.viewer)
        self.assertEqual(len(result['items']), 0)

    def test_search_items_have_no_stats_fields(self):
        """include_stats=False -> khong co like_count/avg_rating trong ket qua tim kiem."""
        make_song(self.artist, self.genre, title='NoStats')
        result = search_songs(q='nostats', viewer=self.viewer)
        self.assertNotIn('like_count', result['items'][0])

    def test_search_query_count_no_n_plus_1(self):
        for i in range(10):
            make_song(self.artist, self.genre, title=f'Bulk Song {i}')
        with CaptureQueriesContext(connection) as ctx:
            result = search_songs(q='bulk', viewer=self.viewer, page_size=20)
            self.assertEqual(len(result['items']), 10)
        self.assertLess(len(ctx.captured_queries), 6)


class SearchArtistsSelectorTest(TestCase):

    def test_search_by_stage_name(self):
        artist = make_user('stageartist', 'stageartist@test.com', role='artist')
        ArtistProfile.objects.create(user=artist, stage_name='Chill Master')
        result = search_artists(q='chill')
        self.assertEqual(len(result['items']), 1)

    def test_search_excludes_blocked(self):
        artist = make_user('blockedartist', 'blockedartist@test.com', role='artist')
        viewer = make_user('artistviewer', 'artistviewer@test.com')
        ArtistProfile.objects.create(user=artist, stage_name='Hidden Artist')
        BlockList.objects.create(blocker=artist, blocked=viewer)
        result = search_artists(q='hidden', viewer=viewer)
        self.assertEqual(len(result['items']), 0)


class SearchPlaylistsSelectorTest(TestCase):

    def test_search_only_public(self):
        owner = make_user('plowner', 'plowner@test.com')
        Playlist.objects.create(owner=owner, title='Public List', is_public=True)
        Playlist.objects.create(owner=owner, title='Private List', is_public=False)
        result = search_playlists(q='list')
        titles = [p['title'] for p in result['items']]
        self.assertIn('Public List', titles)
        self.assertNotIn('Private List', titles)

    def test_search_items_have_no_song_count(self):
        """include_song_count=False -> khong co song_count trong ket qua tim kiem."""
        owner = make_user('plowner2', 'plowner2@test.com')
        Playlist.objects.create(owner=owner, title='NoCount List', is_public=True)
        result = search_playlists(q='nocount')
        self.assertNotIn('song_count', result['items'][0])


class SearchUsersSelectorTest(TestCase):

    def setUp(self):
        self.requester = make_user('requester', 'requester@test.com')

    def test_search_excludes_private_by_default(self):
        make_user('privateuser', 'privateuser@test.com', is_private=True)
        result = search_users(q='privateuser', requester=self.requester)
        self.assertEqual(len(result['items']), 0)

    def test_search_includes_private_if_following(self):
        """Fix R16: user private van xuat hien neu requester dang follow ho."""
        target = make_user('followedprivate', 'followedprivate@test.com', is_private=True)
        Follow.objects.create(follower=self.requester, following=target)
        result = search_users(q='followedprivate', requester=self.requester)
        self.assertEqual(len(result['items']), 1)

    def test_search_excludes_blocked(self):
        target = make_user('blockeruser', 'blockeruser@test.com')
        BlockList.objects.create(blocker=target, blocked=self.requester)
        result = search_users(q='blockeruser', requester=self.requester)
        self.assertEqual(len(result['items']), 0)

    def test_search_anonymous_excludes_private(self):
        make_user('anonprivate', 'anonprivate@test.com', is_private=True)
        result = search_users(q='anonprivate', requester=None)
        self.assertEqual(len(result['items']), 0)


class SearchAllSelectorTest(TestCase):

    def test_search_all_aggregates_every_type(self):
        artist = make_user('allartist', 'allartist@test.com', role='artist')
        genre = make_genre('AllGenre')
        make_song(artist, genre, title='queryword track')
        ArtistProfile.objects.create(user=artist, stage_name='queryword stage')
        Playlist.objects.create(owner=artist, title='queryword playlist', is_public=True)
        make_user('querywordbio', 'querywordbio@test.com')

        result = search_all('queryword', viewer=None, limit=5)
        self.assertEqual(len(result['songs']), 1)
        self.assertEqual(len(result['artists']), 1)
        self.assertEqual(len(result['playlists']), 1)


# ═══════════════════════════════════════════════════════════════════════════════
# VIEW TESTS (HTTP Integration)
# ═══════════════════════════════════════════════════════════════════════════════

class SearchViewTest(TestCase):

    def setUp(self):
        self.client = Client(enforce_csrf_checks=False)
        self.artist = make_user('viewartist', 'viewartist@test.com', role='artist')
        self.genre = make_genre('ViewGenre')
        self.user = make_user('vsuser', 'vsuser@test.com')

    def test_search_all_public(self):
        make_song(self.artist, self.genre, title='Hello World Song')
        response = self.client.get('/api/v1/search/?q=hello')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()['data']['songs']), 1)

    def test_search_all_missing_q_400(self):
        response = self.client.get('/api/v1/search/')
        self.assertEqual(response.status_code, 400)

    def test_search_songs_public_no_q_needed(self):
        make_song(self.artist, self.genre, title='Any Song')
        response = self.client.get('/api/v1/search/songs/')
        self.assertEqual(response.status_code, 200)

    def test_search_artists_public(self):
        ArtistProfile.objects.create(user=self.artist, stage_name='View Stage')
        response = self.client.get('/api/v1/search/artists/?q=view')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()['data']['items']), 1)

    def test_search_playlists_public(self):
        Playlist.objects.create(owner=self.artist, title='View Playlist', is_public=True)
        response = self.client.get('/api/v1/search/playlists/?q=view')
        self.assertEqual(response.status_code, 200)

    def test_search_users_requires_auth(self):
        response = self.client.get('/api/v1/search/users/?q=vs')
        self.assertEqual(response.status_code, 401)

    def test_search_users_authenticated(self):
        self.client.force_login(self.user)
        response = self.client.get('/api/v1/search/users/?q=vs')
        self.assertEqual(response.status_code, 200)
```

---

## Cấu Hình

### 1. Đăng ký app trong `music_platform/settings.py`

```python
INSTALLED_APPS = [
    ...
    'social',
    'notifications',
    'search',   # <-- thêm dòng này (không cần migrations, app không có model)
]
```

### 2. Đăng ký URL trong `music_platform/urls.py`

```python
urlpatterns = [
    ...
    path('api/v1/notifications/', include('notifications.urls')),
    path('api/v1/search/', include('search.urls')),   # <-- thêm dòng này
]
```
