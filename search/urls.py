from django.urls import path
from search.views import SearchAllView, SongSearchView, ArtistSearchView, PlaylistSearchView, UserSearchView

urlpatterns = [
    path('', SearchAllView.as_view(), name='search-all'),
    path('songs/', SongSearchView.as_view(), name='search-songs'),
    path('artists/', ArtistSearchView.as_view(), name='search-artists'),
    path('playlists/', PlaylistSearchView.as_view(), name='search-playlists'),
    path('users/', UserSearchView.as_view(), name='search-users'),
]