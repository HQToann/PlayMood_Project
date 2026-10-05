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