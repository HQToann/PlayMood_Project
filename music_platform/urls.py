"""
music_platform/urls.py

URL gốc của toàn hệ thống.

Tất cả các API đều có prefix /api/v1/
Migration path: nếu cần backward compat, alias /api/ → /api/v1/ trong giai đoạn chuyển tiếp bằng cách include cả hai.
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView


from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, redirect

LOGIN_URL = '/auth/login/'

def login_required_view(template_name):
    """Wrapper tạo view yêu cầu đăng nhập, redirect về login nếu chưa đăng nhập."""
    def view(request, **kwargs):
        if not request.user.is_authenticated:
            return redirect(LOGIN_URL)
        return render(request, template_name, kwargs)
    return view

def home_view(request):
    """Trang chủ - cho phép xem, nhưng phải đăng nhập mới nghe nhạc."""
    return render(request, 'home/index.html')

def profile_routing_view(request):
    """
    Hiển thị trang profile dựa trên role của người dùng.
    Nếu là artist, trả về artist_profile.html, ngược lại trả về profile.html.
    """
    if not request.user.is_authenticated:
        return redirect(LOGIN_URL)
    
    context = {'target_user': request.user, 'is_own_profile': True}
    
    if getattr(request.user, 'role', '') == 'artist':
        return render(request, 'profile/artist_profile.html', context)
    return render(request, 'profile/profile.html', context)


def user_profile_routing_view(request, user_id):
    """
    Hiển thị trang profile của người dùng khác dựa trên role của họ.
    """
    from accounts.models import User
    try:
        target_user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        from django.http import Http404
        raise Http404
    
    context = {
        'target_user': target_user,
        'target_user_id': str(user_id),
        'is_own_profile': request.user.is_authenticated and str(request.user.id) == str(user_id)
    }
        
    if getattr(target_user, 'role', '') == 'artist':
        return render(request, 'profile/artist_profile.html', context)
    return render(request, 'profile/profile.html', context)



def handler404(request, exception):
    """Trả JSON thay vì HTML 404 mặc định."""
    return JsonResponse(
        {
            'success': False, 
            'error': {
                'code': 'NOT_FOUND', 
                'message': 
                'Endpoint không tồn tại'
            }
        },
        status=404,
    )


def handler500(request):
    """Trả JSON thay vì HTML 500 mặc định."""
    return JsonResponse(
        {
            'success': False, 
            'error': {
                'code': 
                'SERVER_ERROR', 
                'mesage': 'Lỗi server'
            }
        },
        status=500,
    )

def handler429(request):
    """Trả JSON khi vượt quá rate limit."""
    return JsonResponse(
        {
            'success': False,
            'error': {
                'code': 'RATE_LIMITED',
                'message': 'Quá nhiều yêu cầu, vui lòng thử lại sau',
            },
        },
        status=429
    )

# URL Patterns
def dummy_favicon(request):
    return redirect('https://res.cloudinary.com/jibxercm/image/upload/v1786899540/music_platform/assets/favicon.svg')

urlpatterns = [
    path('favicon.ico', dummy_favicon),
    # Frontend Routes - Yêu cầu đăng nhập
    path('', home_view, name='home'),
    path('auth/login/', TemplateView.as_view(template_name='auth/login.html'), name='login_page'),
    path('auth/reset-password/', TemplateView.as_view(template_name='auth/reset_password.html'), name='reset_password_page'),
    path('profile/', profile_routing_view, name='profile_page'),
    path('profile/upload/', login_required_view('profile/artist_upload.html'), name='artist_upload_page'),
    path('profile/manage/', login_required_view('profile/artist_manage_songs.html'), name='artist_manage_page'),
    path('profile/<uuid:user_id>/', user_profile_routing_view, name='user_profile_page'),
    path('settings/', login_required_view('settings/settings.html'), name='settings_page'),
    path('notifications/', login_required_view('notifications/notifications.html'), name='notifications_page'),
    path('explore/', login_required_view('explore/explore.html'), name='explore_page'),
    path('explore/list/', login_required_view('explore/explore_list.html'), name='explore_list_page'),
    path('search/', login_required_view('search/search_results.html'), name='search_page'),
    path('mood/', login_required_view('social/mood.html'), name='mood_page'),
    path('mood/explore/', login_required_view('social/mood_explore.html'), name='mood_explore_page'),
    path('playlist/', login_required_view('playlists/playlist.html'), name='playlist_page'),
    path('playlist/detail/', login_required_view('playlists/playlist_detail.html'), name='playlist_detail_page'),
    
    # Library Routes
    path('library/favorites/', login_required_view('library/favorites.html'), name='library_favorites_page'),
    path('library/recent/', login_required_view('library/recent.html'), name='library_recent_page'),
    path('library/albums/', login_required_view('albums/albums.html'), name='library_albums_page'),

    path('song/', TemplateView.as_view(template_name='song/song.html'), name='song_page'),
    path('album/detail/', login_required_view('albums/album_detail.html'), name='album_detail_page'),

    # Admin & API Routes
    path('admin/', admin.site.urls),

    # API v1 - toàn bộ logic backend

    # Tuần 1 - accounts
    path('api/v1/auth/', include('accounts.auth_urls')),
    path('api/v1/accounts/', include('accounts.urls')),

    # Tuần 2 - musics
    path("api/v1/music/", include('music.urls')),

    # Tuần 3 - playlists
    path('api/v1/playlists/', include('playlists.urls')),
    
    # Tuần 3 - actists
    path('api/v1/artists/', include('artists.urls')),

    # Tuần 4 - social
    path('api/v1/social/', include('social.urls')),

    #tuần 5 - notification
    path('api/v1/notifications/', include('notifications.urls')),

    # tuần 5 - search
    path('api/v1/search/', include('search.urls')),

    # recommendations
    path('api/v1/recommendations/', include('recommendations.urls')),

]

# Phục vụ media files trong môi trường development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)