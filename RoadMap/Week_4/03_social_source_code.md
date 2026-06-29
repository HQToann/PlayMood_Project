# 03 — Source Code Hoàn Chỉnh App `social`

**Tuần 5 | Đã verify: 79/79 tests pass riêng app này, 171/171 tests pass toàn hệ thống**

> Copy từng file vào đúng thư mục `social/` trong project.
> Sau khi copy xong, xem file `05_social_configs_and_db_changes.md` để biết các bước apply.

---

## Cấu Trúc File

```
social/
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

## `social/apps.py`

```python
"""social/apps.py"""
from django.apps import AppConfig


class SocialConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'social'
    label = 'social'
    verbose_name = 'Xa hoi'
```

---

## `social/models.py`

```python
"""
social/models.py
==================
Models cho app social:
  - Follow:          Quan he theo doi giua 2 User
  - Mood:             Trang thai tam trang hien tai cua User, co the gan kem bai hat
  - FriendActivity:   Log hoat dong (nghe nhac, like, mood...) de hien thi Feed

Tat ca PK la UUIDField theo quy uoc chung cua he thong.
"""

import uuid
from django.db import models
from django.utils import timezone


class Follow(models.Model):
    """
    Quan he theo doi - follower theo doi following.

    unique_together dam bao 1 cap follower-following chi co 1 ban ghi
    (giong pattern BlockList o accounts/models.py Tuan 1).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    follower = models.ForeignKey(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='following',          # user.following.all() = nhung nguoi user dang theo doi
        verbose_name='Nguoi theo doi',
    )
    following = models.ForeignKey(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='followers',          # user.followers.all() = nhung nguoi dang theo doi user
        verbose_name='Nguoi duoc theo doi',
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Ngay theo doi')

    class Meta:
        db_table = 'social_follow'
        unique_together = [('follower', 'following')]
        ordering = ['-created_at']
        verbose_name = 'Theo doi'
        verbose_name_plural = 'Theo doi'

    def __str__(self):
        return f'{self.follower.username} -> follow -> {self.following.username}'


class Mood(models.Model):
    """
    Trang thai tam trang hien tai cua User - co the gan kem 1 bai hat dang the hien cam xuc.

    Business rule quan trong:
        - Moi User chi co 1 Mood "dang hien thi" tai 1 thoi diem (OneToOneField)
        - Mood co the het han (expires_at) - Mood da het han duoc coi nhu khong con hien thi
        - Cap nhat Mood moi se UPSERT (update_or_create), khong tao nhieu ban ghi rac
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    user = models.OneToOneField(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='mood',
        verbose_name='Nguoi dung',
    )

    status_text = models.CharField(max_length=200, blank=True, default='', verbose_name='Trang thai')

    # Bai hat gan kem Mood - tuy chon, co the null neu chi viet status_text
    song = models.ForeignKey(
        'music.Song',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='moods',
        verbose_name='Bai hat dinh kem',
    )

    expires_at = models.DateTimeField(verbose_name='Het han luc')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Ngay tao')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Cap nhat lan cuoi')

    class Meta:
        db_table = 'social_mood'
        ordering = ['-updated_at']
        verbose_name = 'Tam trang'
        verbose_name_plural = 'Tam trang'

    def __str__(self):
        return f'{self.user.username}: {self.status_text[:30]}'

    def is_expired(self) -> bool:
        """Kiem tra Mood da het han hay chua."""
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
            'status_text': self.status_text,
            'song': {
                'id': str(self.song_id),
                'title': self.song.title,
                'artist_display_name': self.song.artist.get_display_name(),
                'cover_image': self.song.cover_image.url if self.song.cover_image else None,
            } if self.song_id else None,
            'expires_at': self.expires_at.isoformat(),
            'is_expired': self.is_expired(),
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
        }


class FriendActivity(models.Model):
    """
    Log hoat dong cua User - dung de hien thi Feed cho nhung nguoi follow ho.

    activity_type xac dinh loai hoat dong:
        - 'playing':  vua nghe mot bai hat (duoc ghi tu music/services.py::record_play())
        - 'liked':    vua like mot bai hat
        - 'mood':     vua cap nhat Mood moi

    song la FK tuy chon - chi co gia tri voi activity_type='playing'/'liked',
    activity_type='mood' co the khong gan song (neu Mood khong dinh kem bai hat).
    """

    TYPE_PLAYING = 'playing'
    TYPE_LIKED = 'liked'
    TYPE_MOOD = 'mood'
    TYPE_CHOICES = [
        (TYPE_PLAYING, 'Dang nghe'),
        (TYPE_LIKED, 'Da thich'),
        (TYPE_MOOD, 'Cap nhat tam trang'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    user = models.ForeignKey(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='friend_activities',
        verbose_name='Nguoi dung',
        db_index=True,
    )
    activity_type = models.CharField(max_length=10, choices=TYPE_CHOICES, db_index=True)

    song = models.ForeignKey(
        'music.Song',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='friend_activities',
        verbose_name='Bai hat lien quan',
    )

    # Luu lai status_text cua Mood tai thoi diem tao activity (Mood co the bi sua/xoa sau)
    extra_text = models.CharField(max_length=200, blank=True, default='', verbose_name='Noi dung bo sung')

    created_at = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='Thoi diem')

    class Meta:
        db_table = 'social_friend_activity'
        ordering = ['-created_at']
        verbose_name = 'Hoat dong ban be'
        verbose_name_plural = 'Hoat dong ban be'
        indexes = [
            # Composite index ho tro query Feed: lay hoat dong cua nhieu user, sap xep theo thoi gian
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
```

---

## `social/exceptions.py`

```python
"""
social/exceptions.py
=======================
Custom exceptions cho nghiep vu app social.
"""

from accounts.exceptions import AppException


class CannotFollowSelf(AppException):
    """Khong the tu follow ban than - HTTP 400."""
    def __init__(self, message='Ban khong the tu theo doi ban than'):
        super().__init__(message, error_code='VALIDATION_ERROR')


class FollowTargetNotFound(AppException):
    """User muon follow khong ton tai - HTTP 404."""
    def __init__(self, message='Nguoi dung khong ton tai'):
        super().__init__(message, error_code='NOT_FOUND')


class BlockedFollowError(AppException):
    """Khong the follow do bi block (2 chieu) - HTTP 403."""
    def __init__(self, message='Ban khong the thuc hien hanh dong nay'):
        super().__init__(message, error_code='BLOCKED')


class MoodNotFound(AppException):
    """User chua co Mood nao - HTTP 404."""
    def __init__(self, message='Ban chua co tam trang nao duoc thiet lap'):
        super().__init__(message, error_code='NOT_FOUND')
```

---

## `social/validators.py`

```python
"""
social/validators.py
=======================
Kiem tra du lieu dau vao cho app social.

Quy uoc (giu nguyen tu Tuan 1-4):
  - CHI kiem tra kieu du lieu, bat buoc, do dai, format
  - KHONG goi service, KHONG truy van DB
  - KHONG raise HTTP exception - chi raise ValidationError tu accounts.exceptions
  - Moi text public phai qua sanitize_text() (Fix R12)
"""

import uuid
from datetime import timedelta
from django.utils import timezone
from music_platform.sanitize import sanitize_text
from accounts.exceptions import ValidationError

STATUS_TEXT_MAX = 200

# Thoi gian song toi thieu/toi da cho mot Mood, tinh bang gio
MOOD_MIN_DURATION_HOURS = 1
MOOD_MAX_DURATION_HOURS = 168  # 7 ngay
MOOD_DEFAULT_DURATION_HOURS = 24


def validate_set_mood(data: dict) -> dict:
    """
    Validate du lieu thiet lap Mood moi.

    Kỳ vọng: { "status_text": "...", "song_id": "uuid" (optional),
               "duration_hours": 24 (optional, mac dinh 24h) }

    expires_at duoc TINH TOAN o day tu duration_hours, KHONG nhan truc tiep
    tu client de tranh client gui ngay trong qua khu/qua xa tuong lai.
    """
    errors = {}

    status_text = data.get('status_text', '').strip()
    if not status_text:
        errors['status_text'] = ['Trang thai la bat buoc']
    elif len(status_text) > STATUS_TEXT_MAX:
        errors['status_text'] = [f'Trang thai toi da {STATUS_TEXT_MAX} ky tu']

    song_id = data.get('song_id', None)
    if song_id:
        try:
            song_id = uuid.UUID(str(song_id))
        except (ValueError, AttributeError):
            errors['song_id'] = ['song_id khong dung dinh dang UUID']
    else:
        song_id = None

    duration_hours = data.get('duration_hours', MOOD_DEFAULT_DURATION_HOURS)
    try:
        duration_hours = int(duration_hours)
        if not (MOOD_MIN_DURATION_HOURS <= duration_hours <= MOOD_MAX_DURATION_HOURS):
            errors['duration_hours'] = [
                f'Thoi gian hien thi phai tu {MOOD_MIN_DURATION_HOURS} den {MOOD_MAX_DURATION_HOURS} gio'
            ]
    except (ValueError, TypeError):
        errors['duration_hours'] = ['Thoi gian hien thi phai la so nguyen (gio)']
        duration_hours = MOOD_DEFAULT_DURATION_HOURS

    if errors:
        raise ValidationError('Du lieu tam trang khong hop le', fields=errors)

    return {
        'status_text': sanitize_text(status_text),
        'song_id': song_id,
        'expires_at': timezone.now() + timedelta(hours=duration_hours),
    }


def validate_list_feed_params(params: dict) -> dict:
    """Validate va lam sach query params khi lay Feed."""
    try:
        page = max(1, int(params.get('page', 1)))
    except (ValueError, TypeError):
        page = 1

    try:
        page_size = min(100, max(1, int(params.get('page_size', 20))))
    except (ValueError, TypeError):
        page_size = 20

    return {'page': page, 'page_size': page_size}


def validate_list_follow_params(params: dict) -> dict:
    """Validate va lam sach query params khi list followers/following."""
    try:
        page = max(1, int(params.get('page', 1)))
    except (ValueError, TypeError):
        page = 1

    try:
        page_size = min(100, max(1, int(params.get('page_size', 20))))
    except (ValueError, TypeError):
        page_size = 20

    return {'page': page, 'page_size': page_size}
```

---

## `social/selectors.py`

```python
"""
social/selectors.py
======================
Tang Doc cho app social - moi truy van DB chi duoc viet o day.

Quy uoc (giu nguyen tu Tuan 1-4):
  - CHI doc du lieu, KHONG ghi
  - Prefix ham: get_*, list_*, count_*, is_*, check_*
  - KHONG raise HTTP exception (raise custom exception nghiep vu neu can)

Diem ky thuat quan trong nhat cua app nay: list_feed() phai toi uu truy van
bang select_related/prefetch_related de tranh N+1 query - moi FriendActivity
can load: user (1 query), song + song.artist (1 query) - neu khong toi uu,
voi N hoat dong se phat sinh them N*2 query rieng le.
"""

import math
from django.db.models import Q

from social.models import Follow, Mood, FriendActivity
from social.exceptions import MoodNotFound
from accounts.selectors import is_blocked


# ── Follow ────────────────────────────────────────────────────────────────────

def is_following(follower_id, following_id) -> bool:
    """Kiem tra follower_id co dang theo doi following_id hay khong."""
    return Follow.objects.filter(follower_id=follower_id, following_id=following_id).exists()


def get_follow_counts(user_id) -> dict:
    """Tra so luong followers va following cua mot user."""
    return {
        'followers_count': Follow.objects.filter(following_id=user_id).count(),
        'following_count': Follow.objects.filter(follower_id=user_id).count(),
    }


def list_followers(user_id, viewer=None, page=1, page_size=20) -> dict:
    """
    Danh sach nguoi dang theo doi user_id (followers).

    An nguoi da block viewer (Fix R10), tuong tu pattern da dung
    o list_songs()/list_artists() cac tuan truoc.
    """
    qs = Follow.objects.filter(following_id=user_id).select_related('follower')

    viewer_id = getattr(viewer, 'id', None)
    viewer_is_auth = bool(viewer_id and getattr(viewer, 'is_authenticated', False))
    if viewer_is_auth:
        from accounts.models import BlockList
        blocked_ids = BlockList.objects.filter(blocked_id=viewer_id).values_list('blocker_id', flat=True)
        qs = qs.exclude(follower_id__in=blocked_ids)

    qs = qs.order_by('-created_at')
    total = qs.count()
    start = (page - 1) * page_size
    items = []
    for f in qs[start:start + page_size]:
        u = f.follower
        items.append({
            'id': str(u.id), 'username': u.username,
            'display_name': u.get_display_name(),
            'avatar': u.avatar.url if u.avatar else None,
            'followed_at': f.created_at.isoformat(),
        })

    return {
        'items': items,
        'pagination': {'page': page, 'page_size': page_size, 'total': total, 'total_pages': math.ceil(total / page_size) if total > 0 else 1},
    }


def list_following(user_id, viewer=None, page=1, page_size=20) -> dict:
    """Danh sach nguoi user_id dang theo doi (following)."""
    qs = Follow.objects.filter(follower_id=user_id).select_related('following')

    viewer_id = getattr(viewer, 'id', None)
    viewer_is_auth = bool(viewer_id and getattr(viewer, 'is_authenticated', False))
    if viewer_is_auth:
        from accounts.models import BlockList
        blocked_ids = BlockList.objects.filter(blocked_id=viewer_id).values_list('blocker_id', flat=True)
        qs = qs.exclude(following_id__in=blocked_ids)

    qs = qs.order_by('-created_at')
    total = qs.count()
    start = (page - 1) * page_size
    items = []
    for f in qs[start:start + page_size]:
        u = f.following
        items.append({
            'id': str(u.id), 'username': u.username,
            'display_name': u.get_display_name(),
            'avatar': u.avatar.url if u.avatar else None,
            'followed_at': f.created_at.isoformat(),
        })

    return {
        'items': items,
        'pagination': {'page': page, 'page_size': page_size, 'total': total, 'total_pages': math.ceil(total / page_size) if total > 0 else 1},
    }


# ── Mood ──────────────────────────────────────────────────────────────────────

def get_my_mood(user) -> Mood:
    """
    Lay Mood hien tai cua chinh user.

    Raises:
        MoodNotFound: neu user chua tung thiet lap Mood
    """
    try:
        return Mood.objects.select_related('user', 'song', 'song__artist').get(user=user)
    except Mood.DoesNotExist:
        raise MoodNotFound()


def get_user_mood(user_id, viewer=None) -> Mood | None:
    """
    Lay Mood cong khai cua mot user (de hien thi tren profile).

    Tra None neu: chua co Mood, Mood da het han, hoac viewer bi user block (Fix R10).
    KHONG raise exception - Mood la thong tin phu, khong co thi tra None de
    client tu xu ly hien thi (vd: an khoi UI) thay vi bao loi.
    """
    viewer_id = getattr(viewer, 'id', None)
    viewer_is_auth = bool(viewer_id and getattr(viewer, 'is_authenticated', False))
    if viewer_is_auth and is_blocked(viewer_id, user_id):
        return None

    mood = Mood.objects.select_related('user', 'song', 'song__artist').filter(user_id=user_id).first()
    if mood is None or mood.is_expired():
        return None
    return mood


# ── FriendActivity / Feed ─────────────────────────────────────────────────────

def list_feed(user, page=1, page_size=20) -> dict:
    """
    Lay Feed hoat dong cua nhung nguoi user dang theo doi (following).

    DIEM TOI UU QUAN TRONG NHAT cua app nay:
    Dung select_related('user', 'song', 'song__artist') de JOIN san trong
    1 query SQL duy nhat, tranh N+1 query khi serialize tung activity.to_dict()
    (moi to_dict() truy cap .user, .song, .song.artist - neu khong select_related,
    Django se chay rieng 1 query cho moi truong nay, voi N activity se la 3*N query).

    Logic gom nhom/sap xep:
        - Chi lay hoat dong cua nhung nguoi user DANG theo doi (qua Follow)
        - KHONG gom nhom theo user hay theo loai - hien thi dang timeline don gian,
          sap xep giam dan theo created_at (hoat dong moi nhat len dau)
        - An hoat dong cua nguoi da block user (Fix R10) - dam bao tinh nhat quan
          2 chieu voi block policy da ap dung o accounts/music/playlists/artists

    Args:
        user: User dang xem feed (chinh nguoi goi request)
        page, page_size: phan trang chuan

    Returns:
        dict gom 'items' (list) va 'pagination' (dict)
    """
    following_ids = Follow.objects.filter(follower=user).values_list('following_id', flat=True)

    # Loai tru hoat dong cua nguoi da block user (Fix R10)
    from accounts.models import BlockList
    blocked_ids = BlockList.objects.filter(blocked_id=user.id).values_list('blocker_id', flat=True)

    qs = (
        FriendActivity.objects
        .filter(user_id__in=following_ids)
        .exclude(user_id__in=blocked_ids)
        .select_related('user', 'song', 'song__artist')   # <-- toi uu N+1, JOIN 1 lan
        .order_by('-created_at')
    )

    total = qs.count()
    start = (page - 1) * page_size
    items = [a.to_dict() for a in qs[start:start + page_size]]

    return {
        'items': items,
        'pagination': {'page': page, 'page_size': page_size, 'total': total, 'total_pages': math.ceil(total / page_size) if total > 0 else 1},
    }


def list_my_activities(user, page=1, page_size=20) -> dict:
    """Lay lich su hoat dong cua chinh user (dung cho trang profile ca nhan)."""
    qs = (
        FriendActivity.objects
        .filter(user=user)
        .select_related('user', 'song', 'song__artist')
        .order_by('-created_at')
    )
    total = qs.count()
    start = (page - 1) * page_size
    items = [a.to_dict() for a in qs[start:start + page_size]]
    return {
        'items': items,
        'pagination': {'page': page, 'page_size': page_size, 'total': total, 'total_pages': math.ceil(total / page_size) if total > 0 else 1},
    }
```

---

## `social/services.py`

```python
"""
social/services.py
=====================
Tang Ghi cho app social - moi logic Create/Update/Delete o day.

Quy uoc (giu nguyen tu Tuan 1-4):
  - Xu ly toan bo business logic ghi du lieu
  - KHONG tra HTTP response
  - Co the goi selectors de doc, nhung selectors khong goi nguoc lai

QUAN TRONG: create_friend_activity() duoc music/services.py::record_play()
goi truc tiep tu Tuan 2 (boc trong try/except). Signature ham nay PHAI giu
nguyen: create_friend_activity(user, activity_type, song=None, extra_text='')
- doi signature se lam vo luong ghi log khi nghe nhac o app music.
"""

import logging

from accounts.models import User
from music.models import Song
from social.models import Follow, Mood, FriendActivity
from social.selectors import is_following, get_my_mood
from social.exceptions import CannotFollowSelf, FollowTargetNotFound, BlockedFollowError
from accounts.exceptions import NotFound
from accounts.selectors import is_blocked

logger = logging.getLogger(__name__)


# ── Follow ────────────────────────────────────────────────────────────────────

def toggle_follow(follower: User, following_id) -> dict:
    """
    Toggle follow/unfollow.

    Business rules:
        - Khong the tu follow ban than
        - User bi target block khong duoc follow (Fix R10)
        - Target khong ton tai -> FollowTargetNotFound

    Returns:
        dict gom action ('followed'|'unfollowed') va followers_count cua target
    """
    if str(follower.id) == str(following_id):
        raise CannotFollowSelf()

    try:
        following = User.objects.get(id=following_id, is_active=True)
    except User.DoesNotExist:
        raise FollowTargetNotFound()

    if is_blocked(viewer_id=follower.id, target_id=following.id):
        raise BlockedFollowError()

    follow_record, created = Follow.objects.get_or_create(follower=follower, following=following)

    if not created:
        follow_record.delete()
        action = 'unfollowed'
    else:
        action = 'followed'
        # Ghi FriendActivity khong block luong chinh neu loi (giong pattern record_play)
        try:
            create_friend_activity(user=follower, activity_type=FriendActivity.TYPE_LIKED, extra_text=f'Da theo doi {following.get_display_name()}')
        except Exception as e:
            logger.debug('FriendActivity log skipped on follow: %s', e)

    followers_count = Follow.objects.filter(following=following).count()
    return {'action': action, 'followers_count': followers_count, 'target_user_id': str(following_id)}


# ── Mood ──────────────────────────────────────────────────────────────────────

def set_mood(user: User, data: dict) -> Mood:
    """
    Thiet lap/cap nhat Mood cua user - UPSERT (update_or_create).

    Moi user chi co 1 Mood "dang hien thi" - goi lai se thay the Mood cu
    (khong tao ban ghi moi rieng, khong tich luy lich su Mood).

    Sau khi set, ghi 1 FriendActivity loai 'mood' de hien thi tren Feed.
    """
    song = None
    if data.get('song_id'):
        try:
            song = Song.objects.get(id=data['song_id'])
        except Song.DoesNotExist:
            raise NotFound('Bai hat khong ton tai')

    mood, _created = Mood.objects.update_or_create(
        user=user,
        defaults={
            'status_text': data['status_text'],
            'song': song,
            'expires_at': data['expires_at'],
        },
    )

    try:
        create_friend_activity(
            user=user,
            activity_type=FriendActivity.TYPE_MOOD,
            song=song,
            extra_text=data['status_text'],
        )
    except Exception as e:
        logger.debug('FriendActivity log skipped on mood update: %s', e)

    logger.info('Mood updated: user=%s', user.username)
    return mood


def delete_mood(user: User) -> None:
    """Xoa Mood hien tai cua user (vd: muon an trang thai truoc khi het han tu nhien)."""
    Mood.objects.filter(user=user).delete()
    logger.info('Mood deleted: user=%s', user.username)


# ── FriendActivity ────────────────────────────────────────────────────────────

def create_friend_activity(user, activity_type: str, song=None, extra_text: str = '') -> FriendActivity:
    """
    Tao 1 ban ghi FriendActivity moi.

    QUAN TRONG: Day la entrypoint duy nhat duoc music/services.py::record_play()
    goi tu Tuan 2 (qua try/except, khong lam vo luong play nhac neu app social
    chua ton tai/loi). Signature nay la HOP DONG (contract) giua 2 app - khong
    doi ten tham so neu khong muon sua lai ca music/services.py.

    Args:
        user:          User thuc hien hanh dong
        activity_type: 'playing' | 'liked' | 'mood' (xem FriendActivity.TYPE_CHOICES)
        song:          Song lien quan (optional, None cho mood khong gan bai hat)
        extra_text:    Noi dung bo sung (vd: status_text cua mood)
    """
    activity = FriendActivity.objects.create(
        user=user,
        activity_type=activity_type,
        song=song,
        extra_text=extra_text,
    )
    return activity
```

---

## `social/views.py`

```python
"""
social/views.py
==================
Tang HTTP cho app social.

Quy uoc (giu nguyen tu Tuan 1-4):
  - views.py KHONG import Follow, Mood, FriendActivity... de query truc tiep
  - Moi query qua selectors.py, moi ghi qua services.py
  - Exception tu services/selectors duoc map sang HTTP status qua handle_exception()
"""

import json
import logging

from django.http import JsonResponse
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect

from accounts.decorators import require_auth
from accounts.exceptions import ValidationError, PermissionDenied, NotFound, AlreadyExists

from social.exceptions import CannotFollowSelf, FollowTargetNotFound, BlockedFollowError, MoodNotFound
from social.validators import validate_set_mood, validate_list_feed_params, validate_list_follow_params
from social.selectors import (
    is_following, get_follow_counts, list_followers, list_following,
    get_my_mood, get_user_mood, list_feed, list_my_activities,
)
from social.services import toggle_follow, set_mood, delete_mood

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
    if isinstance(e, CannotFollowSelf):
        return JsonResponse(
            {'success': False, 'error': {'code': e.error_code, 'message': e.message}},
            status=400,
        )
    if isinstance(e, (BlockedFollowError, PermissionDenied)):
        return JsonResponse(
            {'success': False, 'error': {'code': e.error_code, 'message': e.message}},
            status=403,
        )
    if isinstance(e, (FollowTargetNotFound, MoodNotFound, NotFound)):
        return JsonResponse(
            {'success': False, 'error': {'code': 'NOT_FOUND', 'message': e.message}},
            status=404,
        )
    if isinstance(e, AlreadyExists):
        return JsonResponse(
            {'success': False, 'error': {'code': 'ALREADY_EXISTS', 'message': e.message}},
            status=409,
        )
    logger.exception('Unhandled exception in social views: %s', e)
    return JsonResponse(
        {'success': False, 'error': {'code': 'SERVER_ERROR', 'message': 'Loi server'}},
        status=500,
    )


# ── Follow Views ──────────────────────────────────────────────────────────────

class FollowToggleView(View):
    """POST /api/v1/social/users/<user_id>/follow/ - Toggle follow/unfollow (Auth+CSRF)"""

    @method_decorator(csrf_protect)
    @method_decorator(require_auth)
    def post(self, request, user_id):
        try:
            result = toggle_follow(request.user, user_id)
            return JsonResponse({'success': True, 'data': result})
        except Exception as e:
            return handle_exception(e)


class FollowStatusView(View):
    """GET /api/v1/social/users/<user_id>/follow-status/ - Trang thai follow + so luong (Public)"""

    def get(self, request, user_id):
        try:
            counts = get_follow_counts(user_id)
            viewer_id = getattr(request.user, 'id', None)
            am_following = False
            if viewer_id and getattr(request.user, 'is_authenticated', False):
                am_following = is_following(viewer_id, user_id)
            return JsonResponse({'success': True, 'data': {**counts, 'is_following': am_following}})
        except Exception as e:
            return handle_exception(e)


class FollowersListView(View):
    """GET /api/v1/social/users/<user_id>/followers/ - Danh sach followers (Public)"""

    def get(self, request, user_id):
        try:
            filters = validate_list_follow_params(request.GET)
            result = list_followers(user_id, viewer=request.user, page=filters['page'], page_size=filters['page_size'])
            return JsonResponse({'success': True, 'data': result})
        except Exception as e:
            return handle_exception(e)


class FollowingListView(View):
    """GET /api/v1/social/users/<user_id>/following/ - Danh sach following (Public)"""

    def get(self, request, user_id):
        try:
            filters = validate_list_follow_params(request.GET)
            result = list_following(user_id, viewer=request.user, page=filters['page'], page_size=filters['page_size'])
            return JsonResponse({'success': True, 'data': result})
        except Exception as e:
            return handle_exception(e)


# ── Mood Views ────────────────────────────────────────────────────────────────

class MyMoodView(View):
    """
    GET    /api/v1/social/me/mood/ - Xem mood hien tai cua toi (Auth)
    POST   /api/v1/social/me/mood/ - Thiet lap/cap nhat mood (Auth+CSRF)
    DELETE /api/v1/social/me/mood/ - Xoa mood hien tai (Auth+CSRF)
    """

    @method_decorator(require_auth)
    def get(self, request):
        try:
            mood = get_my_mood(request.user)
            return JsonResponse({'success': True, 'data': mood.to_dict()})
        except Exception as e:
            return handle_exception(e)

    @method_decorator(csrf_protect)
    @method_decorator(require_auth)
    def post(self, request):
        try:
            data = parse_json_body(request)
            validated = validate_set_mood(data)
            mood = set_mood(request.user, validated)
            return JsonResponse({'success': True, 'data': mood.to_dict()}, status=201)
        except Exception as e:
            return handle_exception(e)

    @method_decorator(csrf_protect)
    @method_decorator(require_auth)
    def delete(self, request):
        try:
            delete_mood(request.user)
            return JsonResponse({'success': True}, status=204)
        except Exception as e:
            return handle_exception(e)


class UserMoodView(View):
    """GET /api/v1/social/users/<user_id>/mood/ - Xem mood cong khai cua mot user (Public)"""

    def get(self, request, user_id):
        try:
            mood = get_user_mood(user_id, viewer=request.user)
            return JsonResponse({'success': True, 'data': mood.to_dict() if mood else None})
        except Exception as e:
            return handle_exception(e)


# ── Feed Views ────────────────────────────────────────────────────────────────

class FeedView(View):
    """GET /api/v1/social/feed/ - Bang tin hoat dong cua nhung nguoi toi theo doi (Auth)"""

    @method_decorator(require_auth)
    def get(self, request):
        try:
            filters = validate_list_feed_params(request.GET)
            result = list_feed(request.user, page=filters['page'], page_size=filters['page_size'])
            return JsonResponse({'success': True, 'data': result})
        except Exception as e:
            return handle_exception(e)


class MyActivitiesView(View):
    """GET /api/v1/social/me/activities/ - Lich su hoat dong cua chinh toi (Auth)"""

    @method_decorator(require_auth)
    def get(self, request):
        try:
            filters = validate_list_feed_params(request.GET)
            result = list_my_activities(request.user, page=filters['page'], page_size=filters['page_size'])
            return JsonResponse({'success': True, 'data': result})
        except Exception as e:
            return handle_exception(e)
```

---

## `social/urls.py`

```python
"""
social/urls.py
=================
URLs cho app social - prefix: /api/v1/social/
"""

from django.urls import path
from social.views import (
    FollowToggleView, FollowStatusView, FollowersListView, FollowingListView,
    MyMoodView, UserMoodView, FeedView, MyActivitiesView,
)

urlpatterns = [
    path('users/<uuid:user_id>/follow/', FollowToggleView.as_view(), name='social-follow-toggle'),
    path('users/<uuid:user_id>/follow-status/', FollowStatusView.as_view(), name='social-follow-status'),
    path('users/<uuid:user_id>/followers/', FollowersListView.as_view(), name='social-followers'),
    path('users/<uuid:user_id>/following/', FollowingListView.as_view(), name='social-following'),

    path('me/mood/', MyMoodView.as_view(), name='social-my-mood'),
    path('users/<uuid:user_id>/mood/', UserMoodView.as_view(), name='social-user-mood'),

    path('feed/', FeedView.as_view(), name='social-feed'),
    path('me/activities/', MyActivitiesView.as_view(), name='social-my-activities'),
]
```

---

## `social/admin.py`

```python
"""social/admin.py"""
from django.contrib import admin
from social.models import Follow, Mood, FriendActivity


@admin.register(Follow)
class FollowAdmin(admin.ModelAdmin):
    list_display = ('follower', 'following', 'created_at')
    search_fields = ('follower__username', 'following__username')


@admin.register(Mood)
class MoodAdmin(admin.ModelAdmin):
    list_display = ('user', 'status_text', 'song', 'expires_at', 'updated_at')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(FriendActivity)
class FriendActivityAdmin(admin.ModelAdmin):
    list_display = ('user', 'activity_type', 'song', 'created_at')
    list_filter = ('activity_type',)
```

---

## `social/tests.py`

```python
"""
social/tests.py
==================
Unit tests cho app social - Tuan 5.

Chay tests:
    python manage.py test social --verbosity=2
    python manage.py test accounts music playlists artists social --verbosity=2

Coverage:
  - Models:      Follow unique_together, Mood.is_expired(), FriendActivity.to_dict()
  - Validators:  set_mood (duration_hours, song_id, sanitize XSS), feed params
  - Selectors:   is_following, list_feed (TRONG TAM: N+1 optimization + dung luong),
                 get_user_mood (block policy + expired)
  - Services:    toggle_follow (self-follow, block, ghi activity),
                 set_mood (upsert), create_friend_activity (signature hop dong voi music app)
  - Views:       toan bo endpoints - HTTP status, phan quyen Auth
  - E2E:         A follow B -> B nghe nhac -> A thay hoat dong trong Feed
"""

import json
import uuid
from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase, Client
from django.test.utils import CaptureQueriesContext
from django.db import connection
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone

from accounts.models import User, BlockList
from music.models import Genre, Song
from music.services import record_play
from social.models import Follow, Mood, FriendActivity
from social.validators import validate_set_mood, validate_list_feed_params
from social.selectors import (
    is_following, get_follow_counts, list_followers, list_following,
    get_my_mood, get_user_mood, list_feed, list_my_activities,
)
from social.services import toggle_follow, set_mood, delete_mood, create_friend_activity
from social.exceptions import CannotFollowSelf, FollowTargetNotFound, BlockedFollowError, MoodNotFound
from accounts.exceptions import ValidationError, NotFound


# ── Helpers ───────────────────────────────────────────────────────────────────

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
# MODEL TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class FollowModelTest(TestCase):

    def setUp(self):
        self.alice = make_user('modelalice', 'modelalice@test.com')
        self.bob = make_user('modelbob', 'modelbob@test.com')

    def test_follow_creation(self):
        f = Follow.objects.create(follower=self.alice, following=self.bob)
        self.assertEqual(f.follower, self.alice)
        self.assertEqual(f.following, self.bob)

    def test_unique_together_prevents_duplicate(self):
        Follow.objects.create(follower=self.alice, following=self.bob)
        with self.assertRaises(Exception):
            Follow.objects.create(follower=self.alice, following=self.bob)

    def test_related_names_correct(self):
        Follow.objects.create(follower=self.alice, following=self.bob)
        self.assertEqual(self.alice.following.count(), 1)
        self.assertEqual(self.bob.followers.count(), 1)


class MoodModelTest(TestCase):

    def setUp(self):
        self.user = make_user('moodmodeluser', 'moodmodeluser@test.com')

    def test_mood_creation(self):
        mood = Mood.objects.create(
            user=self.user, status_text='Happy', expires_at=timezone.now() + timedelta(hours=24)
        )
        self.assertEqual(mood.status_text, 'Happy')

    def test_is_expired_false_for_future(self):
        mood = Mood.objects.create(
            user=self.user, status_text='X', expires_at=timezone.now() + timedelta(hours=1)
        )
        self.assertFalse(mood.is_expired())

    def test_is_expired_true_for_past(self):
        mood = Mood.objects.create(
            user=self.user, status_text='X', expires_at=timezone.now() - timedelta(hours=1)
        )
        self.assertTrue(mood.is_expired())

    def test_one_to_one_constraint(self):
        Mood.objects.create(user=self.user, status_text='First', expires_at=timezone.now() + timedelta(hours=1))
        with self.assertRaises(Exception):
            Mood.objects.create(user=self.user, status_text='Second', expires_at=timezone.now() + timedelta(hours=1))

    def test_to_dict_without_song(self):
        mood = Mood.objects.create(user=self.user, status_text='No song', expires_at=timezone.now() + timedelta(hours=1))
        d = mood.to_dict()
        self.assertIsNone(d['song'])
        self.assertEqual(d['status_text'], 'No song')

    def test_to_dict_with_song(self):
        artist = make_user('moodmodelartist', 'moodmodelartist@test.com', role='artist')
        song = make_song(artist, title='Mood Song')
        mood = Mood.objects.create(user=self.user, status_text='Listening', song=song, expires_at=timezone.now() + timedelta(hours=1))
        d = mood.to_dict()
        self.assertEqual(d['song']['title'], 'Mood Song')


class FriendActivityModelTest(TestCase):

    def setUp(self):
        self.user = make_user('factmodeluser', 'factmodeluser@test.com')

    def test_to_dict_without_song(self):
        activity = FriendActivity.objects.create(user=self.user, activity_type=FriendActivity.TYPE_MOOD, extra_text='Happy day')
        d = activity.to_dict()
        self.assertIsNone(d['song'])
        self.assertEqual(d['activity_type'], 'mood')

    def test_to_dict_with_song(self):
        artist = make_user('factmodelartist', 'factmodelartist@test.com', role='artist')
        song = make_song(artist, title='Activity Song')
        activity = FriendActivity.objects.create(user=self.user, activity_type=FriendActivity.TYPE_PLAYING, song=song)
        d = activity.to_dict()
        self.assertEqual(d['song']['title'], 'Activity Song')


# ═══════════════════════════════════════════════════════════════════════════════
# VALIDATOR TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class ValidateSetMoodTest(TestCase):

    def test_valid_data_minimal(self):
        result = validate_set_mood({'status_text': 'Feeling good'})
        self.assertEqual(result['status_text'], 'Feeling good')
        self.assertIsNone(result['song_id'])
        self.assertIsNotNone(result['expires_at'])

    def test_missing_status_text_raises(self):
        with self.assertRaises(ValidationError) as ctx:
            validate_set_mood({})
        self.assertIn('status_text', ctx.exception.fields)

    def test_status_text_too_long(self):
        with self.assertRaises(ValidationError) as ctx:
            validate_set_mood({'status_text': 'x' * 201})
        self.assertIn('status_text', ctx.exception.fields)

    def test_status_text_xss_sanitized(self):
        result = validate_set_mood({'status_text': '<script>alert(1)</script>Happy'})
        self.assertEqual(result['status_text'], 'Happy')

    def test_valid_song_id(self):
        sid = str(uuid.uuid4())
        result = validate_set_mood({'status_text': 'Listening', 'song_id': sid})
        self.assertEqual(str(result['song_id']), sid)

    def test_invalid_song_id_format(self):
        with self.assertRaises(ValidationError) as ctx:
            validate_set_mood({'status_text': 'X', 'song_id': 'not-a-uuid'})
        self.assertIn('song_id', ctx.exception.fields)

    def test_duration_hours_default_24(self):
        result = validate_set_mood({'status_text': 'X'})
        expected = timezone.now() + timedelta(hours=24)
        self.assertAlmostEqual(result['expires_at'], expected, delta=timedelta(seconds=5))

    def test_duration_hours_custom(self):
        result = validate_set_mood({'status_text': 'X', 'duration_hours': 2})
        expected = timezone.now() + timedelta(hours=2)
        self.assertAlmostEqual(result['expires_at'], expected, delta=timedelta(seconds=5))

    def test_duration_hours_out_of_range_raises(self):
        with self.assertRaises(ValidationError) as ctx:
            validate_set_mood({'status_text': 'X', 'duration_hours': 9999})
        self.assertIn('duration_hours', ctx.exception.fields)

    def test_duration_hours_zero_raises(self):
        with self.assertRaises(ValidationError) as ctx:
            validate_set_mood({'status_text': 'X', 'duration_hours': 0})
        self.assertIn('duration_hours', ctx.exception.fields)


class ValidateListFeedParamsTest(TestCase):

    def test_defaults(self):
        result = validate_list_feed_params({})
        self.assertEqual(result['page'], 1)
        self.assertEqual(result['page_size'], 20)

    def test_page_size_capped_at_100(self):
        result = validate_list_feed_params({'page_size': '500'})
        self.assertEqual(result['page_size'], 100)


# ═══════════════════════════════════════════════════════════════════════════════
# SELECTOR TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class FollowSelectorTest(TestCase):

    def setUp(self):
        self.alice = make_user('selalice', 'selalice@test.com')
        self.bob = make_user('selbob', 'selbob@test.com')

    def test_is_following_true(self):
        Follow.objects.create(follower=self.alice, following=self.bob)
        self.assertTrue(is_following(self.alice.id, self.bob.id))

    def test_is_following_false(self):
        self.assertFalse(is_following(self.alice.id, self.bob.id))

    def test_get_follow_counts(self):
        Follow.objects.create(follower=self.alice, following=self.bob)
        counts = get_follow_counts(self.bob.id)
        self.assertEqual(counts['followers_count'], 1)
        self.assertEqual(counts['following_count'], 0)

    def test_list_followers_excludes_blocked(self):
        Follow.objects.create(follower=self.alice, following=self.bob)
        BlockList.objects.create(blocker=self.alice, blocked=self.bob)
        # Bob bi block boi Alice -> Bob xem followers cua minh khong thay Alice
        result = list_followers(self.bob.id, viewer=self.bob)
        usernames = [f['username'] for f in result['items']]
        self.assertNotIn('selalice', usernames)

    def test_list_following_pagination(self):
        for i in range(5):
            u = make_user(f'selfollowee{i}', f'selfollowee{i}@test.com')
            Follow.objects.create(follower=self.alice, following=u)
        result = list_following(self.alice.id, viewer=self.alice, page=1, page_size=2)
        self.assertEqual(len(result['items']), 2)
        self.assertEqual(result['pagination']['total'], 5)


class MoodSelectorTest(TestCase):

    def setUp(self):
        self.user = make_user('moodselusr', 'moodselusr@test.com')
        self.viewer = make_user('moodselviewer', 'moodselviewer@test.com')

    def test_get_my_mood_not_found_raises(self):
        with self.assertRaises(MoodNotFound):
            get_my_mood(self.user)

    def test_get_my_mood_found(self):
        Mood.objects.create(user=self.user, status_text='Happy', expires_at=timezone.now() + timedelta(hours=1))
        mood = get_my_mood(self.user)
        self.assertEqual(mood.status_text, 'Happy')

    def test_get_user_mood_none_if_not_set(self):
        result = get_user_mood(self.user.id, viewer=self.viewer)
        self.assertIsNone(result)

    def test_get_user_mood_none_if_expired(self):
        Mood.objects.create(user=self.user, status_text='Old', expires_at=timezone.now() - timedelta(hours=1))
        result = get_user_mood(self.user.id, viewer=self.viewer)
        self.assertIsNone(result)

    def test_get_user_mood_returns_active(self):
        Mood.objects.create(user=self.user, status_text='Active', expires_at=timezone.now() + timedelta(hours=1))
        result = get_user_mood(self.user.id, viewer=self.viewer)
        self.assertIsNotNone(result)
        self.assertEqual(result.status_text, 'Active')

    def test_get_user_mood_blocked_returns_none(self):
        """Fix R10: viewer bi user block -> khong xem duoc mood (tra None, khong raise)."""
        Mood.objects.create(user=self.user, status_text='Hidden', expires_at=timezone.now() + timedelta(hours=1))
        BlockList.objects.create(blocker=self.user, blocked=self.viewer)
        result = get_user_mood(self.user.id, viewer=self.viewer)
        self.assertIsNone(result)


class FeedSelectorTest(TestCase):
    """DIEM TRONG TAM cua Tuan 5: list_feed() phai dung va toi uu N+1 query."""

    def setUp(self):
        self.alice = make_user('feedalice', 'feedalice@test.com')
        self.bob = make_user('feedbob', 'feedbob@test.com')
        self.charlie = make_user('feedcharlie', 'feedcharlie@test.com')
        self.artist = make_user('feedartist', 'feedartist@test.com', role='artist')
        self.genre = make_genre('FeedGenre')

    def test_feed_empty_when_not_following_anyone(self):
        result = list_feed(self.alice, page=1, page_size=20)
        self.assertEqual(result['items'], [])

    def test_feed_shows_activity_of_followed_user(self):
        """LUONG CHINH: A follow B -> B co hoat dong -> A thay trong Feed."""
        Follow.objects.create(follower=self.alice, following=self.bob)
        create_friend_activity(user=self.bob, activity_type=FriendActivity.TYPE_MOOD, extra_text='Bob is happy')

        result = list_feed(self.alice, page=1, page_size=20)
        self.assertEqual(len(result['items']), 1)
        self.assertEqual(result['items'][0]['user']['username'], 'feedbob')

    def test_feed_excludes_activity_of_non_followed_user(self):
        """A khong follow Charlie -> hoat dong cua Charlie khong xuat hien trong Feed cua A."""
        create_friend_activity(user=self.charlie, activity_type=FriendActivity.TYPE_MOOD, extra_text='Charlie mood')
        result = list_feed(self.alice, page=1, page_size=20)
        self.assertEqual(result['items'], [])

    def test_feed_excludes_own_activity(self):
        """Feed chi hien thi hoat dong cua NGUOI KHAC (following), khong hien hoat dong cua chinh minh."""
        create_friend_activity(user=self.alice, activity_type=FriendActivity.TYPE_MOOD, extra_text='My own mood')
        result = list_feed(self.alice, page=1, page_size=20)
        self.assertEqual(result['items'], [])

    def test_feed_excludes_blocked_user_activity(self):
        """Fix R10: A follow B nhung B da block A -> hoat dong cua B khong hien trong Feed cua A."""
        Follow.objects.create(follower=self.alice, following=self.bob)
        BlockList.objects.create(blocker=self.bob, blocked=self.alice)
        create_friend_activity(user=self.bob, activity_type=FriendActivity.TYPE_MOOD, extra_text='Hidden from blocked')
        result = list_feed(self.alice, page=1, page_size=20)
        self.assertEqual(result['items'], [])

    def test_feed_sorted_newest_first(self):
        Follow.objects.create(follower=self.alice, following=self.bob)
        a1 = create_friend_activity(user=self.bob, activity_type=FriendActivity.TYPE_MOOD, extra_text='First')
        a2 = create_friend_activity(user=self.bob, activity_type=FriendActivity.TYPE_MOOD, extra_text='Second')
        result = list_feed(self.alice, page=1, page_size=20)
        self.assertEqual(result['items'][0]['extra_text'], 'Second')
        self.assertEqual(result['items'][1]['extra_text'], 'First')

    def test_feed_aggregates_multiple_followed_users(self):
        """Feed gop hoat dong tu NHIEU nguoi dang follow, sap xep chung theo thoi gian."""
        Follow.objects.create(follower=self.alice, following=self.bob)
        Follow.objects.create(follower=self.alice, following=self.charlie)
        create_friend_activity(user=self.bob, activity_type=FriendActivity.TYPE_MOOD, extra_text='Bob activity')
        create_friend_activity(user=self.charlie, activity_type=FriendActivity.TYPE_MOOD, extra_text='Charlie activity')
        result = list_feed(self.alice, page=1, page_size=20)
        self.assertEqual(len(result['items']), 2)

    def test_feed_includes_song_data_when_present(self):
        Follow.objects.create(follower=self.alice, following=self.bob)
        song = make_song(self.artist, self.genre, title='Feed Song')
        create_friend_activity(user=self.bob, activity_type=FriendActivity.TYPE_PLAYING, song=song)
        result = list_feed(self.alice, page=1, page_size=20)
        self.assertEqual(result['items'][0]['song']['title'], 'Feed Song')

    def test_feed_pagination(self):
        Follow.objects.create(follower=self.alice, following=self.bob)
        for i in range(5):
            create_friend_activity(user=self.bob, activity_type=FriendActivity.TYPE_MOOD, extra_text=f'Activity {i}')
        result = list_feed(self.alice, page=1, page_size=2)
        self.assertEqual(len(result['items']), 2)
        self.assertEqual(result['pagination']['total'], 5)
        self.assertEqual(result['pagination']['total_pages'], 3)

    def test_feed_query_count_no_n_plus_1(self):
        """
        DIEM TOI UU QUAN TRONG NHAT: verify list_feed() KHONG phat sinh N+1 query.

        Tao 10 hoat dong tu 10 nguoi khac nhau (deu co bai hat dinh kem),
        sau do dem so query SQL thuc te khi goi list_feed(). Voi select_related
        dung cach, so query phai ON DINH (khong tang theo so luong activity).
        """
        followees = []
        for i in range(10):
            u = make_user(f'n1followee{i}', f'n1followee{i}@test.com', role='artist')
            Follow.objects.create(follower=self.alice, following=u)
            song = make_song(u, self.genre, title=f'N1 Song {i}')
            create_friend_activity(user=u, activity_type=FriendActivity.TYPE_PLAYING, song=song)
            followees.append(u)

        with CaptureQueriesContext(connection) as ctx:
            result = list_feed(self.alice, page=1, page_size=20)
            # Buoc serialize toan bo items (vao to_dict() de cham vao .user/.song/.song.artist)
            self.assertEqual(len(result['items']), 10)

        query_count = len(ctx.captured_queries)
        # Voi select_related dung: ~3-5 query co dinh (follow ids, blocked ids, count, JOIN chinh)
        # KHONG duoc ti le voi so luong activity (neu loi N+1 se la hang chuc query)
        self.assertLess(query_count, 10, f'Qua nhieu query ({query_count}) - co the dang bi N+1, kiem tra select_related')


class MyActivitiesSelectorTest(TestCase):

    def setUp(self):
        self.user = make_user('myactuser', 'myactuser@test.com')

    def test_list_my_activities_only_own(self):
        other = make_user('myactother', 'myactother@test.com')
        create_friend_activity(user=self.user, activity_type=FriendActivity.TYPE_MOOD, extra_text='Mine')
        create_friend_activity(user=other, activity_type=FriendActivity.TYPE_MOOD, extra_text='Not mine')
        result = list_my_activities(self.user, page=1, page_size=20)
        self.assertEqual(len(result['items']), 1)
        self.assertEqual(result['items'][0]['extra_text'], 'Mine')


# ═══════════════════════════════════════════════════════════════════════════════
# SERVICE TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class ToggleFollowServiceTest(TestCase):

    def setUp(self):
        self.alice = make_user('svcalice', 'svcalice@test.com')
        self.bob = make_user('svcbob', 'svcbob@test.com')

    def test_follow_first_time(self):
        result = toggle_follow(self.alice, self.bob.id)
        self.assertEqual(result['action'], 'followed')
        self.assertTrue(Follow.objects.filter(follower=self.alice, following=self.bob).exists())

    def test_unfollow_second_time(self):
        toggle_follow(self.alice, self.bob.id)
        result = toggle_follow(self.alice, self.bob.id)
        self.assertEqual(result['action'], 'unfollowed')
        self.assertFalse(Follow.objects.filter(follower=self.alice, following=self.bob).exists())

    def test_cannot_follow_self(self):
        with self.assertRaises(CannotFollowSelf):
            toggle_follow(self.alice, self.alice.id)

    def test_follow_nonexistent_user_raises(self):
        with self.assertRaises(FollowTargetNotFound):
            toggle_follow(self.alice, uuid.uuid4())

    def test_follow_blocked_user_raises(self):
        """Fix R10: A bi Bob block -> A khong the follow Bob."""
        BlockList.objects.create(blocker=self.bob, blocked=self.alice)
        with self.assertRaises(BlockedFollowError):
            toggle_follow(self.alice, self.bob.id)

    def test_follow_creates_friend_activity(self):
        toggle_follow(self.alice, self.bob.id)
        self.assertTrue(FriendActivity.objects.filter(user=self.alice).exists())

    def test_followers_count_updates(self):
        toggle_follow(self.alice, self.bob.id)
        result = toggle_follow(make_user('svccharlie', 'svccharlie@test.com'), self.bob.id)
        self.assertEqual(result['followers_count'], 2)


class SetMoodServiceTest(TestCase):

    def setUp(self):
        self.user = make_user('moodsvcuser', 'moodsvcuser@test.com')
        self.artist = make_user('moodsvcartist', 'moodsvcartist@test.com', role='artist')

    def test_set_mood_first_time(self):
        data = {'status_text': 'Happy', 'song_id': None, 'expires_at': timezone.now() + timedelta(hours=24)}
        mood = set_mood(self.user, data)
        self.assertEqual(mood.status_text, 'Happy')

    def test_set_mood_upsert_replaces_old(self):
        data1 = {'status_text': 'First', 'song_id': None, 'expires_at': timezone.now() + timedelta(hours=24)}
        set_mood(self.user, data1)
        data2 = {'status_text': 'Second', 'song_id': None, 'expires_at': timezone.now() + timedelta(hours=24)}
        set_mood(self.user, data2)
        self.assertEqual(Mood.objects.filter(user=self.user).count(), 1)
        mood = Mood.objects.get(user=self.user)
        self.assertEqual(mood.status_text, 'Second')

    def test_set_mood_with_song(self):
        song = make_song(self.artist, title='Mood Song Svc')
        data = {'status_text': 'Listening', 'song_id': song.id, 'expires_at': timezone.now() + timedelta(hours=24)}
        mood = set_mood(self.user, data)
        self.assertEqual(mood.song, song)

    def test_set_mood_invalid_song_id_raises(self):
        data = {'status_text': 'X', 'song_id': uuid.uuid4(), 'expires_at': timezone.now() + timedelta(hours=24)}
        with self.assertRaises(NotFound):
            set_mood(self.user, data)

    def test_set_mood_creates_friend_activity(self):
        data = {'status_text': 'Activity test', 'song_id': None, 'expires_at': timezone.now() + timedelta(hours=24)}
        set_mood(self.user, data)
        self.assertTrue(FriendActivity.objects.filter(user=self.user, activity_type=FriendActivity.TYPE_MOOD).exists())

    def test_delete_mood(self):
        data = {'status_text': 'ToDelete', 'song_id': None, 'expires_at': timezone.now() + timedelta(hours=24)}
        set_mood(self.user, data)
        delete_mood(self.user)
        self.assertFalse(Mood.objects.filter(user=self.user).exists())


class CreateFriendActivityContractTest(TestCase):
    """
    Test rieng dam bao signature create_friend_activity() khop dung HOP DONG
    ma music/services.py::record_play() da goi tu Tuan 2 - khong duoc doi.
    """

    def setUp(self):
        self.artist = make_user('contractartist', 'contractartist@test.com', role='artist')
        self.user = make_user('contractuser', 'contractuser@test.com')
        self.song = make_song(self.artist)

    def test_record_play_integration_creates_activity(self):
        """Goi truc tiep record_play() tu music app, xac nhan FriendActivity duoc tao dung."""
        before = FriendActivity.objects.filter(user=self.user).count()
        record_play(self.user, self.song)
        after = FriendActivity.objects.filter(user=self.user).count()
        self.assertEqual(after, before + 1)

        activity = FriendActivity.objects.filter(user=self.user).first()
        self.assertEqual(activity.activity_type, FriendActivity.TYPE_PLAYING)
        self.assertEqual(activity.song, self.song)

    def test_create_friend_activity_signature_with_kwargs(self):
        """Goi dung kieu keyword argument ma music app dang dung: user=, activity_type=, song=."""
        activity = create_friend_activity(user=self.user, activity_type='playing', song=self.song)
        self.assertEqual(activity.user, self.user)
        self.assertEqual(activity.song, self.song)


# ═══════════════════════════════════════════════════════════════════════════════
# VIEW TESTS (HTTP Integration)
# ═══════════════════════════════════════════════════════════════════════════════

class FollowViewTest(TestCase):

    def setUp(self):
        self.client = Client(enforce_csrf_checks=False)
        self.alice = make_user('fvalice', 'fvalice@test.com')
        self.bob = make_user('fvbob', 'fvbob@test.com')

    def test_follow_requires_auth(self):
        response = self.client.post(f'/api/v1/social/users/{self.bob.id}/follow/')
        self.assertEqual(response.status_code, 401)

    def test_follow_success(self):
        self.client.force_login(self.alice)
        response = self.client.post(f'/api/v1/social/users/{self.bob.id}/follow/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['data']['action'], 'followed')

    def test_follow_self_400(self):
        self.client.force_login(self.alice)
        response = self.client.post(f'/api/v1/social/users/{self.alice.id}/follow/')
        self.assertEqual(response.status_code, 400)

    def test_follow_status_public(self):
        Follow.objects.create(follower=self.alice, following=self.bob)
        response = self.client.get(f'/api/v1/social/users/{self.bob.id}/follow-status/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['data']['followers_count'], 1)

    def test_followers_list_public(self):
        Follow.objects.create(follower=self.alice, following=self.bob)
        response = self.client.get(f'/api/v1/social/users/{self.bob.id}/followers/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()['data']['items']), 1)

    def test_following_list_public(self):
        Follow.objects.create(follower=self.alice, following=self.bob)
        response = self.client.get(f'/api/v1/social/users/{self.alice.id}/following/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()['data']['items']), 1)


class MoodViewTest(TestCase):

    def setUp(self):
        self.client = Client(enforce_csrf_checks=False)
        self.user = make_user('mvuser', 'mvuser@test.com')
        self.viewer = make_user('mvviewer', 'mvviewer@test.com')

    def test_get_my_mood_requires_auth(self):
        response = self.client.get('/api/v1/social/me/mood/')
        self.assertEqual(response.status_code, 401)

    def test_get_my_mood_not_found_404(self):
        self.client.force_login(self.user)
        response = self.client.get('/api/v1/social/me/mood/')
        self.assertEqual(response.status_code, 404)

    def test_post_set_mood_success(self):
        self.client.force_login(self.user)
        response = self.client.post(
            '/api/v1/social/me/mood/',
            data=json.dumps({'status_text': 'Feeling great today'}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()['data']['status_text'], 'Feeling great today')

    def test_post_set_mood_validation_error(self):
        self.client.force_login(self.user)
        response = self.client.post(
            '/api/v1/social/me/mood/',
            data=json.dumps({'status_text': ''}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)

    def test_get_my_mood_after_set(self):
        self.client.force_login(self.user)
        self.client.post('/api/v1/social/me/mood/', data=json.dumps({'status_text': 'X'}), content_type='application/json')
        response = self.client.get('/api/v1/social/me/mood/')
        self.assertEqual(response.status_code, 200)

    def test_delete_mood(self):
        self.client.force_login(self.user)
        self.client.post('/api/v1/social/me/mood/', data=json.dumps({'status_text': 'X'}), content_type='application/json')
        response = self.client.delete('/api/v1/social/me/mood/')
        self.assertEqual(response.status_code, 204)
        check = self.client.get('/api/v1/social/me/mood/')
        self.assertEqual(check.status_code, 404)

    def test_get_user_mood_public_none(self):
        response = self.client.get(f'/api/v1/social/users/{self.user.id}/mood/')
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.json()['data'])

    def test_get_user_mood_public_active(self):
        self.client.force_login(self.user)
        self.client.post('/api/v1/social/me/mood/', data=json.dumps({'status_text': 'Public mood'}), content_type='application/json')
        self.client.logout()
        response = self.client.get(f'/api/v1/social/users/{self.user.id}/mood/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['data']['status_text'], 'Public mood')


class FeedViewTest(TestCase):

    def setUp(self):
        self.client = Client(enforce_csrf_checks=False)
        self.alice = make_user('fdvalice', 'fdvalice@test.com')
        self.bob = make_user('fdvbob', 'fdvbob@test.com')

    def test_feed_requires_auth(self):
        response = self.client.get('/api/v1/social/feed/')
        self.assertEqual(response.status_code, 401)

    def test_feed_empty_initially(self):
        self.client.force_login(self.alice)
        response = self.client.get('/api/v1/social/feed/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['data']['items'], [])

    def test_my_activities_requires_auth(self):
        response = self.client.get('/api/v1/social/me/activities/')
        self.assertEqual(response.status_code, 401)

    def test_my_activities_after_mood_set(self):
        self.client.force_login(self.alice)
        self.client.post('/api/v1/social/me/mood/', data=json.dumps({'status_text': 'X'}), content_type='application/json')
        response = self.client.get('/api/v1/social/me/activities/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()['data']['items']), 1)


# ═══════════════════════════════════════════════════════════════════════════════
# END-TO-END FLOW TEST
# ═══════════════════════════════════════════════════════════════════════════════

class EndToEndSocialFlowTest(TestCase):
    """
    Test dung yeu cau de bai: A follow B -> B co hoat dong -> A thay trong Feed.
    Bao phu ca 3 nhom chuc nang: Follow (toggle), Mood, Feed trong 1 luong lien tuc.
    """

    def setUp(self):
        self.client = Client(enforce_csrf_checks=False)
        self.alice = make_user('e2ealice', 'e2ealice@test.com')
        self.bob = make_user('e2ebob', 'e2ebob@test.com')
        self.artist = make_user('e2esocialartist', 'e2esocialartist@test.com', role='artist')

    def test_full_social_lifecycle(self):
        # 1. Alice follow Bob
        self.client.force_login(self.alice)
        r1 = self.client.post(f'/api/v1/social/users/{self.bob.id}/follow/')
        self.assertEqual(r1.status_code, 200)
        self.assertEqual(r1.json()['data']['action'], 'followed')

        # 2. Kiem tra follow-status dung
        r2 = self.client.get(f'/api/v1/social/users/{self.bob.id}/follow-status/')
        self.assertTrue(r2.json()['data']['is_following'])
        self.assertEqual(r2.json()['data']['followers_count'], 1)

        # 3. Alice xem Feed - rong vi Bob chua co hoat dong gi
        r3 = self.client.get('/api/v1/social/feed/')
        self.assertEqual(r3.json()['data']['items'], [])

        # 4. Bob dang nhap, cap nhat Mood
        self.client.force_login(self.bob)
        genre = make_genre('E2ESocialGenre')
        song = make_song(self.artist, genre, title='Bob Listening Song')
        r4 = self.client.post(
            '/api/v1/social/me/mood/',
            data=json.dumps({'status_text': 'Dang nghe nhac chill', 'song_id': str(song.id)}),
            content_type='application/json',
        )
        self.assertEqual(r4.status_code, 201)

        # 5. Bob nghe mot bai hat khac (qua music app, kich hoat record_play -> FriendActivity)
        song2 = make_song(self.artist, genre, title='Bob Played Song', status=Song.STATUS_PUBLISHED)
        self.client.force_login(self.bob)
        r5 = self.client.post(f'/api/v1/music/songs/{song2.id}/play/')
        self.assertEqual(r5.status_code, 200)

        # 6. Alice xem lai Feed - phai thay CA 2 hoat dong cua Bob (mood + playing)
        self.client.force_login(self.alice)
        r6 = self.client.get('/api/v1/social/feed/')
        self.assertEqual(r6.status_code, 200)
        items = r6.json()['data']['items']
        self.assertEqual(len(items), 2)
        activity_types = {item['activity_type'] for item in items}
        self.assertEqual(activity_types, {'mood', 'playing'})
        for item in items:
            self.assertEqual(item['user']['username'], 'e2ebob')

        # 7. Alice unfollow Bob
        r7 = self.client.post(f'/api/v1/social/users/{self.bob.id}/follow/')
        self.assertEqual(r7.json()['data']['action'], 'unfollowed')

        # 8. Feed cua Alice tro lai rong sau khi unfollow
        r8 = self.client.get('/api/v1/social/feed/')
        self.assertEqual(r8.json()['data']['items'], [])
```

---

*Tổng cộng: 10 files — 1683 dòng code, đã chạy test xác nhận PASS 100%.*
