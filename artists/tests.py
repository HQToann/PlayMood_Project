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