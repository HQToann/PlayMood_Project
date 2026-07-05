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


# Handler tuỳ chỉnh
from django.http import JsonResponse
from django.shortcuts import render

def profile_routing_view(request):
    """
    Hiển thị trang profile dựa trên role của người dùng.
    Nếu là artist, trả về artist_profile.html, ngược lại trả về profile.html.
    """
    if request.user.is_authenticated and getattr(request.user, 'role', '') == 'artist':
        return render(request, 'profile/artist_profile.html')
    return render(request, 'profile/profile.html')


def user_profile_routing_view(request, user_id):
    """
    Hiển thị trang profile của người dùng khác dựa trên role của họ.
    Nếu là artist, trả về artist_profile.html, ngược lại trả về profile.html.
    Truyền target_user_id vào context để JS biết cần load profile của ai.
    """
    from accounts.models import User
    try:
        target_user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        from django.http import Http404
        raise Http404
    if getattr(target_user, 'role', '') == 'artist':
        return render(request, 'profile/artist_profile.html', {'target_user_id': str(user_id)})
    return render(request, 'profile/profile.html', {'target_user_id': str(user_id)})



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
urlpatterns = [
    # Frontend Routes
    path('', TemplateView.as_view(template_name='home/index.html'), name='home'),
    path('auth/login/', TemplateView.as_view(template_name='auth/login.html'), name='login_page'),
    path('profile/', profile_routing_view, name='profile_page'),
    path('profile/upload/', TemplateView.as_view(template_name='profile/artist_upload.html'), name='artist_upload_page'),
    path('profile/manage/', TemplateView.as_view(template_name='profile/artist_manage_songs.html'), name='artist_manage_page'),
    path('profile/<uuid:user_id>/', user_profile_routing_view, name='user_profile_page'),
    path('settings/', TemplateView.as_view(template_name='settings/settings.html'), name='settings_page'),
    path('notifications/', TemplateView.as_view(template_name='notifications/notifications.html'), name='notifications_page'),
    path('mood/', TemplateView.as_view(template_name='social/mood.html'), name='mood_page'),

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

]

# Phục vụ media files trong môi trường development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)