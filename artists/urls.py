from django.urls import path
from artists.views import (
    ArtistListView, 
    MyArtistProfileView, 
    MyArtistStatsView, 
    ArtistDetailView, 
    ArtistStatsView,
)

urlpatterns = [
    path('', ArtistListView.as_view(), name='artist-list'),
    path('me/', MyArtistProfileView.as_view(), name='artist-me'),
    path('me/stats/', MyArtistStatsView.as_view(), name='artist-me-stats'),
    path('<uuid:user_id>/', ArtistDetailView.as_view(), name='artist-detail'),
    path('<uuid:user_id>/stats/', ArtistStatsView.as_view(), name='artist-stats'),
]
