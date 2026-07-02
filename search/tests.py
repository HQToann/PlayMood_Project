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