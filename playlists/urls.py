"""
playlists/urls.py

URLs cho app playlists — prefix: /api/v1/playlists/
"""

from django.urls import path
from playlists.views import (
    PlaylistListView, PlaylistDetailView, PlaylistCoverUploadView,
    PlaylistVisibilityView,
    PlaylistSongListView, PlaylistSongDetailView, PlaylistSongReorderView,
)

urlpatterns = [
    # Playlist CRUD
    path("", PlaylistListView.as_view(), name="playlist-list"),
    path("<uuid:playlist_id>/", PlaylistDetailView.as_view(), name="playlist-detail"),
    path("<uuid:playlist_id>/cover/", PlaylistCoverUploadView.as_view(), name="playlist-cover"),
    path("<uuid:playlist_id>/visibility/", PlaylistVisibilityView.as_view(), name="playlist-visibility"),


    # Playlist Songs
    path("<uuid:playlist_id>/songs/", PlaylistSongListView.as_view(), name="playlist-song-list"),
    path("<uuid:playlist_id>/songs/reorder/", PlaylistSongReorderView.as_view(), name="playlist-song-reorder"),
    path("<uuid:playlist_id>/songs/<uuid:song_id>/", PlaylistSongDetailView.as_view(), name="playlist-song-detail"),
]