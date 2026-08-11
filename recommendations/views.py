"""
recommendations/views.py

Tầng HTTP cho app recommendations.

Quy ước giống music/views.py:
  - views.py KHÔNG import model để query trực tiếp
  - Mọi query qua selectors.py, mọi ghi qua services.py
  - Exception từ services/selectors được map sang HTTP status
"""

import logging

from django.http import JsonResponse
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect

from accounts.decorators import require_auth
from accounts.exceptions import ValidationError, PermissionDenied, NotFound
from music.exceptions import SongNotFound

from recommendations.validators import validate_recommend_params, validate_similar_params, validate_media_params
from recommendations.selectors import (
    get_recommendations_for_user, get_similar_songs,
    get_recommended_artists, get_recommended_playlists,
    get_songs_for_mood, get_playlists_for_mood,
)
from recommendations.services import dismiss_recommendation

logger = logging.getLogger(__name__)


def handle_exception(e: Exception) -> JsonResponse:
    """Map exception nghiệp vụ sang HTTP response chuẩn (theo pattern music/views.py)."""
    if isinstance(e, ValidationError):
        return JsonResponse(
            {
                'success': False,
                'error': {'code': 'VALIDATION_ERROR', 'message': e.message, 'fields': e.fields},
            },
            status=400,
        )
    if isinstance(e, (SongNotFound, NotFound)):
        return JsonResponse(
            {'success': False, 'error': {'code': 'NOT_FOUND', 'message': e.message}},
            status=404,
        )
    if isinstance(e, PermissionDenied):
        return JsonResponse(
            {'success': False, 'error': {'code': e.error_code, 'message': e.message}},
            status=403,
        )
    logger.exception('Unhandled exception in recommendations')
    return JsonResponse(
        {'success': False, 'error': {'code': 'SERVER_ERROR', 'message': 'Đã có lỗi xảy ra'}},
        status=500,
    )


class ForYouView(View):
    """GET /api/v1/recommendations/for-you/ - Auth. Gợi ý hybrid cá nhân hoá."""

    @method_decorator(require_auth)
    def get(self, request):
        try:
            params = validate_recommend_params(request.GET)
            result = get_recommendations_for_user(
                request.user, page=params['page'], page_size=params['page_size']
            )
            return JsonResponse({'success': True, 'data': result})
        except Exception as e:
            return handle_exception(e)


class SimilarSongsView(View):
    """GET /api/v1/recommendations/similar/<song_id>/ - Public. "Nghe tiếp" từ 1 bài hát."""

    def get(self, request, song_id):
        try:
            params = validate_similar_params(request.GET)
            items = get_similar_songs(song_id, viewer=request.user, limit=params['limit'])
            return JsonResponse({'success': True, 'data': {'items': items, 'total': len(items)}})
        except Exception as e:
            return handle_exception(e)


class DismissRecommendationView(View):
    """POST /api/v1/recommendations/<song_id>/dismiss/ - Auth. Toggle 'không quan tâm'."""

    @method_decorator(csrf_protect)
    @method_decorator(require_auth)
    def post(self, request, song_id):
        try:
            dismissed = dismiss_recommendation(request.user, song_id)
            return JsonResponse({'success': True, 'data': {'dismissed': dismissed}})
        except Exception as e:
            return handle_exception(e)


class RecommendedArtistsView(View):
    """GET /api/v1/recommendations/artists/ - Auth. Gợi ý nghệ sĩ theo gu nghe."""

    @method_decorator(require_auth)
    def get(self, request):
        try:
            params = validate_media_params(request.GET)
            artists = get_recommended_artists(request.user, limit=params['limit'])
            return JsonResponse({'success': True, 'data': {'items': artists, 'total': len(artists)}})
        except Exception as e:
            return handle_exception(e)


class RecommendedPlaylistsView(View):
    """GET /api/v1/recommendations/playlists/ - Auth. Gợi ý playlist công khai theo gu nghe."""

    @method_decorator(require_auth)
    def get(self, request):
        try:
            params = validate_media_params(request.GET)
            playlists = get_recommended_playlists(request.user, limit=params['limit'])
            return JsonResponse({'success': True, 'data': {'items': playlists, 'total': len(playlists)}})
        except Exception as e:
            return handle_exception(e)


class MoodBasedSongsView(View):
    """GET /api/v1/recommendations/mood/<mood_type_id>/songs/ - Auth.
    Gợi ý bài hát phù hợp với tâm trạng cụ thể."""

    @method_decorator(require_auth)
    def get(self, request, mood_type_id):
        try:
            params = validate_media_params(request.GET)
            result = get_songs_for_mood(
                mood_type_id=mood_type_id,
                user=request.user,
                limit=params['limit'],
            )
            return JsonResponse({'success': True, 'data': result})
        except Exception as e:
            return handle_exception(e)


class MoodBasedPlaylistsView(View):
    """GET /api/v1/recommendations/mood/<mood_type_id>/playlists/ - Auth.
    Gợi ý playlist phù hợp với tâm trạng cụ thể."""

    @method_decorator(require_auth)
    def get(self, request, mood_type_id):
        try:
            params = validate_media_params(request.GET)
            result = get_playlists_for_mood(
                mood_type_id=mood_type_id,
                user=request.user,
                limit=params['limit'],
            )
            return JsonResponse({'success': True, 'data': result})
        except Exception as e:
            return handle_exception(e)
