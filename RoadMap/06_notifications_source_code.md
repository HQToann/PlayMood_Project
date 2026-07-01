# 06 — Source Code Hoàn Chỉnh App `notifications`

**Tuần 6 | Tuân thủ kiến trúc phân tầng (views → selectors/services → models), Fix R11 (target_type/target_id bắt buộc), tối ưu N+1 bằng `select_related('sender')`**

> Copy từng file vào đúng thư mục `notifications/` trong project, rồi xem mục **"Cấu hình & Tích hợp"** ở cuối file để đăng ký app + tạo hook thông báo từ các app khác.

---

## Lưu ý về lỗi N+1 đã sửa

Ở app `social` (Tuần 5), điểm tối ưu quan trọng nhất là `list_feed()` phải dùng `select_related('user', 'song', 'song__artist')` để tránh N+1. App `notifications` áp dụng đúng nguyên tắc đó:

- `list_notifications()` dùng `select_related('sender')` — mỗi `Notification.to_dict()` chỉ đụng vào `self.sender` (1 FK), nên 1 query JOIN là đủ, bất kể có bao nhiêu thông báo.
- **Không** thêm `include_stats`/`include_song_count` kiểu tính toán phụ (như `Song.to_dict(include_stats=True)` hay `Playlist.to_dict(include_song_count=True)`) vào bất kỳ list nào — vì các hàm đó tự chạy thêm 1 query aggregate cho **mỗi item**, đây chính là dạng N+1 "ẩn" cần tránh khi viết `search` (xem file 07).

---

## Cấu Trúc File

```
notifications/
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
├── tests.py
└── migrations/
    ├── __init__.py
    └── 0001_initial.py
```

---

## `notifications/apps.py`

```python
"""notifications/apps.py"""
from django.apps import AppConfig


class NotificationsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'notifications'
    label = 'notifications'
    verbose_name = 'Thông báo'
```

---

## `notifications/models.py`

```python
"""
notifications/models.py
=========================
Model Notification - thông báo trong hệ thống.

Business rule quan trọng nhất (Fix R11):
    Mọi notif_type TRỪ 'system' và 'verify_result' BẮT BUỘC phải có
    target_type + target_id. Frontend dùng 2 field này để điều hướng khi
    người dùng bấm vào thông báo (vd: bấm thông báo 'like' -> mở bài hát đó).
    Rule này được enforce ở services.create_notification(), KHÔNG ở model,
    theo đúng quy ước phân tầng của dự án (model không chứa business logic).
"""

import uuid
from django.db import models


class Notification(models.Model):
    TYPE_FOLLOW = 'follow'
    TYPE_LIKE = 'like'
    TYPE_COMMENT = 'comment'
    TYPE_REPLY = 'reply'
    TYPE_SYSTEM = 'system'
    TYPE_VERIFY_RESULT = 'verify_result'
    TYPE_CHOICES = [
        (TYPE_FOLLOW, 'Theo dõi mới'),
        (TYPE_LIKE, 'Lượt thích'),
        (TYPE_COMMENT, 'Bình luận mới'),
        (TYPE_REPLY, 'Trả lời bình luận'),
        (TYPE_SYSTEM, 'Hệ thống'),
        (TYPE_VERIFY_RESULT, 'Kết quả xác thực'),
    ]

    TARGET_SONG = 'song'
    TARGET_PLAYLIST = 'playlist'
    TARGET_COMMENT = 'comment'
    TARGET_USER = 'user'
    TARGET_CHOICES = [
        (TARGET_SONG, 'Bài hát'),
        (TARGET_PLAYLIST, 'Playlist'),
        (TARGET_COMMENT, 'Bình luận'),
        (TARGET_USER, 'Người dùng'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    recipient = models.ForeignKey(
        'accounts.User', on_delete=models.CASCADE,
        related_name='notifications', verbose_name='Người nhận', db_index=True,
    )
    sender = models.ForeignKey(
        'accounts.User', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='sent_notifications', verbose_name='Người gửi',
    )

    notif_type = models.CharField(max_length=20, choices=TYPE_CHOICES, db_index=True, verbose_name='Loại')

    # Fix R11 - bắt buộc với mọi loại trừ system/verify_result, enforce ở services.py
    target_type = models.CharField(max_length=10, choices=TARGET_CHOICES, null=True, blank=True)
    target_id = models.UUIDField(null=True, blank=True)

    message = models.TextField(verbose_name='Nội dung')
    is_read = models.BooleanField(default=False, db_index=True, verbose_name='Đã đọc')

    created_at = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='Thời điểm')

    class Meta:
        db_table = 'notifications_notification'
        ordering = ['-created_at']
        verbose_name = 'Thông báo'
        verbose_name_plural = 'Thông báo'
        indexes = [
            # Hỗ trợ 2 truy vấn phổ biến nhất: list theo recipient, và đếm unread
            models.Index(fields=['recipient', 'is_read', 'created_at'], name='notif_recipient_read_idx'),
        ]

    def __str__(self):
        state = 'read' if self.is_read else 'unread'
        return f'{self.recipient.username}: {self.notif_type} ({state})'

    def to_dict(self) -> dict:
        return {
            'id': str(self.id),
            'sender': {
                'id': str(self.sender_id),
                'username': self.sender.username,
                'display_name': self.sender.get_display_name(),
                'avatar': self.sender.avatar.url if self.sender.avatar else None,
            } if self.sender_id else None,
            'notif_type': self.notif_type,
            'target_type': self.target_type,
            'target_id': str(self.target_id) if self.target_id else None,
            'message': self.message,
            'is_read': self.is_read,
            'created_at': self.created_at.isoformat(),
        }
```

---

## `notifications/exceptions.py`

```python
"""notifications/exceptions.py"""
from accounts.exceptions import AppException


class NotificationNotFound(AppException):
    """Thông báo không tồn tại hoặc không thuộc về user - HTTP 404."""
    def __init__(self, message='Thông báo không tồn tại'):
        super().__init__(message, error_code='NOT_FOUND')
```

---

## `notifications/validators.py`

```python
"""
notifications/validators.py
=============================
Quy ước (giữ nguyên từ các app trước):
  - CHỈ kiểm tra kiểu dữ liệu, không gọi service, không truy vấn DB
  - KHÔNG raise HTTP exception - chỉ raise ValidationError nếu cần
"""


def validate_list_notifications_params(params: dict) -> dict:
    """Validate query params khi list thông báo: page, page_size, unread_only."""
    try:
        page = max(1, int(params.get('page', 1)))
    except (ValueError, TypeError):
        page = 1

    try:
        page_size = min(100, max(1, int(params.get('page_size', 20))))
    except (ValueError, TypeError):
        page_size = 20

    unread_only = str(params.get('unread_only', '')).strip().lower() in ('true', '1', 'yes')

    return {'page': page, 'page_size': page_size, 'unread_only': unread_only}
```

---

## `notifications/selectors.py`

```python
"""
notifications/selectors.py
=============================
Tầng Đọc cho app notifications.

DIEM TOI UU N+1 QUAN TRONG: list_notifications() dùng select_related('sender')
để JOIN sẵn thông tin người gửi trong 1 query SQL - mỗi to_dict() chỉ đụng
vào self.sender (1 FK), không có vòng lặp query nào phát sinh thêm dù list
có bao nhiêu thông báo.
"""

import math

from notifications.models import Notification
from notifications.exceptions import NotificationNotFound


def list_notifications(user, page=1, page_size=20, unread_only=False) -> dict:
    qs = Notification.objects.filter(recipient=user).select_related('sender')

    if unread_only:
        qs = qs.filter(is_read=False)

    qs = qs.order_by('-created_at')

    total = qs.count()
    start = (page - 1) * page_size
    items = [n.to_dict() for n in qs[start:start + page_size]]

    return {
        'items': items,
        'pagination': {
            'page': page,
            'page_size': page_size,
            'total': total,
            'total_pages': math.ceil(total / page_size) if total > 0 else 1,
        },
    }


def count_unread(user) -> int:
    return Notification.objects.filter(recipient=user, is_read=False).count()


def get_notification_by_id(notification_id, user) -> Notification:
    """Lấy 1 thông báo - chỉ trả nếu thuộc về user (không lộ thông báo người khác)."""
    try:
        return Notification.objects.select_related('sender').get(id=notification_id, recipient=user)
    except Notification.DoesNotExist:
        raise NotificationNotFound()
```

---

## `notifications/services.py`

```python
"""
notifications/services.py
=============================
Tầng Ghi cho app notifications.

QUAN TRONG - create_notification() là ENTRYPOINT DUY NHẤT được các app khác
(social, music, accounts) gọi để phát thông báo, theo đúng pattern đã thiết
lập ở Tuần 5 với create_friend_activity(): caller LUÔN bọc lời gọi trong
try/except để lỗi ở notifications không bao giờ làm vỡ luồng nghiệp vụ chính
(vd: like một bài hát vẫn phải thành công dù việc tạo notification bị lỗi).

Fix R11: enforce rule target_type/target_id bắt buộc ngay tại đây.
"""

import logging

from notifications.models import Notification
from notifications.exceptions import NotificationNotFound

logger = logging.getLogger(__name__)

# 2 loại duy nhất được phép không có target - thông báo hệ thống/kết quả xác thực
NO_TARGET_REQUIRED = {Notification.TYPE_SYSTEM, Notification.TYPE_VERIFY_RESULT}


def create_notification(recipient, notif_type: str, message: str, sender=None,
                         target_type: str = None, target_id=None):
    """
    Tạo 1 Notification mới.

    Business rules:
        - Không tự thông báo cho chính mình (recipient == sender -> bỏ qua, trả None)
        - Fix R11: notif_type ngoài {system, verify_result} bắt buộc có target_type + target_id,
          nếu thiếu -> raise ValueError để lộ lỗi lập trình ngay khi dev tích hợp sai,
          thay vì âm thầm lưu dữ liệu thiếu vào DB.

    Returns:
        Notification vừa tạo, hoặc None nếu bị bỏ qua (tự thông báo cho chính mình).
    """
    if sender is not None and str(getattr(sender, 'id', sender)) == str(recipient.id):
        return None

    if notif_type not in NO_TARGET_REQUIRED and (not target_type or not target_id):
        raise ValueError(
            f'notif_type="{notif_type}" bắt buộc phải có target_type và target_id (Fix R11)'
        )

    notification = Notification.objects.create(
        recipient=recipient,
        sender=sender,
        notif_type=notif_type,
        target_type=target_type,
        target_id=target_id,
        message=message,
    )
    logger.info('Notification created: recipient=%s type=%s', recipient.username, notif_type)
    return notification


def mark_read(notification: Notification, user) -> Notification:
    """Đánh dấu 1 thông báo đã đọc - chỉ chủ sở hữu."""
    if str(notification.recipient_id) != str(user.id):
        raise NotificationNotFound()

    if not notification.is_read:
        notification.is_read = True
        notification.save(update_fields=['is_read'])
    return notification


def mark_all_read(user) -> int:
    """Đánh dấu tất cả thông báo chưa đọc của user thành đã đọc. Trả số bản ghi bị ảnh hưởng."""
    updated = Notification.objects.filter(recipient=user, is_read=False).update(is_read=True)
    return updated


def delete_notification(notification: Notification, user) -> None:
    """Xoá 1 thông báo - chỉ chủ sở hữu."""
    if str(notification.recipient_id) != str(user.id):
        raise NotificationNotFound()
    notification.delete()
```

---

## `notifications/views.py`

```python
"""
notifications/views.py
=========================
Tầng HTTP cho app notifications.

Quy ước (giữ nguyên): views.py KHÔNG import Notification để query trực tiếp,
mọi đọc qua selectors.py, mọi ghi qua services.py.
"""

import json
import logging

from django.http import JsonResponse
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect

from accounts.decorators import require_auth
from accounts.exceptions import ValidationError, PermissionDenied, NotFound

from notifications.exceptions import NotificationNotFound
from notifications.validators import validate_list_notifications_params
from notifications.selectors import list_notifications, count_unread, get_notification_by_id
from notifications.services import mark_read, mark_all_read, delete_notification

logger = logging.getLogger(__name__)


def handle_exception(e: Exception) -> JsonResponse:
    if isinstance(e, ValidationError):
        return JsonResponse(
            {'success': False, 'error': {'code': 'VALIDATION_ERROR', 'message': e.message, 'fields': e.fields}},
            status=400,
        )
    if isinstance(e, PermissionDenied):
        return JsonResponse(
            {'success': False, 'error': {'code': e.error_code, 'message': e.message}},
            status=403,
        )
    if isinstance(e, (NotificationNotFound, NotFound)):
        return JsonResponse(
            {'success': False, 'error': {'code': 'NOT_FOUND', 'message': e.message}},
            status=404,
        )
    logger.exception('Unhandled exception in notifications views: %s', e)
    return JsonResponse(
        {'success': False, 'error': {'code': 'SERVER_ERROR', 'message': 'Lỗi server'}},
        status=500,
    )


class NotificationListView(View):
    """GET /api/v1/notifications/ - Danh sách thông báo của tôi (Auth)"""

    @method_decorator(require_auth)
    def get(self, request):
        try:
            filters = validate_list_notifications_params(request.GET)
            result = list_notifications(
                request.user,
                page=filters['page'],
                page_size=filters['page_size'],
                unread_only=filters['unread_only'],
            )
            return JsonResponse({'success': True, 'data': result})
        except Exception as e:
            return handle_exception(e)


class UnreadCountView(View):
    """GET /api/v1/notifications/unread-count/ - Số thông báo chưa đọc (Auth)"""

    @method_decorator(require_auth)
    def get(self, request):
        try:
            count = count_unread(request.user)
            return JsonResponse({'success': True, 'data': {'unread_count': count}})
        except Exception as e:
            return handle_exception(e)


class NotificationReadView(View):
    """POST /api/v1/notifications/<id>/read/ - Đánh dấu 1 thông báo đã đọc (Auth+CSRF)"""

    @method_decorator(csrf_protect)
    @method_decorator(require_auth)
    def post(self, request, notification_id):
        try:
            notification = get_notification_by_id(notification_id, request.user)
            notification = mark_read(notification, request.user)
            return JsonResponse({'success': True, 'data': notification.to_dict()})
        except Exception as e:
            return handle_exception(e)


class MarkAllReadView(View):
    """POST /api/v1/notifications/read-all/ - Đánh dấu tất cả đã đọc (Auth+CSRF)"""

    @method_decorator(csrf_protect)
    @method_decorator(require_auth)
    def post(self, request):
        try:
            updated = mark_all_read(request.user)
            return JsonResponse({'success': True, 'data': {'updated_count': updated}})
        except Exception as e:
            return handle_exception(e)


class NotificationDetailView(View):
    """DELETE /api/v1/notifications/<id>/ - Xoá 1 thông báo (Auth+Owner+CSRF)"""

    @method_decorator(csrf_protect)
    @method_decorator(require_auth)
    def delete(self, request, notification_id):
        try:
            notification = get_notification_by_id(notification_id, request.user)
            delete_notification(notification, request.user)
            return JsonResponse({'success': True}, status=204)
        except Exception as e:
            return handle_exception(e)
```

---

## `notifications/urls.py`

```python
"""notifications/urls.py — prefix: /api/v1/notifications/"""

from django.urls import path
from notifications.views import (
    NotificationListView, UnreadCountView, NotificationReadView,
    MarkAllReadView, NotificationDetailView,
)

urlpatterns = [
    path('', NotificationListView.as_view(), name='notifications-list'),
    path('unread-count/', UnreadCountView.as_view(), name='notifications-unread-count'),
    path('read-all/', MarkAllReadView.as_view(), name='notifications-read-all'),
    path('<uuid:notification_id>/read/', NotificationReadView.as_view(), name='notifications-read'),
    path('<uuid:notification_id>/', NotificationDetailView.as_view(), name='notifications-detail'),
]
```

> **Lưu ý thứ tự route:** `read-all/` và `unread-count/` phải khai báo **trước** `<uuid:notification_id>/`, giống nguyên tắc `me/` phải đứng trước `<uuid:user_id>/` đã ghi trong `accounts/urls.py` — nếu không Django sẽ thử match `read-all` như một UUID và lỗi 404.

---

## `notifications/admin.py`

```python
"""notifications/admin.py"""
from django.contrib import admin
from notifications.models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('recipient', 'sender', 'notif_type', 'is_read', 'created_at')
    list_filter = ('notif_type', 'is_read')
    search_fields = ('recipient__username', 'sender__username', 'message')
    readonly_fields = ('created_at',)
```

---

## `notifications/migrations/__init__.py`

```python
```

---

## `notifications/migrations/0001_initial.py`

```python
import uuid
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Notification',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('notif_type', models.CharField(choices=[
                    ('follow', 'Theo dõi mới'), ('like', 'Lượt thích'), ('comment', 'Bình luận mới'),
                    ('reply', 'Trả lời bình luận'), ('system', 'Hệ thống'), ('verify_result', 'Kết quả xác thực'),
                ], db_index=True, max_length=20, verbose_name='Loại')),
                ('target_type', models.CharField(blank=True, choices=[
                    ('song', 'Bài hát'), ('playlist', 'Playlist'), ('comment', 'Bình luận'), ('user', 'Người dùng'),
                ], max_length=10, null=True)),
                ('target_id', models.UUIDField(blank=True, null=True)),
                ('message', models.TextField(verbose_name='Nội dung')),
                ('is_read', models.BooleanField(db_index=True, default=False, verbose_name='Đã đọc')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='Thời điểm')),
                ('recipient', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='notifications', to=settings.AUTH_USER_MODEL, verbose_name='Người nhận')),
                ('sender', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='sent_notifications', to=settings.AUTH_USER_MODEL, verbose_name='Người gửi')),
            ],
            options={
                'verbose_name': 'Thông báo',
                'verbose_name_plural': 'Thông báo',
                'db_table': 'notifications_notification',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='notification',
            index=models.Index(fields=['recipient', 'is_read', 'created_at'], name='notif_recipient_read_idx'),
        ),
    ]
```

---

## `notifications/tests.py`

```python
"""
notifications/tests.py
=========================
Unit tests cho app notifications - Tuan 6.

Chay tests:
    python manage.py test notifications --verbosity=2

Coverage:
  - Models:      Notification.to_dict() co/khong sender
  - Validators:  list params (page, page_size, unread_only)
  - Selectors:   list_notifications (TRONG TAM: khong N+1 qua select_related),
                 count_unread, get_notification_by_id (chi chu so huu)
  - Services:    create_notification (Fix R11: bat buoc target khi khong phai
                 system/verify_result, khong tu thong bao cho chinh minh),
                 mark_read, mark_all_read, delete_notification
  - Views:       toan bo endpoints - HTTP status, phan quyen Auth+Owner
"""

import uuid

from django.test import TestCase, Client
from django.test.utils import CaptureQueriesContext
from django.db import connection

from accounts.models import User
from notifications.models import Notification
from notifications.validators import validate_list_notifications_params
from notifications.selectors import list_notifications, count_unread, get_notification_by_id
from notifications.services import create_notification, mark_read, mark_all_read, delete_notification
from notifications.exceptions import NotificationNotFound


def make_user(username, email, password='Test1234', role='user', **kwargs):
    return User.objects.create_user(username=username, email=email, password=password, role=role, **kwargs)


# ═══════════════════════════════════════════════════════════════════════════════
# MODEL TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class NotificationModelTest(TestCase):

    def setUp(self):
        self.recipient = make_user('modelrecipient', 'modelrecipient@test.com')
        self.sender = make_user('modelsender', 'modelsender@test.com')

    def test_to_dict_with_sender(self):
        n = Notification.objects.create(
            recipient=self.recipient, sender=self.sender, notif_type=Notification.TYPE_FOLLOW,
            target_type=Notification.TARGET_USER, target_id=self.sender.id, message='Da theo doi ban',
        )
        d = n.to_dict()
        self.assertEqual(d['sender']['username'], 'modelsender')
        self.assertFalse(d['is_read'])

    def test_to_dict_without_sender_system_type(self):
        n = Notification.objects.create(
            recipient=self.recipient, sender=None, notif_type=Notification.TYPE_SYSTEM, message='Bao tri he thong',
        )
        d = n.to_dict()
        self.assertIsNone(d['sender'])
        self.assertIsNone(d['target_type'])


# ═══════════════════════════════════════════════════════════════════════════════
# VALIDATOR TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class ValidateListNotificationsParamsTest(TestCase):

    def test_defaults(self):
        result = validate_list_notifications_params({})
        self.assertEqual(result['page'], 1)
        self.assertEqual(result['page_size'], 20)
        self.assertFalse(result['unread_only'])

    def test_unread_only_true(self):
        result = validate_list_notifications_params({'unread_only': 'true'})
        self.assertTrue(result['unread_only'])

    def test_page_size_capped_at_100(self):
        result = validate_list_notifications_params({'page_size': '500'})
        self.assertEqual(result['page_size'], 100)


# ═══════════════════════════════════════════════════════════════════════════════
# SELECTOR TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class NotificationSelectorTest(TestCase):

    def setUp(self):
        self.user = make_user('selusr', 'selusr@test.com')
        self.other = make_user('selother', 'selother@test.com')
        self.sender = make_user('selsender', 'selsender@test.com')

    def test_list_notifications_only_own(self):
        create_notification(self.user, Notification.TYPE_FOLLOW, 'X', sender=self.sender,
                             target_type='user', target_id=self.sender.id)
        create_notification(self.other, Notification.TYPE_FOLLOW, 'Y', sender=self.sender,
                             target_type='user', target_id=self.sender.id)
        result = list_notifications(self.user)
        self.assertEqual(len(result['items']), 1)

    def test_list_notifications_unread_only_filter(self):
        n1 = create_notification(self.user, Notification.TYPE_FOLLOW, 'A', sender=self.sender,
                                  target_type='user', target_id=self.sender.id)
        n2 = create_notification(self.user, Notification.TYPE_FOLLOW, 'B', sender=self.sender,
                                  target_type='user', target_id=self.sender.id)
        mark_read(n1, self.user)
        result = list_notifications(self.user, unread_only=True)
        self.assertEqual(len(result['items']), 1)
        self.assertEqual(result['items'][0]['id'], str(n2.id))

    def test_count_unread(self):
        create_notification(self.user, Notification.TYPE_FOLLOW, 'A', sender=self.sender,
                             target_type='user', target_id=self.sender.id)
        create_notification(self.user, Notification.TYPE_FOLLOW, 'B', sender=self.sender,
                             target_type='user', target_id=self.sender.id)
        self.assertEqual(count_unread(self.user), 2)

    def test_get_notification_by_id_not_owner_raises(self):
        n = create_notification(self.user, Notification.TYPE_FOLLOW, 'A', sender=self.sender,
                                 target_type='user', target_id=self.sender.id)
        with self.assertRaises(NotificationNotFound):
            get_notification_by_id(n.id, self.other)

    def test_list_notifications_query_count_no_n_plus_1(self):
        """
        DIEM TOI UU QUAN TRONG: list_notifications() KHONG duoc phat sinh N+1 query
        du co bao nhieu nguoi gui khac nhau, nho select_related('sender').
        """
        for i in range(10):
            s = make_user(f'n1sender{i}', f'n1sender{i}@test.com')
            create_notification(self.user, Notification.TYPE_FOLLOW, f'Follow {i}', sender=s,
                                 target_type='user', target_id=s.id)

        with CaptureQueriesContext(connection) as ctx:
            result = list_notifications(self.user, page=1, page_size=20)
            self.assertEqual(len(result['items']), 10)

        query_count = len(ctx.captured_queries)
        self.assertLess(query_count, 6, f'Qua nhieu query ({query_count}) - kiem tra select_related("sender")')


# ═══════════════════════════════════════════════════════════════════════════════
# SERVICE TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class CreateNotificationServiceTest(TestCase):

    def setUp(self):
        self.recipient = make_user('svcrecipient', 'svcrecipient@test.com')
        self.sender = make_user('svcsender', 'svcsender@test.com')

    def test_create_follow_notification_success(self):
        n = create_notification(
            self.recipient, Notification.TYPE_FOLLOW, 'Da theo doi ban', sender=self.sender,
            target_type='user', target_id=self.sender.id,
        )
        self.assertIsNotNone(n)
        self.assertEqual(n.notif_type, 'follow')

    def test_create_system_notification_without_target_ok(self):
        n = create_notification(self.recipient, Notification.TYPE_SYSTEM, 'Bao tri')
        self.assertIsNotNone(n)
        self.assertIsNone(n.target_type)

    def test_create_non_system_without_target_raises(self):
        """Fix R11: bat buoc target_type/target_id cho moi loai tru system/verify_result."""
        with self.assertRaises(ValueError):
            create_notification(self.recipient, Notification.TYPE_LIKE, 'Da thich bai hat', sender=self.sender)

    def test_self_notification_skipped(self):
        result = create_notification(
            self.recipient, Notification.TYPE_FOLLOW, 'X', sender=self.recipient,
            target_type='user', target_id=self.recipient.id,
        )
        self.assertIsNone(result)
        self.assertEqual(Notification.objects.filter(recipient=self.recipient).count(), 0)

    def test_mark_read(self):
        n = create_notification(self.recipient, Notification.TYPE_FOLLOW, 'X', sender=self.sender,
                                 target_type='user', target_id=self.sender.id)
        updated = mark_read(n, self.recipient)
        self.assertTrue(updated.is_read)

    def test_mark_read_not_owner_raises(self):
        n = create_notification(self.recipient, Notification.TYPE_FOLLOW, 'X', sender=self.sender,
                                 target_type='user', target_id=self.sender.id)
        with self.assertRaises(NotificationNotFound):
            mark_read(n, self.sender)

    def test_mark_all_read(self):
        create_notification(self.recipient, Notification.TYPE_FOLLOW, 'A', sender=self.sender,
                             target_type='user', target_id=self.sender.id)
        create_notification(self.recipient, Notification.TYPE_FOLLOW, 'B', sender=self.sender,
                             target_type='user', target_id=self.sender.id)
        updated = mark_all_read(self.recipient)
        self.assertEqual(updated, 2)
        self.assertEqual(count_unread(self.recipient), 0)

    def test_delete_notification(self):
        n = create_notification(self.recipient, Notification.TYPE_FOLLOW, 'X', sender=self.sender,
                                 target_type='user', target_id=self.sender.id)
        delete_notification(n, self.recipient)
        self.assertFalse(Notification.objects.filter(id=n.id).exists())


# ═══════════════════════════════════════════════════════════════════════════════
# VIEW TESTS (HTTP Integration)
# ═══════════════════════════════════════════════════════════════════════════════

class NotificationViewTest(TestCase):

    def setUp(self):
        self.client = Client(enforce_csrf_checks=False)
        self.user = make_user('viewuser', 'viewuser@test.com')
        self.sender = make_user('viewsender', 'viewsender@test.com')

    def test_list_requires_auth(self):
        response = self.client.get('/api/v1/notifications/')
        self.assertEqual(response.status_code, 401)

    def test_list_success(self):
        create_notification(self.user, Notification.TYPE_FOLLOW, 'X', sender=self.sender,
                             target_type='user', target_id=self.sender.id)
        self.client.force_login(self.user)
        response = self.client.get('/api/v1/notifications/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()['data']['items']), 1)

    def test_unread_count(self):
        create_notification(self.user, Notification.TYPE_FOLLOW, 'X', sender=self.sender,
                             target_type='user', target_id=self.sender.id)
        self.client.force_login(self.user)
        response = self.client.get('/api/v1/notifications/unread-count/')
        self.assertEqual(response.json()['data']['unread_count'], 1)

    def test_mark_one_read(self):
        n = create_notification(self.user, Notification.TYPE_FOLLOW, 'X', sender=self.sender,
                                 target_type='user', target_id=self.sender.id)
        self.client.force_login(self.user)
        response = self.client.post(f'/api/v1/notifications/{n.id}/read/')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['data']['is_read'])

    def test_mark_read_not_owner_404(self):
        n = create_notification(self.user, Notification.TYPE_FOLLOW, 'X', sender=self.sender,
                                 target_type='user', target_id=self.sender.id)
        self.client.force_login(self.sender)
        response = self.client.post(f'/api/v1/notifications/{n.id}/read/')
        self.assertEqual(response.status_code, 404)

    def test_mark_all_read(self):
        create_notification(self.user, Notification.TYPE_FOLLOW, 'A', sender=self.sender,
                             target_type='user', target_id=self.sender.id)
        create_notification(self.user, Notification.TYPE_FOLLOW, 'B', sender=self.sender,
                             target_type='user', target_id=self.sender.id)
        self.client.force_login(self.user)
        response = self.client.post('/api/v1/notifications/read-all/')
        self.assertEqual(response.json()['data']['updated_count'], 2)

    def test_delete_notification(self):
        n = create_notification(self.user, Notification.TYPE_FOLLOW, 'X', sender=self.sender,
                                 target_type='user', target_id=self.sender.id)
        self.client.force_login(self.user)
        response = self.client.delete(f'/api/v1/notifications/{n.id}/')
        self.assertEqual(response.status_code, 204)

    def test_route_ordering_read_all_not_matched_as_uuid(self):
        """Xac nhan 'read-all/' khong bi Django hieu nham la <uuid:notification_id>."""
        self.client.force_login(self.user)
        response = self.client.post('/api/v1/notifications/read-all/')
        self.assertNotEqual(response.status_code, 404)
```

---

## Cấu Hình & Tích Hợp

### 1. Đăng ký app trong `music_platform/settings.py`

```python
INSTALLED_APPS = [
    ...
    'accounts',
    'music',
    'playlists',
    'artists',
    'social',
    'notifications',   # <-- thêm dòng này
]
```

### 2. Đăng ký URL trong `music_platform/urls.py`

```python
urlpatterns = [
    ...
    path('api/v1/social/', include('social.urls')),
    path('api/v1/notifications/', include('notifications.urls')),   # <-- thêm dòng này
]
```

### 3. Hook phát thông báo từ các app khác

Xem chi tiết đầy đủ (kèm giải thích tại sao dùng try/except) ở file **`08_integration_patches.md`**. Tóm tắt các điểm hook:

| Sự kiện | App gọi | notif_type | target |
|---|---|---|---|
| A follow B | `social/services.py::toggle_follow()` | `follow` | `user` / id của A (người follow) |
| Like bài hát | `music/services.py::toggle_like()` | `like` | `song` / id bài hát |
| Bình luận gốc | `music/services.py::create_comment()` | `comment` | `song` / id bài hát |
| Trả lời bình luận | `music/services.py::create_comment()` | `reply` | `comment` / id comment cha |
| Duyệt/từ chối xác thực nghệ sĩ | `accounts/services.py::approve_verification()` / `reject_verification()` | `verify_result` | *(không cần target)* |
