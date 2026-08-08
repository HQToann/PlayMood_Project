"""
music/urls.py

URLs cho app music — prefix: /api/v1/music/
"""

from django.urls import path
from music.views import (
    GenreListView, GenreDetailView,
    SongListView, SongTrendingView, SongDetailView,
    SongPublishView, SongHideView, SongAppealView, SongPlayView, SongDownloadView,
    SongLikeView, SongRatingView, UserLikedSongsView,
    SongCommentListView, CommentDetailView, CommentLikeView,
    ListenHistoryView,
    ReportCreateView, AdminReportListView, AdminReportResolveView,
    AdminSongTrendingView, AdminSongHideView, AdminCommentHideView,
    AlbumListView, AlbumDetailView, AlbumPublishView, AlbumSongsView, ArtistAlbumsView,
)

urlpatterns = [
    # Genre
    path('genres/', GenreListView.as_view(), name='music-genre-list'),
    path('genres/<uuid:genre_id>/', GenreDetailView.as_view(), name='music-genre-detail'),

    # Song list + create
    path('songs/', SongListView.as_view(), name='music-song-list'),
    path('songs/trending/', SongTrendingView.as_view(), name='music-song-trending'),

    # Song detail
    path('songs/<uuid:song_id>/', SongDetailView.as_view(), name='music-song-detail'),
    path('songs/<uuid:song_id>/publish/', SongPublishView.as_view(), name='music-song-publish'),
    path('songs/<uuid:song_id>/hide/', SongHideView.as_view(), name='music-song-hide'),
    path('songs/<uuid:song_id>/appeal/', SongAppealView.as_view(), name='music-song-appeal'),
    path('songs/<uuid:song_id>/play/', SongPlayView.as_view(), name='music-song-play'),
    path('songs/<uuid:song_id>/download/', SongDownloadView.as_view(), name='music-song-download'),

    # Like + Rating
    path('songs/<uuid:song_id>/like/', SongLikeView.as_view(), name='music-song-like'),
    path('songs/<uuid:song_id>/likes/', SongLikeView.as_view(), name='music-song-likes'),
    path('songs/<uuid:song_id>/rate/', SongRatingView.as_view(), name='music-song-rate'),
    path('songs/<uuid:song_id>/rating/', SongRatingView.as_view(), name='music-song-rating'),

    # Comment
    path('songs/<uuid:song_id>/comments/', SongCommentListView.as_view(), name='music-comment-list'),
    path('comments/<uuid:comment_id>/', CommentDetailView.as_view(), name='music-comment-detail'),
    path('comments/<uuid:comment_id>/like/', CommentLikeView.as_view(), name='music-comment-like'),

    # Listen History & User Likes
    path('me/history/', ListenHistoryView.as_view(), name='music-history'),
    path('users/<uuid:user_id>/likes/', UserLikedSongsView.as_view(), name='music-user-likes'),
    path('users/<uuid:user_id>/albums/', ArtistAlbumsView.as_view(), name='music-artist-albums'),

    # Albums
    path('albums/', AlbumListView.as_view(), name='music-album-list'),
    path('albums/<uuid:album_id>/', AlbumDetailView.as_view(), name='music-album-detail'),
    path('albums/<uuid:album_id>/publish/', AlbumPublishView.as_view(), {'action': 'publish'}, name='music-album-publish'),
    path('albums/<uuid:album_id>/unpublish/', AlbumPublishView.as_view(), {'action': 'unpublish'}, name='music-album-unpublish'),
    path('albums/<uuid:album_id>/songs/', AlbumSongsView.as_view(), name='music-album-songs'),
    path('albums/<uuid:album_id>/songs/<uuid:song_id>/', AlbumSongsView.as_view(), name='music-album-song-detail'),

    # Reports
    path('reports/', ReportCreateView.as_view(), name='music-report-create'),

    # Admin
    path('admin/reports/', AdminReportListView.as_view(), name='music-admin-report-list'),
    path('admin/reports/<uuid:report_id>/resolve/', AdminReportResolveView.as_view(), name='music-admin-report-resolve'),
    path('admin/songs/<uuid:song_id>/trending/', AdminSongTrendingView.as_view(), name='music-admin-song-trending'),
    path('admin/songs/<uuid:song_id>/hide/', AdminSongHideView.as_view(), name='music-admin-song-hide'),
    path('admin/comments/<uuid:comment_id>/hide/', AdminCommentHideView.as_view(), name='music-admin-comment-hide'),
]
