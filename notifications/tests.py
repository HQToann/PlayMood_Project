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