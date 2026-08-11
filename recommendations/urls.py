"""
recommendations/urls.py

URLs cho app recommendations — prefix: /api/v1/recommendations/
"""

from django.urls import path
from recommendations.views import (
    ForYouView, SimilarSongsView, DismissRecommendationView,
    RecommendedArtistsView, RecommendedPlaylistsView,
    MoodBasedSongsView, MoodBasedPlaylistsView,
)

urlpatterns = [
    path('for-you/', ForYouView.as_view(), name='recommendations-for-you'),
    path('similar/<uuid:song_id>/', SimilarSongsView.as_view(), name='recommendations-similar'),
    path('<uuid:song_id>/dismiss/', DismissRecommendationView.as_view(), name='recommendations-dismiss'),
    path('artists/', RecommendedArtistsView.as_view(), name='recommendations-artists'),
    path('playlists/', RecommendedPlaylistsView.as_view(), name='recommendations-playlists'),
    # Mood-based
    path('mood/<uuid:mood_type_id>/songs/', MoodBasedSongsView.as_view(), name='recommendations-mood-songs'),
    path('mood/<uuid:mood_type_id>/playlists/', MoodBasedPlaylistsView.as_view(), name='recommendations-mood-playlists'),
]
