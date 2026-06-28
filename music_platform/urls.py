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


# Handler tuỳ chỉnh
from django.http import JsonResponse

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
    # path('api/v1/playlists/', include('playlists.urls')),
    # path('api/v1/social/', include('social.urls')),
    # path('api/v1/notifications/', include('notifications.urls')),
    # path('api/v1/search/', include('search.urls')),
]

# Phục vụ media files trong môi trường development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)