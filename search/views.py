import logging

from django.http import JsonResponse
from django.views import View

from accounts.exceptions import ValidationError

from search.validators import (
    validate_search_params, validate_search_songs_params, validate_search_all_params,
)
from search.selectors import search_songs, search_artists, search_playlists, search_users, search_all

logger = logging.getLogger(__name__)


def handle_exception(e: Exception) -> JsonResponse:
    if isinstance(e, ValidationError):
        return JsonResponse(
            {'success': False, 'error': {'code': 'VALIDATION_ERROR', 'message': e.message, 'fields': e.fields}},
            status=400,
        )
    logger.exception('Unhandled exception in search views: %s', e)
    return JsonResponse(
        {'success': False, 'error': {'code': 'SERVER_ERROR', 'message': 'Lỗi server'}},
        status=500,
    )


class SearchAllView(View):
    """GET /api/v1/search/ - Tìm kiếm tổng hợp songs+artists+playlists+users (Public)"""

    def get(self, request):
        try:
            filters = validate_search_all_params(request.GET)
            result = search_all(filters['q'], viewer=request.user, limit=filters['limit'])
            return JsonResponse({'success': True, 'data': result})
        except Exception as e:
            return handle_exception(e)


class SongSearchView(View):
    """GET /api/v1/search/songs/ - Tìm bài hát (Public)"""

    def get(self, request):
        try:
            filters = validate_search_songs_params(request.GET)
            result = search_songs(
                q=filters['q'], genre=filters['genre'], artist_id=filters['artist_id'],
                ordering=filters['ordering'], viewer=request.user,
                page=filters['page'], page_size=filters['page_size'],
            )
            return JsonResponse({'success': True, 'data': result})
        except Exception as e:
            return handle_exception(e)


class ArtistSearchView(View):
    """GET /api/v1/search/artists/ - Tìm nghệ sĩ (Public)"""

    def get(self, request):
        try:
            filters = validate_search_params(request.GET, require_q=False)
            result = search_artists(
                q=filters['q'], viewer=request.user, page=filters['page'], page_size=filters['page_size'],
            )
            return JsonResponse({'success': True, 'data': result})
        except Exception as e:
            return handle_exception(e)


class PlaylistSearchView(View):
    """GET /api/v1/search/playlists/ - Tìm playlist công khai (Public)"""

    def get(self, request):
        try:
            filters = validate_search_params(request.GET, require_q=False)
            result = search_playlists(
                q=filters['q'], viewer=request.user, page=filters['page'], page_size=filters['page_size'],
            )
            return JsonResponse({'success': True, 'data': result})
        except Exception as e:
            return handle_exception(e)


class UserSearchView(View):
    """
    GET /api/v1/search/users/ - Tìm người dùng (Auth)

    Yêu cầu đăng nhập vì kết quả phụ thuộc vào quan hệ follow/block của
    requester  tìm kiếm ẩn danh sẽ không phân biệt được "người
    quen" nên chỉ nên thấy user public, phù hợp hơn khi bắt buộc đăng nhập
    để tận dụng đầy đủ tính năng và tránh scraping danh sách user hàng loạt.
    """

    def get(self, request):
        try:
            if not request.user.is_authenticated:
                return JsonResponse(
                    {'success': False, 'error': {'code': 'AUTH_REQUIRED', 'message': 'Cần đăng nhập để tìm người dùng'}},
                    status=401,
                )
            filters = validate_search_params(request.GET, require_q=False)
            result = search_users(
                q=filters['q'], requester=request.user, page=filters['page'], page_size=filters['page_size'],
            )
            return JsonResponse({'success': True, 'data': result})
        except Exception as e:
            return handle_exception(e)