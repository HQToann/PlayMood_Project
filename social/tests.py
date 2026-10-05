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
        from django.utils import timezone
        from datetime import timedelta

        Follow.objects.create(follower=self.alice, following=self.bob)
        a1 = create_friend_activity(user=self.bob, activity_type=FriendActivity.TYPE_MOOD, extra_text='First')
        a2 = create_friend_activity(user=self.bob, activity_type=FriendActivity.TYPE_MOOD, extra_text='Second')

        FriendActivity.objects.filter(id=a1.id).update(created_at=timezone.now() - timedelta(seconds=10))
        FriendActivity.objects.filter(id=a2.id).update(created_at=timezone.now())

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