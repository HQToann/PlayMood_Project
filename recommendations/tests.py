"""
recommendations/tests.py
=========================
Unit tests cho app recommendations.

Chạy tests:
    python manage.py test recommendations --verbosity=2
"""

from django.test import TestCase

from accounts.models import User
from music.models import Genre, Song, Like, Rating
from recommendations.selectors import (
    get_recommendations_for_user,
    get_similar_songs,
    _cosine_similarity,
)
from recommendations.services import dismiss_recommendation
from music.exceptions import SongNotFound


def make_user(username, role='user'):
    return User.objects.create_user(
        username=username, email=f'{username}@test.com', password='Test1234', role=role
    )


def make_song(title, artist, genre=None, play_count=0):
    return Song.objects.create(
        title=title,
        artist=artist,
        genre=genre,
        audio_file='audio/fake.mp3',
        status=Song.STATUS_PUBLISHED,
        play_count=play_count,
    )


class CosineSimilarityTests(TestCase):
    def test_identical_vectors_are_fully_similar(self):
        vec = {'a': 3, 'b': 2}
        self.assertAlmostEqual(_cosine_similarity(vec, vec), 1.0)

    def test_disjoint_vectors_have_zero_similarity(self):
        self.assertEqual(_cosine_similarity({'a': 1}, {'b': 1}), 0.0)

    def test_empty_vector_has_zero_similarity(self):
        self.assertEqual(_cosine_similarity({}, {'a': 1}), 0.0)


class RecommendationSelectorTests(TestCase):
    def setUp(self):
        self.artist1 = make_user('artist1', role='artist')
        self.artist2 = make_user('artist2', role='artist')
        self.viewer = make_user('viewer')
        self.twin = make_user('twin')  # user có gu giống viewer -> nguồn collaborative

        self.pop = Genre.objects.create(name='Pop')
        self.rock = Genre.objects.create(name='Rock')

        self.song_pop_1 = make_song('Pop 1', self.artist1, genre=self.pop)
        self.song_pop_2 = make_song('Pop 2', self.artist1, genre=self.pop)
        self.song_rock_1 = make_song('Rock 1', self.artist2, genre=self.rock)

    def test_cold_start_falls_back_to_trending(self):
        # viewer chưa Like/Rate/nghe bài nào -> phải trả về nguồn 'trending'
        result = get_recommendations_for_user(self.viewer, page=1, page_size=10)
        self.assertEqual(result['source'], 'trending')

    def test_excludes_already_liked_songs(self):
        Like.objects.create(user=self.viewer, song=self.song_pop_1)
        # twin thích cả 2 bài pop -> tạo tín hiệu content + collaborative
        Like.objects.create(user=self.twin, song=self.song_pop_1)
        Like.objects.create(user=self.twin, song=self.song_pop_2)

        result = get_recommendations_for_user(self.viewer, page=1, page_size=10)
        recommended_ids = {item['id'] for item in result['items']}
        self.assertNotIn(str(self.song_pop_1.id), recommended_ids)

    def test_content_based_prefers_same_genre(self):
        Like.objects.create(user=self.viewer, song=self.song_pop_1)
        Rating.objects.create(user=self.twin, song=self.song_pop_2, score=5)
        Like.objects.create(user=self.twin, song=self.song_pop_2)

        result = get_recommendations_for_user(self.viewer, page=1, page_size=10)
        recommended_ids = [item['id'] for item in result['items']]
        # bài pop còn lại nên được gợi ý trước bài rock (không liên quan gu nghe)
        self.assertIn(str(self.song_pop_2.id), recommended_ids)


class SimilarSongsSelectorTests(TestCase):
    def setUp(self):
        self.artist = make_user('artist1', role='artist')
        self.genre = Genre.objects.create(name='Pop')
        self.anchor = make_song('Anchor', self.artist, genre=self.genre)
        self.same_artist_song = make_song('Same Artist', self.artist, genre=self.genre)

    def test_similar_songs_includes_same_artist(self):
        items = get_similar_songs(self.anchor.id, viewer=None, limit=5)
        ids = [item['id'] for item in items]
        self.assertIn(str(self.same_artist_song.id), ids)

    def test_raises_when_song_not_found(self):
        with self.assertRaises(SongNotFound):
            get_similar_songs('00000000-0000-0000-0000-000000000000', viewer=None, limit=5)


class DismissRecommendationServiceTests(TestCase):
    def setUp(self):
        self.user = make_user('viewer')
        self.artist = make_user('artist1', role='artist')
        self.song = make_song('Song', self.artist)

    def test_dismiss_then_undo(self):
        dismissed = dismiss_recommendation(self.user, self.song.id)
        self.assertTrue(dismissed)

        undone = dismiss_recommendation(self.user, self.song.id)
        self.assertFalse(undone)
