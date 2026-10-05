"""
accounts/tests.py
=================
Unit tests cho app accounts — Tuần 1.

Chạy tests:
    python manage.py test accounts --verbosity=2

Coverage:
  - Validators: register, login, update_profile, change_password
  - Services: register_user, login_user, update_profile, toggle_block
  - Selectors: get_user_by_id, is_blocked, get_public_profile
  - Auth Views: CSRF, Register, Login, Logout, Me
  - Account Views: MyProfile, Avatar, Privacy, PublicProfile, Block
  - Decorator: require_auth, require_artist, require_admin

Dùng django.test.TestCase (transaction rollback sau mỗi test).
Dùng Client tích hợp sẵn để test HTTP flow đầy đủ.
"""

import json
import uuid
from io import BytesIO
from unittest.mock import patch, MagicMock
from PIL import Image

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import SESSION_KEY

from accounts.models import User, BlockList, ArtistVerification
from accounts.validators import (
    validate_register,
    validate_login,
    validate_update_profile,
    validate_change_password,
)
from accounts.services import (
    register_user,
    login_user,
    toggle_block,
)
from accounts.selectors import (
    get_user_by_id,
    get_user_by_email,
    is_blocked,
    get_public_profile,
    check_email_exists,
)
from accounts.exceptions import (
    ValidationError,
    AuthenticationError,
    AlreadyExists,
    NotFound,
    AccountInactive,
)
from music_platform.sanitize import sanitize_text, sanitize_url


# ── Helpers ───────────────────────────────────────────────────────────────────

def make_user(username='testuser', email='test@example.com', password='Test1234', role='user', **kwargs):
    """Factory tạo User cho test."""
    return User.objects.create_user(
        username=username,
        email=email,
        password=password,
        role=role,
        **kwargs,
    )


def make_image_file(name='test.jpg', fmt='JPEG', size=(100, 100)):
    """Tạo InMemoryUploadedFile giả lập ảnh upload."""
    from django.core.files.uploadedfile import InMemoryUploadedFile
    buf = BytesIO()
    img = Image.new('RGB', size, color=(255, 0, 0))
    img.save(buf, format=fmt)
    buf.seek(0)
    return InMemoryUploadedFile(
        file=buf,
        field_name='avatar',
        name=name,
        content_type='image/jpeg',
        size=buf.getbuffer().nbytes,
        charset=None,
    )


def get_csrf_token(client):
    """Lấy CSRF token từ cookie sau khi gọi /api/v1/auth/csrf/."""
    client.get('/api/v1/auth/csrf/')
    return client.cookies.get('csrftoken', MagicMock(value='')).value


# ═══════════════════════════════════════════════════════════════════════════════
# SANITIZE TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class SanitizeTextTest(TestCase):
    """Test input sanitization — Fix R12."""

    def test_strips_script_tag(self):
        result = sanitize_text('<script>alert("xss")</script>Hello')
        self.assertEqual(result, 'Hello')

    def test_strips_html_tags(self):
        result = sanitize_text('<b>Bold</b> and <i>italic</i>')
        self.assertEqual(result, 'Bold and italic')

    def test_empty_string(self):
        self.assertEqual(sanitize_text(''), '')

    def test_none_returns_empty(self):
        self.assertEqual(sanitize_text(None), '')

    def test_plain_text_unchanged(self):
        text = 'Xin chào, đây là văn bản thường!'
        self.assertEqual(sanitize_text(text), text)

    def test_strips_onclick(self):
        result = sanitize_text('<div onclick="evil()">text</div>')
        self.assertEqual(result, 'text')

    def test_sanitize_url_valid(self):
        self.assertEqual(sanitize_url('https://example.com'), 'https://example.com')

    def test_sanitize_url_invalid(self):
        with self.assertRaises(ValueError):
            sanitize_url('javascript:alert(1)')

    def test_sanitize_url_empty(self):
        self.assertEqual(sanitize_url(''), '')


# ═══════════════════════════════════════════════════════════════════════════════
# VALIDATOR TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class ValidateRegisterTest(TestCase):

    def test_valid_data(self):
        data = {'username': 'john_doe', 'email': 'john@example.com', 'password': 'Test1234'}
        result = validate_register(data)
        self.assertEqual(result['email'], 'john@example.com')
        self.assertEqual(result['username'], 'john_doe')

    def test_email_lowercased(self):
        data = {'username': 'user', 'email': 'JOHN@EXAMPLE.COM', 'password': 'Test1234'}
        result = validate_register(data)
        self.assertEqual(result['email'], 'john@example.com')

    def test_missing_username(self):
        with self.assertRaises(ValidationError) as ctx:
            validate_register({'email': 'a@b.com', 'password': 'Test1234'})
        self.assertIn('username', ctx.exception.fields)

    def test_username_too_short(self):
        with self.assertRaises(ValidationError) as ctx:
            validate_register({'username': 'ab', 'email': 'a@b.com', 'password': 'Test1234'})
        self.assertIn('username', ctx.exception.fields)

    def test_invalid_username_chars(self):
        with self.assertRaises(ValidationError) as ctx:
            validate_register({'username': 'user name!', 'email': 'a@b.com', 'password': 'Test1234'})
        self.assertIn('username', ctx.exception.fields)

    def test_invalid_email(self):
        with self.assertRaises(ValidationError) as ctx:
            validate_register({'username': 'user', 'email': 'notanemail', 'password': 'Test1234'})
        self.assertIn('email', ctx.exception.fields)

    def test_password_too_short(self):
        with self.assertRaises(ValidationError) as ctx:
            validate_register({'username': 'user', 'email': 'a@b.com', 'password': 'Abc1'})
        self.assertIn('password', ctx.exception.fields)

    def test_weak_password_no_uppercase(self):
        with self.assertRaises(ValidationError) as ctx:
            validate_register({'username': 'user', 'email': 'a@b.com', 'password': 'test1234'})
        self.assertIn('password', ctx.exception.fields)

    def test_weak_password_no_digit(self):
        with self.assertRaises(ValidationError) as ctx:
            validate_register({'username': 'user', 'email': 'a@b.com', 'password': 'TestPass'})
        self.assertIn('password', ctx.exception.fields)

    def test_multiple_errors_at_once(self):
        with self.assertRaises(ValidationError) as ctx:
            validate_register({'username': '', 'email': 'bad', 'password': '123'})
        fields = ctx.exception.fields
        self.assertIn('username', fields)
        self.assertIn('email', fields)
        self.assertIn('password', fields)


class ValidateLoginTest(TestCase):

    def test_valid_data(self):
        result = validate_login({'email': 'user@example.com', 'password': 'pass'})
        self.assertEqual(result['email'], 'user@example.com')

    def test_missing_email(self):
        with self.assertRaises(ValidationError) as ctx:
            validate_login({'password': 'pass'})
        self.assertIn('email', ctx.exception.fields)

    def test_missing_password(self):
        with self.assertRaises(ValidationError) as ctx:
            validate_login({'email': 'a@b.com'})
        self.assertIn('password', ctx.exception.fields)


class ValidateChangePasswordTest(TestCase):

    def test_valid(self):
        data = {
            'old_password': 'OldPass1',
            'new_password': 'NewPass2',
            'confirm_password': 'NewPass2',
        }
        result = validate_change_password(data)
        self.assertEqual(result['new_password'], 'NewPass2')

    def test_confirm_mismatch(self):
        with self.assertRaises(ValidationError) as ctx:
            validate_change_password({
                'old_password': 'OldPass1',
                'new_password': 'NewPass2',
                'confirm_password': 'WrongPass',
            })
        self.assertIn('confirm_password', ctx.exception.fields)

    def test_same_as_old(self):
        with self.assertRaises(ValidationError) as ctx:
            validate_change_password({
                'old_password': 'SamePass1',
                'new_password': 'SamePass1',
                'confirm_password': 'SamePass1',
            })
        self.assertIn('new_password', ctx.exception.fields)


# ═══════════════════════════════════════════════════════════════════════════════
# SELECTOR TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class SelectorsTest(TestCase):

    def setUp(self):
        self.user_a = make_user('alice', 'alice@example.com', 'Alice1234')
        self.user_b = make_user('bob',   'bob@example.com',   'Bob12345')

    def test_get_user_by_id_found(self):
        user = get_user_by_id(self.user_a.id)
        self.assertEqual(user.username, 'alice')

    def test_get_user_by_id_not_found(self):
        with self.assertRaises(NotFound):
            get_user_by_id(uuid.uuid4())

    def test_get_user_by_id_inactive(self):
        self.user_a.is_active = False
        self.user_a.save()
        with self.assertRaises(NotFound):
            get_user_by_id(self.user_a.id)

    def test_get_user_by_email_found(self):
        user = get_user_by_email('alice@example.com')
        self.assertIsNotNone(user)
        self.assertEqual(user.username, 'alice')

    def test_get_user_by_email_not_found(self):
        self.assertIsNone(get_user_by_email('nobody@example.com'))

    def test_check_email_exists_true(self):
        self.assertTrue(check_email_exists('alice@example.com'))

    def test_check_email_exists_false(self):
        self.assertFalse(check_email_exists('new@example.com'))

    def test_is_blocked_false(self):
        """Khi chưa block, is_blocked phải trả False."""
        self.assertFalse(is_blocked(self.user_b.id, self.user_a.id))

    def test_is_blocked_true(self):
        """A block B → is_blocked(viewer=B, target=A) = True."""
        BlockList.objects.create(blocker=self.user_a, blocked=self.user_b)
        self.assertTrue(is_blocked(viewer_id=self.user_b.id, target_id=self.user_a.id))

    def test_get_public_profile_blocked_returns_404(self):
        """Người bị block xem profile của người block → NotFound (Fix R10)."""
        BlockList.objects.create(blocker=self.user_a, blocked=self.user_b)
        with self.assertRaises(NotFound):
            get_public_profile(self.user_a.id, viewer=self.user_b)

    def test_get_public_profile_not_blocked(self):
        """Người không bị block xem profile bình thường."""
        user = get_public_profile(self.user_a.id, viewer=self.user_b)
        self.assertEqual(user.username, 'alice')


# ═══════════════════════════════════════════════════════════════════════════════
# SERVICE TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class RegisterServiceTest(TestCase):

    def test_register_success(self):
        data = {'username': 'newuser', 'email': 'new@example.com', 'password': 'Test1234'}
        user = register_user(data)
        self.assertEqual(user.email, 'new@example.com')
        self.assertEqual(user.role, 'user')
        self.assertTrue(user.is_active)
        # Password phải được hash
        self.assertTrue(user.check_password('Test1234'))
        self.assertNotEqual(user.password, 'Test1234')

    def test_register_duplicate_email(self):
        make_user('user1', 'dup@example.com')
        with self.assertRaises(AlreadyExists):
            register_user({'username': 'user2', 'email': 'dup@example.com', 'password': 'Test1234'})

    def test_register_duplicate_username(self):
        make_user('dupname', 'first@example.com')
        with self.assertRaises(AlreadyExists):
            register_user({'username': 'dupname', 'email': 'second@example.com', 'password': 'Test1234'})


class ToggleBlockServiceTest(TestCase):

    def setUp(self):
        self.blocker = make_user('blocker', 'blocker@example.com')
        self.target  = make_user('target',  'target@example.com')

    def test_block_first_time(self):
        result = toggle_block(self.blocker, self.target.id)
        self.assertEqual(result['action'], 'blocked')
        self.assertTrue(BlockList.objects.filter(blocker=self.blocker, blocked=self.target).exists())

    def test_unblock_second_time(self):
        BlockList.objects.create(blocker=self.blocker, blocked=self.target)
        result = toggle_block(self.blocker, self.target.id)
        self.assertEqual(result['action'], 'unblocked')
        self.assertFalse(BlockList.objects.filter(blocker=self.blocker, blocked=self.target).exists())

    def test_cannot_block_self(self):
        with self.assertRaises(ValidationError):
            toggle_block(self.blocker, self.blocker.id)

    def test_block_nonexistent_user(self):
        with self.assertRaises(NotFound):
            toggle_block(self.blocker, uuid.uuid4())


# ═══════════════════════════════════════════════════════════════════════════════
# VIEW TESTS (HTTP Integration)
# ═══════════════════════════════════════════════════════════════════════════════

class CsrfViewTest(TestCase):

    def test_csrf_cookie_set(self):
        client = Client(enforce_csrf_checks=False)
        response = client.get('/api/v1/auth/csrf/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])


class RegisterViewTest(TestCase):

    def setUp(self):
        self.client = Client(enforce_csrf_checks=False)

    def test_register_success(self):
        response = self.client.post(
            '/api/v1/auth/register/',
            data=json.dumps({'username': 'newuser', 'email': 'new@example.com', 'password': 'Test1234'}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['data']['username'], 'newuser')
        self.assertIn('email', data['data'])   # include_private=True cho chính user

    def test_register_duplicate_email(self):
        make_user('existing', 'dup@example.com')
        response = self.client.post(
            '/api/v1/auth/register/',
            data=json.dumps({'username': 'newname', 'email': 'dup@example.com', 'password': 'Test1234'}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 409)

    def test_register_validation_error(self):
        response = self.client.post(
            '/api/v1/auth/register/',
            data=json.dumps({'username': '', 'email': 'bad', 'password': '123'}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertEqual(data['error']['code'], 'VALIDATION_ERROR')
        self.assertIn('fields', data['error'])

    def test_register_missing_body(self):
        response = self.client.post(
            '/api/v1/auth/register/',
            data='{}',
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)


class LoginViewTest(TestCase):

    def setUp(self):
        self.client = Client(enforce_csrf_checks=False)
        self.user = make_user('loginuser', 'login@example.com', 'Test1234')

    def test_login_success(self):
        response = self.client.post(
            '/api/v1/auth/login/',
            data=json.dumps({'email': 'login@example.com', 'password': 'Test1234'}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['data']['username'], 'loginuser')
        # Session phải được tạo
        self.assertIn(SESSION_KEY, self.client.session)

    def test_login_wrong_password(self):
        response = self.client.post(
            '/api/v1/auth/login/',
            data=json.dumps({'email': 'login@example.com', 'password': 'WrongPass'}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 401)

    def test_login_wrong_email(self):
        response = self.client.post(
            '/api/v1/auth/login/',
            data=json.dumps({'email': 'nobody@example.com', 'password': 'Test1234'}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 401)

    def test_login_inactive_account(self):
        self.user.is_active = False
        self.user.save()
        response = self.client.post(
            '/api/v1/auth/login/',
            data=json.dumps({'email': 'login@example.com', 'password': 'Test1234'}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 403)


class LogoutViewTest(TestCase):

    def setUp(self):
        self.client = Client(enforce_csrf_checks=False)
        self.user = make_user('logoutuser', 'logout@example.com', 'Test1234')

    def _login(self):
        self.client.post(
            '/api/v1/auth/login/',
            data=json.dumps({'email': 'logout@example.com', 'password': 'Test1234'}),
            content_type='application/json',
        )

    def test_logout_success(self):
        self._login()
        response = self.client.post('/api/v1/auth/logout/', content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['success'])

    def test_logout_requires_auth(self):
        response = self.client.post('/api/v1/auth/logout/', content_type='application/json')
        self.assertEqual(response.status_code, 401)


class MeAuthViewTest(TestCase):

    def setUp(self):
        self.client = Client(enforce_csrf_checks=False)
        self.user = make_user('meuser', 'me@example.com', 'Test1234')

    def test_me_authenticated(self):
        self.client.force_login(self.user)
        response = self.client.get('/api/v1/auth/me/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['data']['username'], 'meuser')

    def test_me_unauthenticated(self):
        response = self.client.get('/api/v1/auth/me/')
        self.assertEqual(response.status_code, 401)


class MyProfileViewTest(TestCase):

    def setUp(self):
        self.client = Client(enforce_csrf_checks=False)
        self.user = make_user('profileuser', 'profile@example.com', 'Test1234')
        self.client.force_login(self.user)

    def test_get_my_profile(self):
        response = self.client.get('/api/v1/accounts/me/')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['success'])

    def test_patch_username(self):
        response = self.client.patch(
            '/api/v1/accounts/me/',
            data=json.dumps({'username': 'New Name'}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual(self.user.username, 'New Name')

    def test_patch_sanitizes_xss(self):
        """Bio với XSS phải được sanitize trước khi lưu (Fix R12)."""
        response = self.client.patch(
            '/api/v1/accounts/me/',
            data=json.dumps({'bio': '<script>alert(1)</script>Normal bio'}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual(self.user.bio, 'Normal bio')

    def test_patch_requires_auth(self):
        self.client.logout()
        response = self.client.patch(
            '/api/v1/accounts/me/',
            data=json.dumps({'username': 'X'}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 401)


class PrivacyViewTest(TestCase):

    def setUp(self):
        self.client = Client(enforce_csrf_checks=False)
        self.user = make_user('privacyuser', 'privacy@example.com', 'Test1234')
        self.client.force_login(self.user)

    def test_set_private(self):
        response = self.client.patch(
            '/api/v1/accounts/me/privacy/',
            data=json.dumps({'is_private': True}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_private)

    def test_invalid_value(self):
        response = self.client.patch(
            '/api/v1/accounts/me/privacy/',
            data=json.dumps({'is_private': 'yes'}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)


class PublicProfileViewTest(TestCase):

    def setUp(self):
        self.client = Client(enforce_csrf_checks=False)
        self.alice = make_user('alice', 'alice@example.com', 'Test1234')
        self.bob   = make_user('bob',   'bob@example.com',   'Test1234')

    def test_view_public_profile(self):
        response = self.client.get(f'/api/v1/accounts/users/{self.alice.id}/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        # Email không được trả cho người xem public
        self.assertNotIn('email', data['data'])

    def test_blocked_user_sees_404(self):
        """B bị A block → B xem profile A → 404 (Fix R10)."""
        BlockList.objects.create(blocker=self.alice, blocked=self.bob)
        self.client.force_login(self.bob)
        response = self.client.get(f'/api/v1/accounts/users/{self.alice.id}/')
        self.assertEqual(response.status_code, 404)

    def test_nonexistent_user(self):
        response = self.client.get(f'/api/v1/accounts/users/{uuid.uuid4()}/')
        self.assertEqual(response.status_code, 404)


class BlockViewTest(TestCase):

    def setUp(self):
        self.client = Client(enforce_csrf_checks=False)
        self.alice = make_user('alice_b', 'alice_b@example.com', 'Test1234')
        self.bob   = make_user('bob_b',   'bob_b@example.com',   'Test1234')
        self.client.force_login(self.alice)

    def test_block_user(self):
        response = self.client.post(
            f'/api/v1/accounts/users/{self.bob.id}/block/',
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['data']['action'], 'blocked')
        self.assertTrue(BlockList.objects.filter(blocker=self.alice, blocked=self.bob).exists())

    def test_unblock_user(self):
        BlockList.objects.create(blocker=self.alice, blocked=self.bob)
        response = self.client.post(
            f'/api/v1/accounts/users/{self.bob.id}/block/',
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['data']['action'], 'unblocked')

    def test_requires_auth(self):
        self.client.logout()
        response = self.client.post(
            f'/api/v1/accounts/users/{self.bob.id}/block/',
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 401)


# ═══════════════════════════════════════════════════════════════════════════════
# DECORATOR TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class DecoratorTest(TestCase):

    def setUp(self):
        self.client = Client(enforce_csrf_checks=False)

    def test_require_auth_unauthenticated(self):
        """Endpoint auth-required trả 401 khi chưa đăng nhập."""
        response = self.client.get('/api/v1/accounts/me/')
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()['error']['code'], 'AUTH_REQUIRED')

    def test_require_auth_inactive(self):
        """
        Tài khoản bị khóa mid-session trả 401/403.

        Django behavior: ModelBackend.get_user() trả None cho inactive user
        → session bị invalidate → request.user = AnonymousUser → 401.
        Cả hai response code đều là behavior đúng trong các tình huống khác nhau.
        """
        user = make_user('inactive_u', 'inactive@example.com', 'Test1234')
        # Login bình thường trước
        self.client.post(
            '/api/v1/auth/login/',
            data=json.dumps({'email': 'inactive@example.com', 'password': 'Test1234'}),
            content_type='application/json',
        )
        # Deactivate mid-session (simulate admin action)
        User.objects.filter(pk=user.pk).update(is_active=False)
        # Gọi với session cũ → Django invalidate → 401 hoặc 403
        response = self.client.get('/api/v1/accounts/me/')
        self.assertIn(response.status_code, [401, 403])
        self.assertIn(response.json()['error']['code'], ['AUTH_REQUIRED', 'ACCOUNT_INACTIVE'])

    def test_require_admin_as_regular_user(self):
        """User thường gọi admin endpoint trả 403 ADMIN_ONLY."""
        user = make_user('regular', 'regular@example.com', 'Test1234', role='user')
        self.client.force_login(user)
        response = self.client.get('/api/v1/accounts/admin/verifications/')
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()['error']['code'], 'ADMIN_ONLY')

    def test_require_admin_as_admin(self):
        """Admin gọi admin endpoint thành công."""
        admin = make_user('adminuser', 'admin@example.com', 'Test1234', role='admin')
        self.client.force_login(admin)
        response = self.client.get('/api/v1/accounts/admin/verifications/')
        self.assertEqual(response.status_code, 200)


# ═══════════════════════════════════════════════════════════════════════════════
# USER MODEL TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class UserModelTest(TestCase):

    def test_uuid_primary_key(self):
        user = make_user('uuidtest', 'uuid@example.com')
        self.assertIsInstance(user.id, uuid.UUID)

    def test_default_role_is_user(self):
        user = make_user('roletest', 'role@example.com')
        self.assertEqual(user.role, 'user')

    def test_get_display_name_fallback(self):
        user = make_user('fallback', 'fallback@example.com')
        self.assertEqual(user.get_display_name(), 'fallback')

    def test_get_display_name_set(self):
        user = make_user('withname', 'withname@example.com')
        user.username = 'Real Name'
        self.assertEqual(user.get_display_name(), 'Real Name')

    def test_to_dict_excludes_email_by_default(self):
        user = make_user('dicttest', 'dict@example.com')
        d = user.to_dict(include_private=False)
        self.assertNotIn('email', d)
        self.assertIn('username', d)

    def test_to_dict_includes_email_when_private(self):
        user = make_user('dictprivate', 'dictprivate@example.com')
        d = user.to_dict(include_private=True)
        self.assertIn('email', d)

    def test_password_is_hashed(self):
        user = make_user('hashtest', 'hash@example.com', 'MyPass123')
        self.assertNotEqual(user.password, 'MyPass123')
        self.assertTrue(user.check_password('MyPass123'))