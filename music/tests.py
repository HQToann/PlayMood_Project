"""
music/tests.py
==============
Unit tests cho app music - Tuan 2.

Chay tests:
    python manage.py test music --verbosity=2
    python manage.py test accounts music --verbosity=2

Coverage:
  - Models, Validators, Selectors, Services, Views
  - Fix R1 (F() atomic), Fix R8 (dedup 5 phut), Fix R10 (block policy)
"""

import json
import uuid
from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase, Client
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone

from accounts.models import User, BlockList
from music.models import (
    Genre, Song, Like, Rating, Comment, CommentLike, ListenHistory, Report,
)
from music.validators import (
    validate_genre, validate_song_create, validate_song_update,
    validate_rating, validate_comment, validate_report,
    validate_list_songs_params,
)
from music.selectors import (
    list_genres, get_genre_by_id, list_songs, get_song_by_id, get_song_detail,
    get_song_like_count, get_song_rating_stats, list_comments, get_comment_by_id,
    list_reports, get_report_by_id,
)
from music.services import (
    create_genre, update_genre, delete_genre,
    create_song, update_song, delete_song, publish_song, hide_song,
    admin_hide_song, admin_toggle_trending,
    record_play, clear_listen_history,
    toggle_like, upsert_rating,
    create_comment, delete_comment, admin_hide_comment, toggle_comment_like,
    create_report, resolve_report,
)
from music.exceptions import (
    SongNotFound, GenreNotFound, CommentNotFound, NotSongOwner,
    NotCommentOwner, BlockedByArtist, GenreHasSongs,
    SongAlreadyPublished, InvalidParentComment, ReportNotFound,
)
from accounts.exceptions import ValidationError


def make_user(username, email, password='Test1234', role='user', **kwargs):
    return User.objects.create_user(
        username=username, email=email, password=password, role=role, **kwargs
    )


def make_audio_file(name='song.mp3', content_type='audio/mpeg', size_bytes=1024):
    content = b'\x00' * size_bytes
    return SimpleUploadedFile(name, content, content_type=content_type)


def make_image_file(name='cover.jpg', content_type='image/jpeg', size_bytes=512):
    content = b'\x00' * size_bytes
    return SimpleUploadedFile(name, content, content_type=content_type)


def make_genre(name='Pop'):
    return Genre.objects.create(name=name, description=f'{name} description')


def make_song(artist, genre=None, status=Song.STATUS_PUBLISHED, **kwargs):
    if genre is None:
        genre = make_genre(f'Genre-{uuid.uuid4().hex[:6]}')
    defaults = {
        'title':    'Test Song',
        'artist':   artist,
        'genre':    genre,
        'duration': 200,
        'status':   status,
        'audio_file': make_audio_file(f'{uuid.uuid4().hex}.mp3'),
    }
    defaults.update(kwargs)
    return Song.objects.create(**defaults)


class GenreModelTest(TestCase):

    def test_slug_auto_generated(self):
        genre = Genre.objects.create(name='Nhac Pop')
        self.assertTrue(genre.slug)
        self.assertNotIn(' ', genre.slug)

    def test_slug_not_overwritten_if_set(self):
        genre = Genre.objects.create(name='Rock', slug='custom-rock-slug')
        self.assertEqual(genre.slug, 'custom-rock-slug')

    def test_to_dict_basic(self):
        genre = make_genre('Jazz')
        d = genre.to_dict()
        self.assertEqual(d['name'], 'Jazz')
        self.assertIn('slug', d)
        self.assertNotIn('song_count', d)

    def test_to_dict_with_song_count(self):
        genre = make_genre('Blues')
        artist = make_user('artist1', 'artist1@test.com', role='artist')
        make_song(artist, genre=genre, status=Song.STATUS_PUBLISHED)
        d = genre.to_dict(include_song_count=True)
        self.assertEqual(d['song_count'], 1)

    def test_unique_name_constraint(self):
        Genre.objects.create(name='Unique Genre')
        with self.assertRaises(Exception):
            Genre.objects.create(name='Unique Genre')


class SongModelTest(TestCase):

    def setUp(self):
        self.artist = make_user('songartist', 'songartist@test.com', role='artist')
        self.genre  = make_genre('Pop')

    def test_song_creation(self):
        song = make_song(self.artist, self.genre, title='My Song')
        self.assertEqual(song.title, 'My Song')
        self.assertEqual(song.status, Song.STATUS_PUBLISHED)
        self.assertEqual(song.play_count, 0)

    def test_default_status_is_draft(self):
        song = Song.objects.create(
            title='Draft Song', artist=self.artist, genre=self.genre,
            duration=100, audio_file=make_audio_file(),
        )
        self.assertEqual(song.status, Song.STATUS_DRAFT)

    def test_to_dict_basic_fields(self):
        song = make_song(self.artist, self.genre, title='Dict Test')
        d = song.to_dict(include_stats=False)
        self.assertEqual(d['title'], 'Dict Test')
        self.assertEqual(d['artist']['username'], self.artist.username)
        self.assertNotIn('like_count', d)

    def test_to_dict_with_stats(self):
        song = make_song(self.artist, self.genre)
        d = song.to_dict(include_stats=True)
        self.assertEqual(d['like_count'], 0)
        self.assertEqual(d['rating_count'], 0)
        self.assertIsNone(d['avg_rating'])

    def test_to_dict_with_viewer_is_liked(self):
        song = make_song(self.artist, self.genre)
        viewer = make_user('viewer1', 'viewer1@test.com')
        Like.objects.create(user=viewer, song=song)
        d = song.to_dict(viewer=viewer)
        self.assertTrue(d['is_liked'])

    def test_to_dict_with_viewer_my_rating(self):
        song = make_song(self.artist, self.genre)
        viewer = make_user('viewer2', 'viewer2@test.com')
        Rating.objects.create(user=viewer, song=song, score=4)
        d = song.to_dict(viewer=viewer)
        self.assertEqual(d['my_rating'], 4)


class CommentModelTest(TestCase):

    def setUp(self):
        self.artist = make_user('cartist', 'cartist@test.com', role='artist')
        self.song   = make_song(self.artist)
        self.user   = make_user('cuser', 'cuser@test.com')

    def test_root_comment_to_dict(self):
        c = Comment.objects.create(user=self.user, song=self.song, content='Hello')
        d = c.to_dict()
        self.assertEqual(d['content'], 'Hello')
        self.assertIsNone(d['parent_id'])

    def test_reply_to_dict_has_parent_id(self):
        root  = Comment.objects.create(user=self.user, song=self.song, content='Root')
        reply = Comment.objects.create(user=self.user, song=self.song, content='Reply', parent=root)
        d = reply.to_dict()
        self.assertEqual(d['parent_id'], str(root.id))

    def test_to_dict_include_replies(self):
        root = Comment.objects.create(user=self.user, song=self.song, content='Root')
        Comment.objects.create(user=self.user, song=self.song, content='Reply1', parent=root)
        d = root.to_dict(include_replies=True)
        self.assertEqual(len(d['replies']), 1)

    def test_hidden_reply_excluded_from_replies(self):
        root = Comment.objects.create(user=self.user, song=self.song, content='Root')
        Comment.objects.create(
            user=self.user, song=self.song, content='Hidden Reply',
            parent=root, is_hidden=True,
        )
        d = root.to_dict(include_replies=True)
        self.assertEqual(len(d['replies']), 0)


class ValidateGenreTest(TestCase):

    def test_valid_data(self):
        result = validate_genre({'name': 'Pop', 'description': 'desc'})
        self.assertEqual(result['name'], 'Pop')

    def test_missing_name(self):
        with self.assertRaises(ValidationError) as ctx:
            validate_genre({'description': 'desc'})
        self.assertIn('name', ctx.exception.fields)

    def test_name_too_long(self):
        with self.assertRaises(ValidationError):
            validate_genre({'name': 'x' * 101})

    def test_description_sanitized(self):
        result = validate_genre({'name': 'Rock', 'description': '<script>alert(1)</script>desc'})
        self.assertEqual(result['description'], 'desc')


class ValidateSongCreateTest(TestCase):

    def setUp(self):
        self.genre_id = str(uuid.uuid4())
        self.base_data = {
            'title': 'My Song',
            'genre_id': self.genre_id,
            'duration': '200',
        }

    def test_valid_data(self):
        files = {'audio_file': make_audio_file()}
        result = validate_song_create(self.base_data, files)
        self.assertEqual(result['title'], 'My Song')
        self.assertEqual(result['duration'], 200)

    def test_missing_title(self):
        data = {**self.base_data, 'title': ''}
        files = {'audio_file': make_audio_file()}
        with self.assertRaises(ValidationError) as ctx:
            validate_song_create(data, files)
        self.assertIn('title', ctx.exception.fields)

    def test_missing_audio_file(self):
        with self.assertRaises(ValidationError) as ctx:
            validate_song_create(self.base_data, {})
        self.assertIn('audio_file', ctx.exception.fields)

    def test_invalid_audio_mime_type(self):
        files = {'audio_file': SimpleUploadedFile('file.txt', b'data', content_type='text/plain')}
        with self.assertRaises(ValidationError) as ctx:
            validate_song_create(self.base_data, files)
        self.assertIn('audio_file', ctx.exception.fields)

    def test_audio_file_too_large(self):
        files = {'audio_file': make_audio_file(size_bytes=60 * 1024 * 1024)}
        with self.assertRaises(ValidationError) as ctx:
            validate_song_create(self.base_data, files)
        self.assertIn('audio_file', ctx.exception.fields)

    def test_invalid_genre_id_format(self):
        data = {**self.base_data, 'genre_id': 'not-a-uuid'}
        files = {'audio_file': make_audio_file()}
        with self.assertRaises(ValidationError) as ctx:
            validate_song_create(data, files)
        self.assertIn('genre_id', ctx.exception.fields)

    def test_invalid_duration(self):
        data = {**self.base_data, 'duration': '-5'}
        files = {'audio_file': make_audio_file()}
        with self.assertRaises(ValidationError) as ctx:
            validate_song_create(data, files)
        self.assertIn('duration', ctx.exception.fields)

    def test_cover_image_valid(self):
        files = {'audio_file': make_audio_file(), 'cover_image': make_image_file()}
        result = validate_song_create(self.base_data, files)
        self.assertEqual(result['title'], 'My Song')

    def test_cover_image_invalid_mime(self):
        files = {
            'audio_file': make_audio_file(),
            'cover_image': SimpleUploadedFile('cover.txt', b'data', content_type='text/plain'),
        }
        with self.assertRaises(ValidationError) as ctx:
            validate_song_create(self.base_data, files)
        self.assertIn('cover_image', ctx.exception.fields)

    def test_lyrics_sanitized(self):
        data = {**self.base_data, 'lyrics': '<script>x</script>Lyrics here'}
        files = {'audio_file': make_audio_file()}
        result = validate_song_create(data, files)
        self.assertEqual(result['lyrics'], 'Lyrics here')

    def test_allow_download_string_true(self):
        data = {**self.base_data, 'allow_download': 'true'}
        files = {'audio_file': make_audio_file()}
        result = validate_song_create(data, files)
        self.assertTrue(result['allow_download'])


class ValidateSongUpdateTest(TestCase):

    def test_partial_update_title_only(self):
        result = validate_song_update({'title': 'New Title'}, {})
        self.assertEqual(result, {'title': 'New Title'})

    def test_empty_title_raises(self):
        with self.assertRaises(ValidationError):
            validate_song_update({'title': ''}, {})

    def test_lyrics_sanitized(self):
        result = validate_song_update({'lyrics': '<b>bold</b>text'}, {})
        self.assertEqual(result['lyrics'], 'boldtext')

    def test_no_fields_returns_empty_dict(self):
        result = validate_song_update({}, {})
        self.assertEqual(result, {})


class ValidateRatingTest(TestCase):

    def test_valid_score(self):
        result = validate_rating({'score': 5})
        self.assertEqual(result['score'], 5)

    def test_score_out_of_range_high(self):
        with self.assertRaises(ValidationError):
            validate_rating({'score': 6})

    def test_score_out_of_range_low(self):
        with self.assertRaises(ValidationError):
            validate_rating({'score': 0})

    def test_score_not_a_number(self):
        with self.assertRaises(ValidationError):
            validate_rating({'score': 'abc'})


class ValidateCommentTest(TestCase):

    def test_valid_comment(self):
        result = validate_comment({'content': 'Nice song!'})
        self.assertEqual(result['content'], 'Nice song!')
        self.assertIsNone(result['parent_id'])

    def test_empty_content_raises(self):
        with self.assertRaises(ValidationError):
            validate_comment({'content': ''})

    def test_content_too_long(self):
        with self.assertRaises(ValidationError):
            validate_comment({'content': 'x' * 2001})

    def test_content_xss_sanitized(self):
        result = validate_comment({'content': '<script>alert(1)</script>Great!'})
        self.assertEqual(result['content'], 'Great!')

    def test_valid_parent_id(self):
        pid = str(uuid.uuid4())
        result = validate_comment({'content': 'Reply', 'parent_id': pid})
        self.assertEqual(str(result['parent_id']), pid)

    def test_invalid_parent_id_format(self):
        with self.assertRaises(ValidationError):
            validate_comment({'content': 'Reply', 'parent_id': 'not-a-uuid'})


class ValidateReportTest(TestCase):

    def test_valid_report(self):
        result = validate_report({
            'target_type': 'song',
            'target_id': str(uuid.uuid4()),
            'reason': 'copyright',
            'description': 'Vi pham ban quyen',
        })
        self.assertEqual(result['target_type'], 'song')

    def test_invalid_target_type(self):
        with self.assertRaises(ValidationError) as ctx:
            validate_report({
                'target_type': 'invalid',
                'target_id': str(uuid.uuid4()),
                'reason': 'spam',
            })
        self.assertIn('target_type', ctx.exception.fields)

    def test_invalid_reason(self):
        with self.assertRaises(ValidationError) as ctx:
            validate_report({
                'target_type': 'song',
                'target_id': str(uuid.uuid4()),
                'reason': 'invalid_reason',
            })
        self.assertIn('reason', ctx.exception.fields)

    def test_invalid_target_id(self):
        with self.assertRaises(ValidationError) as ctx:
            validate_report({
                'target_type': 'song',
                'target_id': 'not-a-uuid',
                'reason': 'spam',
            })
        self.assertIn('target_id', ctx.exception.fields)


class ValidateListSongsParamsTest(TestCase):

    def test_defaults(self):
        result = validate_list_songs_params({})
        self.assertEqual(result['page'], 1)
        self.assertEqual(result['page_size'], 20)
        self.assertEqual(result['ordering'], '-created_at')

    def test_page_size_capped_at_100(self):
        result = validate_list_songs_params({'page_size': '500'})
        self.assertEqual(result['page_size'], 100)

    def test_invalid_ordering_falls_back(self):
        result = validate_list_songs_params({'ordering': 'invalid_field'})
        self.assertEqual(result['ordering'], '-created_at')

    def test_valid_ordering_accepted(self):
        result = validate_list_songs_params({'ordering': '-play_count'})
        self.assertEqual(result['ordering'], '-play_count')

    def test_negative_page_corrected(self):
        result = validate_list_songs_params({'page': '-5'})
        self.assertEqual(result['page'], 1)


class GenreSelectorTest(TestCase):

    def test_list_genres_empty(self):
        result = list_genres()
        self.assertEqual(result, [])

    def test_list_genres_with_data(self):
        make_genre('Pop')
        make_genre('Rock')
        result = list_genres()
        self.assertEqual(len(result), 2)

    def test_get_genre_by_id_found(self):
        genre = make_genre('Jazz')
        result = get_genre_by_id(genre.id)
        self.assertEqual(result.name, 'Jazz')

    def test_get_genre_by_id_not_found(self):
        with self.assertRaises(GenreNotFound):
            get_genre_by_id(uuid.uuid4())


class SongSelectorTest(TestCase):

    def setUp(self):
        self.artist  = make_user('selartist', 'selartist@test.com', role='artist')
        self.genre   = make_genre('Pop')
        self.viewer  = make_user('selviewer', 'selviewer@test.com')

    def test_list_songs_only_published_for_anonymous(self):
        make_song(self.artist, self.genre, status=Song.STATUS_PUBLISHED, title='Pub')
        make_song(self.artist, self.genre, status=Song.STATUS_DRAFT, title='Draft')

        from django.contrib.auth.models import AnonymousUser
        result = list_songs({'page': 1, 'page_size': 20, 'ordering': '-created_at'}, viewer=AnonymousUser())
        titles = [s['title'] for s in result['items']]
        self.assertIn('Pub', titles)
        self.assertNotIn('Draft', titles)

    def test_list_songs_artist_sees_own_draft(self):
        make_song(self.artist, self.genre, status=Song.STATUS_DRAFT, title='MyDraft')
        result = list_songs({'page': 1, 'page_size': 20, 'ordering': '-created_at'}, viewer=self.artist)
        titles = [s['title'] for s in result['items']]
        self.assertIn('MyDraft', titles)

    def test_list_songs_filter_by_query(self):
        make_song(self.artist, self.genre, title='Shape of You')
        make_song(self.artist, self.genre, title='Perfect')
        result = list_songs({'q': 'shape', 'page': 1, 'page_size': 20, 'ordering': '-created_at'}, viewer=self.viewer)
        self.assertEqual(len(result['items']), 1)

    def test_list_songs_pagination(self):
        for i in range(5):
            make_song(self.artist, self.genre, title=f'Song {i}')
        result = list_songs({'page': 1, 'page_size': 2, 'ordering': '-created_at'}, viewer=self.viewer)
        self.assertEqual(len(result['items']), 2)
        self.assertEqual(result['pagination']['total'], 5)
        self.assertEqual(result['pagination']['total_pages'], 3)

    def test_list_songs_excludes_blocked_artist(self):
        make_song(self.artist, self.genre, title='Blocked Artist Song')
        BlockList.objects.create(blocker=self.artist, blocked=self.viewer)
        result = list_songs({'page': 1, 'page_size': 20, 'ordering': '-created_at'}, viewer=self.viewer)
        titles = [s['title'] for s in result['items']]
        self.assertNotIn('Blocked Artist Song', titles)

    def test_get_song_detail_published_visible(self):
        song = make_song(self.artist, self.genre, status=Song.STATUS_PUBLISHED)
        result = get_song_detail(song.id, viewer=self.viewer)
        self.assertEqual(result.id, song.id)

    def test_get_song_detail_hidden_raises_notfound(self):
        song = make_song(self.artist, self.genre, status=Song.STATUS_HIDDEN)
        with self.assertRaises(SongNotFound):
            get_song_detail(song.id, viewer=self.viewer)

    def test_get_song_detail_draft_not_owner_raises(self):
        song = make_song(self.artist, self.genre, status=Song.STATUS_DRAFT)
        with self.assertRaises(SongNotFound):
            get_song_detail(song.id, viewer=self.viewer)

    def test_get_song_detail_draft_owner_can_view(self):
        song = make_song(self.artist, self.genre, status=Song.STATUS_DRAFT)
        result = get_song_detail(song.id, viewer=self.artist)
        self.assertEqual(result.id, song.id)

    def test_get_song_detail_blocked_viewer_raises_notfound(self):
        song = make_song(self.artist, self.genre, status=Song.STATUS_PUBLISHED)
        BlockList.objects.create(blocker=self.artist, blocked=self.viewer)
        with self.assertRaises(SongNotFound):
            get_song_detail(song.id, viewer=self.viewer)

    def test_get_song_by_id_not_found(self):
        with self.assertRaises(SongNotFound):
            get_song_by_id(uuid.uuid4())

    def test_get_song_like_count(self):
        song = make_song(self.artist, self.genre)
        Like.objects.create(user=self.viewer, song=song)
        result = get_song_like_count(song.id, viewer=self.viewer)
        self.assertEqual(result['like_count'], 1)
        self.assertTrue(result['is_liked'])

    def test_get_song_rating_stats(self):
        song = make_song(self.artist, self.genre)
        Rating.objects.create(user=self.viewer, song=song, score=4)
        result = get_song_rating_stats(song.id, viewer=self.viewer)
        self.assertEqual(result['avg_rating'], 4.0)
        self.assertEqual(result['my_rating'], 4)


class CommentSelectorTest(TestCase):

    def setUp(self):
        self.artist = make_user('comselartist', 'comselartist@test.com', role='artist')
        self.song   = make_song(self.artist)
        self.user   = make_user('comseluser', 'comseluser@test.com')

    def test_list_comments_excludes_hidden(self):
        Comment.objects.create(user=self.user, song=self.song, content='Visible')
        Comment.objects.create(user=self.user, song=self.song, content='Hidden', is_hidden=True)
        result = list_comments(self.song.id, viewer=self.user)
        contents = [c['content'] for c in result['items']]
        self.assertIn('Visible', contents)
        self.assertNotIn('Hidden', contents)

    def test_list_comments_only_root_in_items(self):
        root = Comment.objects.create(user=self.user, song=self.song, content='Root')
        Comment.objects.create(user=self.user, song=self.song, content='Reply', parent=root)
        result = list_comments(self.song.id, viewer=self.user)
        self.assertEqual(len(result['items']), 1)
        self.assertEqual(len(result['items'][0]['replies']), 1)

    def test_get_comment_by_id_not_found(self):
        with self.assertRaises(CommentNotFound):
            get_comment_by_id(uuid.uuid4())

    def test_get_comment_by_id_hidden_not_found(self):
        c = Comment.objects.create(user=self.user, song=self.song, content='X', is_hidden=True)
        with self.assertRaises(CommentNotFound):
            get_comment_by_id(c.id)


class ReportSelectorTest(TestCase):

    def setUp(self):
        self.reporter = make_user('reporter1', 'reporter1@test.com')

    def test_list_reports_filter_by_status(self):
        Report.objects.create(
            reporter=self.reporter, target_type='song', target_id=uuid.uuid4(),
            reason='spam', status=Report.STATUS_PENDING,
        )
        Report.objects.create(
            reporter=self.reporter, target_type='song', target_id=uuid.uuid4(),
            reason='spam', status=Report.STATUS_RESOLVED,
        )
        result = list_reports({'status': 'pending', 'page': 1, 'page_size': 20})
        self.assertEqual(len(result['items']), 1)

    def test_get_report_by_id_not_found(self):
        with self.assertRaises(ReportNotFound):
            get_report_by_id(uuid.uuid4())


class GenreServiceTest(TestCase):

    def test_create_genre_success(self):
        genre = create_genre({'name': 'Pop', 'description': 'desc'})
        self.assertEqual(genre.name, 'Pop')
        self.assertTrue(genre.slug)

    def test_create_genre_duplicate_raises(self):
        create_genre({'name': 'Pop', 'description': ''})
        with self.assertRaises(ValidationError):
            create_genre({'name': 'Pop', 'description': ''})

    def test_update_genre_success(self):
        genre = create_genre({'name': 'Old Name', 'description': ''})
        updated = update_genre(genre, {'name': 'New Name', 'description': 'new desc'})
        self.assertEqual(updated.name, 'New Name')

    def test_delete_genre_without_songs(self):
        genre = create_genre({'name': 'ToDelete', 'description': ''})
        delete_genre(genre)
        self.assertFalse(Genre.objects.filter(id=genre.id).exists())

    def test_delete_genre_with_songs_raises(self):
        artist = make_user('delartist', 'delartist@test.com', role='artist')
        genre  = create_genre({'name': 'HasSongs', 'description': ''})
        make_song(artist, genre)
        with self.assertRaises(GenreHasSongs):
            delete_genre(genre)


class SongServiceTest(TestCase):

    def setUp(self):
        self.artist  = make_user('svcartist', 'svcartist@test.com', role='artist')
        self.artist2 = make_user('svcartist2', 'svcartist2@test.com', role='artist')
        self.genre   = make_genre('Pop')

    def test_create_song_success(self):
        data = {
            'title': 'New Song', 'genre_id': self.genre.id,
            'duration': 200, 'lyrics': '', 'allow_download': False,
            'released_at': None,
        }
        files = {'audio_file': make_audio_file()}
        song = create_song(self.artist, data, files)
        self.assertEqual(song.title, 'New Song')
        self.assertEqual(song.status, Song.STATUS_DRAFT)

    def test_create_song_with_cover(self):
        data = {
            'title': 'Song With Cover', 'genre_id': self.genre.id,
            'duration': 200, 'lyrics': '', 'allow_download': False,
            'released_at': None,
        }
        files = {'audio_file': make_audio_file(), 'cover_image': make_image_file()}
        song = create_song(self.artist, data, files)
        self.assertTrue(song.cover_image)

    def test_update_song_by_owner(self):
        song = make_song(self.artist, self.genre, title='Original')
        updated = update_song(song, self.artist, {'title': 'Updated'}, {})
        self.assertEqual(updated.title, 'Updated')

    def test_update_song_not_owner_raises(self):
        song = make_song(self.artist, self.genre)
        with self.assertRaises(NotSongOwner):
            update_song(song, self.artist2, {'title': 'Hack'}, {})

    def test_delete_song_by_owner(self):
        song = make_song(self.artist, self.genre)
        delete_song(song, self.artist)
        self.assertFalse(Song.objects.filter(id=song.id).exists())

    def test_delete_song_not_owner_raises(self):
        song = make_song(self.artist, self.genre)
        with self.assertRaises(NotSongOwner):
            delete_song(song, self.artist2)

    def test_publish_song_from_draft(self):
        song = make_song(self.artist, self.genre, status=Song.STATUS_DRAFT)
        published = publish_song(song, self.artist)
        self.assertEqual(published.status, Song.STATUS_PUBLISHED)
        self.assertIsNotNone(published.released_at)

    def test_publish_song_not_owner_raises(self):
        song = make_song(self.artist, self.genre, status=Song.STATUS_DRAFT)
        with self.assertRaises(NotSongOwner):
            publish_song(song, self.artist2)

    def test_publish_song_already_published_raises(self):
        song = make_song(self.artist, self.genre, status=Song.STATUS_PUBLISHED)
        with self.assertRaises(SongAlreadyPublished):
            publish_song(song, self.artist)

    def test_hide_song_by_owner(self):
        song = make_song(self.artist, self.genre, status=Song.STATUS_PUBLISHED)
        hidden = hide_song(song, self.artist)
        self.assertEqual(hidden.status, Song.STATUS_HIDDEN)

    def test_hide_song_not_owner_raises(self):
        song = make_song(self.artist, self.genre)
        with self.assertRaises(NotSongOwner):
            hide_song(song, self.artist2)

    def test_admin_hide_song(self):
        song = make_song(self.artist, self.genre, status=Song.STATUS_PUBLISHED)
        hidden = admin_hide_song(song)
        self.assertEqual(hidden.status, Song.STATUS_HIDDEN)

    def test_admin_toggle_trending(self):
        song = make_song(self.artist, self.genre, is_trending=False)
        toggled = admin_toggle_trending(song)
        self.assertTrue(toggled.is_trending)
        toggled2 = admin_toggle_trending(song)
        self.assertFalse(toggled2.is_trending)


class RecordPlayServiceTest(TestCase):
    """Test ky Fix R1 (F() atomic) va Fix R8 (dedup 5 phut)."""

    def setUp(self):
        self.artist = make_user('playartist', 'playartist@test.com', role='artist')
        self.song   = make_song(self.artist, status=Song.STATUS_PUBLISHED)
        self.user   = make_user('playuser', 'playuser@test.com')

    def test_record_play_increments_count(self):
        count = record_play(self.user, self.song)
        self.assertEqual(count, 1)

    def test_record_play_creates_listen_history(self):
        record_play(self.user, self.song)
        self.assertTrue(
            ListenHistory.objects.filter(user=self.user, song=self.song).exists()
        )

    def test_record_play_dedup_within_5_minutes(self):
        record_play(self.user, self.song)
        count2 = record_play(self.user, self.song)
        self.assertEqual(count2, 1)

    def test_record_play_after_5_minutes_increments(self):
        record_play(self.user, self.song)
        old_time = timezone.now() - timedelta(minutes=10)
        ListenHistory.objects.filter(user=self.user, song=self.song).update(listened_at=old_time)

        count2 = record_play(self.user, self.song)
        self.assertEqual(count2, 2)

    def test_record_play_atomic_no_race_condition(self):
        users = [make_user(f'raceuser{i}', f'raceuser{i}@test.com') for i in range(5)]
        for u in users:
            record_play(u, self.song)
        self.song.refresh_from_db()
        self.assertEqual(self.song.play_count, 5)

    def test_clear_listen_history(self):
        record_play(self.user, self.song)
        deleted_count = clear_listen_history(self.user)
        self.assertEqual(deleted_count, 1)
        self.assertEqual(ListenHistory.objects.filter(user=self.user).count(), 0)


class LikeServiceTest(TestCase):

    def setUp(self):
        self.artist = make_user('likeartist', 'likeartist@test.com', role='artist')
        self.song   = make_song(self.artist)
        self.user   = make_user('likeuser', 'likeuser@test.com')

    def test_toggle_like_first_time(self):
        result = toggle_like(self.user, self.song)
        self.assertEqual(result['action'], 'liked')
        self.assertEqual(result['like_count'], 1)

    def test_toggle_like_second_time_unlikes(self):
        toggle_like(self.user, self.song)
        result = toggle_like(self.user, self.song)
        self.assertEqual(result['action'], 'unliked')
        self.assertEqual(result['like_count'], 0)


class RatingServiceTest(TestCase):

    def setUp(self):
        self.artist = make_user('rateartist', 'rateartist@test.com', role='artist')
        self.song   = make_song(self.artist)
        self.user   = make_user('rateuser', 'rateuser@test.com')

    def test_upsert_rating_first_time(self):
        result = upsert_rating(self.user, self.song, 5)
        self.assertEqual(result['score'], 5)
        self.assertEqual(result['avg_rating'], 5.0)

    def test_upsert_rating_updates_existing(self):
        upsert_rating(self.user, self.song, 5)
        result = upsert_rating(self.user, self.song, 2)
        self.assertEqual(result['score'], 2)
        self.assertEqual(result['rating_count'], 1)


class CommentServiceTest(TestCase):

    def setUp(self):
        self.artist = make_user('comsvcartist', 'comsvcartist@test.com', role='artist')
        self.song   = make_song(self.artist)
        self.user   = make_user('comsvcuser', 'comsvcuser@test.com')

    def test_create_comment_success(self):
        comment = create_comment(self.user, self.song, {'content': 'Nice!', 'parent_id': None})
        self.assertEqual(comment.content, 'Nice!')

    def test_create_comment_blocked_by_artist_raises(self):
        BlockList.objects.create(blocker=self.artist, blocked=self.user)
        with self.assertRaises(BlockedByArtist):
            create_comment(self.user, self.song, {'content': 'Hi', 'parent_id': None})

    def test_create_reply_success(self):
        root = Comment.objects.create(user=self.user, song=self.song, content='Root')
        reply = create_comment(self.user, self.song, {'content': 'Reply', 'parent_id': root.id})
        self.assertEqual(reply.parent_id, root.id)

    def test_create_reply_of_reply_raises(self):
        root  = Comment.objects.create(user=self.user, song=self.song, content='Root')
        reply = Comment.objects.create(user=self.user, song=self.song, content='Reply', parent=root)
        with self.assertRaises(InvalidParentComment):
            create_comment(self.user, self.song, {'content': 'Reply2', 'parent_id': reply.id})

    def test_create_comment_invalid_parent_raises(self):
        with self.assertRaises(InvalidParentComment):
            create_comment(self.user, self.song, {'content': 'X', 'parent_id': uuid.uuid4()})

    def test_delete_comment_by_owner(self):
        c = Comment.objects.create(user=self.user, song=self.song, content='Delete me')
        delete_comment(c, self.user)
        self.assertFalse(Comment.objects.filter(id=c.id).exists())

    def test_delete_comment_not_owner_raises(self):
        other = make_user('otheruser', 'otheruser@test.com')
        c = Comment.objects.create(user=self.user, song=self.song, content='Not yours')
        with self.assertRaises(NotCommentOwner):
            delete_comment(c, other)

    def test_admin_hide_comment(self):
        c = Comment.objects.create(user=self.user, song=self.song, content='Bad comment')
        hidden = admin_hide_comment(c)
        self.assertTrue(hidden.is_hidden)

    def test_toggle_comment_like(self):
        c = Comment.objects.create(user=self.user, song=self.song, content='Likable')
        result = toggle_comment_like(self.user, c)
        self.assertEqual(result['action'], 'liked')
        result2 = toggle_comment_like(self.user, c)
        self.assertEqual(result2['action'], 'unliked')


class ReportServiceTest(TestCase):

    def setUp(self):
        self.reporter = make_user('reportuser', 'reportuser@test.com')
        self.admin    = make_user('reportadmin', 'reportadmin@test.com', role='admin')

    def test_create_report(self):
        report = create_report(self.reporter, {
            'target_type': 'song', 'target_id': uuid.uuid4(),
            'reason': 'spam', 'description': '',
        })
        self.assertEqual(report.status, Report.STATUS_PENDING)

    def test_resolve_report_resolved(self):
        report = create_report(self.reporter, {
            'target_type': 'song', 'target_id': uuid.uuid4(),
            'reason': 'spam', 'description': '',
        })
        resolved = resolve_report(report, self.admin, 'resolved', 'Da xu ly')
        self.assertEqual(resolved.status, 'resolved')
        self.assertEqual(resolved.resolved_by, self.admin)

    def test_resolve_report_invalid_action_raises(self):
        report = create_report(self.reporter, {
            'target_type': 'song', 'target_id': uuid.uuid4(),
            'reason': 'spam', 'description': '',
        })
        with self.assertRaises(ValidationError):
            resolve_report(report, self.admin, 'invalid_action', '')


class GenreViewTest(TestCase):

    def setUp(self):
        self.client = Client(enforce_csrf_checks=False)
        self.admin  = make_user('genreadmin', 'genreadmin@test.com', role='admin')
        self.user   = make_user('genreuser', 'genreuser@test.com')

    def test_list_genres_public(self):
        make_genre('Pop')
        response = self.client.get('/api/v1/music/genres/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data['data']['items']), 1)

    def test_create_genre_as_admin(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            '/api/v1/music/genres/',
            data=json.dumps({'name': 'Rock', 'description': 'desc'}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 201)

    def test_create_genre_as_user_forbidden(self):
        self.client.force_login(self.user)
        response = self.client.post(
            '/api/v1/music/genres/',
            data=json.dumps({'name': 'Rock'}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 403)

    def test_create_genre_unauthenticated(self):
        response = self.client.post(
            '/api/v1/music/genres/',
            data=json.dumps({'name': 'Rock'}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 401)

    def test_update_genre_as_admin(self):
        genre = make_genre('OldName')
        self.client.force_login(self.admin)
        response = self.client.put(
            f'/api/v1/music/genres/{genre.id}/',
            data=json.dumps({'name': 'NewName', 'description': ''}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)

    def test_delete_genre_as_admin(self):
        genre = make_genre('ToDelete')
        self.client.force_login(self.admin)
        response = self.client.delete(f'/api/v1/music/genres/{genre.id}/')
        self.assertEqual(response.status_code, 204)

    def test_delete_genre_not_found(self):
        self.client.force_login(self.admin)
        response = self.client.delete(f'/api/v1/music/genres/{uuid.uuid4()}/')
        self.assertEqual(response.status_code, 404)


class SongUploadViewTest(TestCase):

    def setUp(self):
        self.client = Client(enforce_csrf_checks=False)
        self.artist = make_user('uploadartist', 'uploadartist@test.com', role='artist')
        self.user   = make_user('uploaduser', 'uploaduser@test.com')
        self.genre  = make_genre('Pop')

    def test_upload_song_as_artist(self):
        self.client.force_login(self.artist)
        response = self.client.post(
            '/api/v1/music/songs/',
            data={
                'title': 'New Song',
                'genre_id': str(self.genre.id),
                'duration': '200',
                'audio_file': make_audio_file(),
            },
        )
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data['data']['status'], 'draft')

    def test_upload_song_as_user_forbidden(self):
        self.client.force_login(self.user)
        response = self.client.post(
            '/api/v1/music/songs/',
            data={
                'title': 'New Song',
                'genre_id': str(self.genre.id),
                'duration': '200',
                'audio_file': make_audio_file(),
            },
        )
        self.assertEqual(response.status_code, 403)

    def test_upload_song_invalid_mime(self):
        self.client.force_login(self.artist)
        response = self.client.post(
            '/api/v1/music/songs/',
            data={
                'title': 'New Song',
                'genre_id': str(self.genre.id),
                'duration': '200',
                'audio_file': SimpleUploadedFile('f.txt', b'data', content_type='text/plain'),
            },
        )
        self.assertEqual(response.status_code, 400)


class SongListViewTest(TestCase):

    def setUp(self):
        self.client = Client(enforce_csrf_checks=False)
        self.artist = make_user('listartist', 'listartist@test.com', role='artist')
        self.genre  = make_genre('Pop')

    def test_list_songs_public(self):
        make_song(self.artist, self.genre, status=Song.STATUS_PUBLISHED)
        response = self.client.get('/api/v1/music/songs/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data['data']['items']), 1)

    def test_list_songs_with_filters(self):
        make_song(self.artist, self.genre, title='Shape of You', status=Song.STATUS_PUBLISHED)
        response = self.client.get('/api/v1/music/songs/?q=shape')
        data = response.json()
        self.assertEqual(len(data['data']['items']), 1)

    def test_trending_songs_empty(self):
        response = self.client.get('/api/v1/music/songs/trending/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['data']['items'], [])


class SongDetailViewTest(TestCase):

    def setUp(self):
        self.client = Client(enforce_csrf_checks=False)
        self.artist = make_user('detailartist', 'detailartist@test.com', role='artist')
        self.other_artist = make_user('otherartist', 'otherartist@test.com', role='artist')
        self.genre  = make_genre('Pop')

    def test_get_published_song(self):
        song = make_song(self.artist, self.genre, status=Song.STATUS_PUBLISHED)
        response = self.client.get(f'/api/v1/music/songs/{song.id}/')
        self.assertEqual(response.status_code, 200)

    def test_get_hidden_song_404(self):
        song = make_song(self.artist, self.genre, status=Song.STATUS_HIDDEN)
        response = self.client.get(f'/api/v1/music/songs/{song.id}/')
        self.assertEqual(response.status_code, 404)

    def test_patch_song_as_owner(self):
        song = make_song(self.artist, self.genre)
        self.client.force_login(self.artist)
        response = self.client.patch(
            f'/api/v1/music/songs/{song.id}/',
            data=json.dumps({'title': 'Updated Title'}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)

    def test_patch_song_not_owner_forbidden(self):
        song = make_song(self.artist, self.genre)
        self.client.force_login(self.other_artist)
        response = self.client.patch(
            f'/api/v1/music/songs/{song.id}/',
            data=json.dumps({'title': 'Hacked'}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 403)

    def test_delete_song_as_owner(self):
        song = make_song(self.artist, self.genre)
        self.client.force_login(self.artist)
        response = self.client.delete(f'/api/v1/music/songs/{song.id}/')
        self.assertEqual(response.status_code, 204)


class SongPublishViewTest(TestCase):

    def setUp(self):
        self.client = Client(enforce_csrf_checks=False)
        self.artist = make_user('pubartist', 'pubartist@test.com', role='artist')
        self.genre  = make_genre('Pop')

    def test_publish_song_success(self):
        song = make_song(self.artist, self.genre, status=Song.STATUS_DRAFT)
        self.client.force_login(self.artist)
        response = self.client.post(f'/api/v1/music/songs/{song.id}/publish/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['data']['status'], 'published')

    def test_publish_already_published_400(self):
        song = make_song(self.artist, self.genre, status=Song.STATUS_PUBLISHED)
        self.client.force_login(self.artist)
        response = self.client.post(f'/api/v1/music/songs/{song.id}/publish/')
        self.assertEqual(response.status_code, 400)


class SongPlayDownloadViewTest(TestCase):

    def setUp(self):
        self.client = Client(enforce_csrf_checks=False)
        self.artist = make_user('pdartist', 'pdartist@test.com', role='artist')
        self.genre  = make_genre('Pop')
        self.user   = make_user('pduser', 'pduser@test.com')

    def test_play_song_requires_auth(self):
        song = make_song(self.artist, self.genre, status=Song.STATUS_PUBLISHED)
        response = self.client.post(f'/api/v1/music/songs/{song.id}/play/')
        self.assertEqual(response.status_code, 401)

    def test_play_song_increments_count(self):
        song = make_song(self.artist, self.genre, status=Song.STATUS_PUBLISHED)
        self.client.force_login(self.user)
        response = self.client.post(f'/api/v1/music/songs/{song.id}/play/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['data']['play_count'], 1)

    def test_download_not_allowed_403(self):
        song = make_song(self.artist, self.genre, status=Song.STATUS_PUBLISHED, allow_download=False)
        self.client.force_login(self.user)
        response = self.client.get(f'/api/v1/music/songs/{song.id}/download/')
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()['error']['code'], 'DOWNLOAD_NOT_ALLOWED')

    def test_download_allowed_200(self):
        song = make_song(self.artist, self.genre, status=Song.STATUS_PUBLISHED, allow_download=True)
        self.client.force_login(self.user)
        response = self.client.get(f'/api/v1/music/songs/{song.id}/download/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('download_url', response.json()['data'])


class LikeViewTest(TestCase):

    def setUp(self):
        self.client = Client(enforce_csrf_checks=False)
        self.artist = make_user('likeviewartist', 'likeviewartist@test.com', role='artist')
        self.genre  = make_genre('Pop')
        self.user   = make_user('likeviewuser', 'likeviewuser@test.com')

    def test_toggle_like_requires_auth(self):
        song = make_song(self.artist, self.genre)
        response = self.client.post(f'/api/v1/music/songs/{song.id}/like/')
        self.assertEqual(response.status_code, 401)

    def test_toggle_like_success(self):
        song = make_song(self.artist, self.genre)
        self.client.force_login(self.user)
        response = self.client.post(f'/api/v1/music/songs/{song.id}/like/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['data']['action'], 'liked')

    def test_get_likes_public(self):
        song = make_song(self.artist, self.genre)
        response = self.client.get(f'/api/v1/music/songs/{song.id}/likes/')
        self.assertEqual(response.status_code, 200)


class RatingViewTest(TestCase):

    def setUp(self):
        self.client = Client(enforce_csrf_checks=False)
        self.artist = make_user('rateviewartist', 'rateviewartist@test.com', role='artist')
        self.genre  = make_genre('Pop')
        self.user   = make_user('rateviewuser', 'rateviewuser@test.com')

    def test_rate_song_success(self):
        song = make_song(self.artist, self.genre)
        self.client.force_login(self.user)
        response = self.client.post(
            f'/api/v1/music/songs/{song.id}/rate/',
            data=json.dumps({'score': 5}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['data']['score'], 5)

    def test_rate_song_invalid_score(self):
        song = make_song(self.artist, self.genre)
        self.client.force_login(self.user)
        response = self.client.post(
            f'/api/v1/music/songs/{song.id}/rate/',
            data=json.dumps({'score': 10}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)


class CommentViewTest(TestCase):

    def setUp(self):
        self.client = Client(enforce_csrf_checks=False)
        self.artist = make_user('comviewartist', 'comviewartist@test.com', role='artist')
        self.genre  = make_genre('Pop')
        self.user   = make_user('comviewuser', 'comviewuser@test.com')
        self.other  = make_user('comviewother', 'comviewother@test.com')

    def test_create_comment_success(self):
        song = make_song(self.artist, self.genre)
        self.client.force_login(self.user)
        response = self.client.post(
            f'/api/v1/music/songs/{song.id}/comments/',
            data=json.dumps({'content': 'Great song!', 'parent_id': None}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 201)

    def test_create_comment_blocked_by_artist_403(self):
        song = make_song(self.artist, self.genre)
        BlockList.objects.create(blocker=self.artist, blocked=self.user)
        self.client.force_login(self.user)
        response = self.client.post(
            f'/api/v1/music/songs/{song.id}/comments/',
            data=json.dumps({'content': 'Hi', 'parent_id': None}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()['error']['code'], 'BLOCKED')

    def test_list_comments_public(self):
        song = make_song(self.artist, self.genre)
        Comment.objects.create(user=self.user, song=song, content='Visible comment')
        response = self.client.get(f'/api/v1/music/songs/{song.id}/comments/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()['data']['items']), 1)

    def test_delete_comment_as_owner(self):
        song = make_song(self.artist, self.genre)
        comment = Comment.objects.create(user=self.user, song=song, content='Delete me')
        self.client.force_login(self.user)
        response = self.client.delete(f'/api/v1/music/comments/{comment.id}/')
        self.assertEqual(response.status_code, 204)

    def test_delete_comment_not_owner_403(self):
        song = make_song(self.artist, self.genre)
        comment = Comment.objects.create(user=self.user, song=song, content='Not yours')
        self.client.force_login(self.other)
        response = self.client.delete(f'/api/v1/music/comments/{comment.id}/')
        self.assertEqual(response.status_code, 403)

    def test_like_comment(self):
        song = make_song(self.artist, self.genre)
        comment = Comment.objects.create(user=self.user, song=song, content='Likable')
        self.client.force_login(self.other)
        response = self.client.post(f'/api/v1/music/comments/{comment.id}/like/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['data']['action'], 'liked')


class ListenHistoryViewTest(TestCase):

    def setUp(self):
        self.client = Client(enforce_csrf_checks=False)
        self.artist = make_user('histartist', 'histartist@test.com', role='artist')
        self.genre  = make_genre('Pop')
        self.user   = make_user('histuser', 'histuser@test.com')

    def test_get_history_requires_auth(self):
        response = self.client.get('/api/v1/music/me/history/')
        self.assertEqual(response.status_code, 401)

    def test_get_history_after_play(self):
        song = make_song(self.artist, self.genre, status=Song.STATUS_PUBLISHED)
        self.client.force_login(self.user)
        self.client.post(f'/api/v1/music/songs/{song.id}/play/')
        response = self.client.get('/api/v1/music/me/history/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()['data']['items']), 1)

    def test_delete_history(self):
        song = make_song(self.artist, self.genre, status=Song.STATUS_PUBLISHED)
        self.client.force_login(self.user)
        self.client.post(f'/api/v1/music/songs/{song.id}/play/')
        response = self.client.delete('/api/v1/music/me/history/')
        self.assertEqual(response.status_code, 204)

        check = self.client.get('/api/v1/music/me/history/')
        self.assertEqual(len(check.json()['data']['items']), 0)


class ReportViewTest(TestCase):

    def setUp(self):
        self.client = Client(enforce_csrf_checks=False)
        self.user  = make_user('repviewuser', 'repviewuser@test.com')
        self.admin = make_user('repviewadmin', 'repviewadmin@test.com', role='admin')

    def test_create_report_requires_auth(self):
        response = self.client.post(
            '/api/v1/music/reports/',
            data=json.dumps({
                'target_type': 'song', 'target_id': str(uuid.uuid4()), 'reason': 'spam',
            }),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 401)

    def test_create_report_success(self):
        self.client.force_login(self.user)
        response = self.client.post(
            '/api/v1/music/reports/',
            data=json.dumps({
                'target_type': 'song', 'target_id': str(uuid.uuid4()),
                'reason': 'copyright', 'description': 'Vi pham',
            }),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 201)

    def test_admin_list_reports(self):
        self.client.force_login(self.admin)
        response = self.client.get('/api/v1/music/admin/reports/')
        self.assertEqual(response.status_code, 200)

    def test_admin_list_reports_forbidden_for_user(self):
        self.client.force_login(self.user)
        response = self.client.get('/api/v1/music/admin/reports/')
        self.assertEqual(response.status_code, 403)

    def test_admin_resolve_report(self):
        report = Report.objects.create(
            reporter=self.user, target_type='song', target_id=uuid.uuid4(), reason='spam',
        )
        self.client.force_login(self.admin)
        response = self.client.post(
            f'/api/v1/music/admin/reports/{report.id}/resolve/',
            data=json.dumps({'action': 'resolved', 'note': 'Da xu ly'}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['data']['status'], 'resolved')


class AdminSongCommentViewTest(TestCase):

    def setUp(self):
        self.client = Client(enforce_csrf_checks=False)
        self.artist = make_user('adminviewartist', 'adminviewartist@test.com', role='artist')
        self.genre  = make_genre('Pop')
        self.admin  = make_user('adminviewadmin', 'adminviewadmin@test.com', role='admin')
        self.user   = make_user('adminviewuser', 'adminviewuser@test.com')

    def test_admin_toggle_trending(self):
        song = make_song(self.artist, self.genre)
        self.client.force_login(self.admin)
        response = self.client.post(f'/api/v1/music/admin/songs/{song.id}/trending/')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['data']['is_trending'])

    def test_admin_toggle_trending_forbidden_for_user(self):
        song = make_song(self.artist, self.genre)
        self.client.force_login(self.user)
        response = self.client.post(f'/api/v1/music/admin/songs/{song.id}/trending/')
        self.assertEqual(response.status_code, 403)

    def test_admin_hide_song(self):
        song = make_song(self.artist, self.genre, status=Song.STATUS_PUBLISHED)
        self.client.force_login(self.admin)
        response = self.client.post(f'/api/v1/music/admin/songs/{song.id}/hide/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['data']['status'], 'hidden')

    def test_admin_hide_comment(self):
        song = make_song(self.artist, self.genre)
        comment = Comment.objects.create(user=self.user, song=song, content='Bad content')
        self.client.force_login(self.admin)
        response = self.client.post(f'/api/v1/music/admin/comments/{comment.id}/hide/')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['data']['is_hidden'])


class EndToEndMusicFlowTest(TestCase):
    """Test toan bo luong: upload -> publish -> play -> like -> rate -> comment."""

    def setUp(self):
        self.client = Client(enforce_csrf_checks=False)
        self.artist = make_user('e2eartist', 'e2eartist@test.com', role='artist')
        self.user   = make_user('e2euser', 'e2euser@test.com')
        self.admin  = make_user('e2eadmin', 'e2eadmin@test.com', role='admin')

    def test_full_song_lifecycle(self):
        self.client.force_login(self.admin)
        r1 = self.client.post(
            '/api/v1/music/genres/',
            data=json.dumps({'name': 'E2E Pop', 'description': ''}),
            content_type='application/json',
        )
        self.assertEqual(r1.status_code, 201)
        genre_id = r1.json()['data']['id']

        self.client.force_login(self.artist)
        r2 = self.client.post(
            '/api/v1/music/songs/',
            data={
                'title': 'E2E Song', 'genre_id': genre_id, 'duration': '180',
                'audio_file': make_audio_file(),
            },
        )
        self.assertEqual(r2.status_code, 201)
        song_id = r2.json()['data']['id']
        self.assertEqual(r2.json()['data']['status'], 'draft')

        r3 = self.client.post(f'/api/v1/music/songs/{song_id}/publish/')
        self.assertEqual(r3.status_code, 200)
        self.assertEqual(r3.json()['data']['status'], 'published')

        self.client.logout()
        r4 = self.client.get('/api/v1/music/songs/')
        titles = [s['title'] for s in r4.json()['data']['items']]
        self.assertIn('E2E Song', titles)

        self.client.force_login(self.user)
        r5 = self.client.post(f'/api/v1/music/songs/{song_id}/play/')
        self.assertEqual(r5.json()['data']['play_count'], 1)

        r6 = self.client.post(f'/api/v1/music/songs/{song_id}/like/')
        self.assertEqual(r6.json()['data']['action'], 'liked')

        r7 = self.client.post(
            f'/api/v1/music/songs/{song_id}/rate/',
            data=json.dumps({'score': 5}),
            content_type='application/json',
        )
        self.assertEqual(r7.json()['data']['avg_rating'], 5.0)

        r8 = self.client.post(
            f'/api/v1/music/songs/{song_id}/comments/',
            data=json.dumps({'content': 'Amazing!', 'parent_id': None}),
            content_type='application/json',
        )
        self.assertEqual(r8.status_code, 201)

        r9 = self.client.get(f'/api/v1/music/songs/{song_id}/')
        detail = r9.json()['data']
        self.assertEqual(detail['play_count'], 1)
        self.assertEqual(detail['like_count'], 1)
        self.assertTrue(detail['is_liked'])
        self.assertEqual(detail['my_rating'], 5)

        r10 = self.client.get('/api/v1/music/me/history/')
        self.assertEqual(len(r10.json()['data']['items']), 1)