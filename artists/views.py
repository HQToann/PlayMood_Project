"""
artists/views.py

Tăng HTTP cho app artists.

Quy ước:
    - views.py không inport ArtistsProfile, Song, Like... để query trực tiếp
    - Mỗi query qua selecetors.py, mỗi ghi qua services.py
    - Exception từ services/selectors được map sang HTTP status qua handle_exception()
"""

import json
import logging

from django.http import JsonResponse
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect

from accounts.decorators import require_auth, require_artist
from accounts.exceptions import ValidationError, PermissionDenied, NotFound, AlreadyExists

from artists.exceptions import (
    ArtistProfileNotFound,
    ArtistProfileAlreadyExists,
    NotArtistProfileOwner,
    UserNotArtist,
)
from artists.validators import (
    validate_artist_profile_create, validate_artist_profile_update,
    validate_list_artists_params,
)
from artists.selectors import (
    get_artist_profile_by_user_id, get_artist_profile_detail, list_artists,
    get_artist_stats, list_artist_top_songs,
)
from artists.services import (
    create_artist_profile,
    update_artist_profile,
    get_or_create_my_profile,
)

logger = logging.getLogger(__name__)

def parse_json_body(request) -> dict:
    """
    Parse JSON body an toàn - trả {} nếu body rỗng hoặc lỗi parse.
    """
    try:
        return json.loads(request.body or '{}')
    except (json.JSONDecodeError, ValueError):
        return {}
    
def handle_exception(e: Exception) -> JsonResponse:
    """
    Map exception nghiệp vụ snag HTTP response chuẩn. Dùng chung cho mọi view trong app"""
    if isinstance(e, ValidationError):
        return JsonResponse(
            {
                'success': False,
                'error': {
                    'code': 'VALIDATION_ERROR',
                    'message': e.message,
                    'fields': e.fields,
                }
            },
            status=400,
        )
    
    if isinstance(e, (NotArtistProfileOwner, PermissionDenied, UserNotArtist)):
        return JsonResponse (
            {
                'success': False,
                'error': {
                    'code': e.error_code,
                    'message': e.message,
                }
            },
            status=403,
        )
    
    if isinstance(e, (ArtistProfileNotFound, NotFound)):
        return JsonResponse (
            {
                'success': False,
                'error': {
                    'code': 'NOT_FOUND',
                    'message': e.message,
                }
            },
            status=404,
        )
    
    if isinstance(e, (ArtistProfileAlreadyExists, AlreadyExists)):
        return JsonResponse(
            {
                'success': False,
                'error': {
                    'code': 'ALREADY_EXISTS',
                    'message': e.message,
                }
            },
            status=409,
        )
    
    logger.exception('Unhandle exception in artists view: %s', e)
    return JsonResponse (
        {
            'success': False,
            'error': {
                'code': 'SERVER_ERROR',
                'message': 'Lỗi server'
            }
        },
        status=500,
    )

class ArtistListView(View):
    """
    GET /api/v1/artists/ - Danh sách nghệ sĩ (Public)
    """
    def get(self, request):
        try:
            filters = validate_list_artists_params(request.GET)
            result = list_artists(filters, viewer=request.user)
            return JsonResponse(
                {
                    'success': True,
                    'data': result,
                }
            )
        except Exception as e:
            return handle_exception(e)
        
class MyArtistProfileView(View):
    """
    GET /api/v1/artists/me/ - Xem hồ sơ của chính mình, tự tạo rỗng nếu chưa có
    POST /api/v1/artists/me/ - Tạo hồ sơ nghệ sĩ (Artist+CSRF)
    """

    @method_decorator(require_artist)
    def get(self, request):
        try:
            profile = get_or_create_my_profile(request.user)
            return JsonResponse(
                {
                    'success': True,
                    'data': profile.to_dict(viewer=request.user),
                }
            )
        except Exception as e:
            return handle_exception(e)
        
    @method_decorator(csrf_protect)
    @method_decorator(require_artist)
    def post(self, request):
        try:
            data = parse_json_body(request)
            validated = validate_artist_profile_create(data)
            profile = create_artist_profile(request.user, validated)
            return JsonResponse(
                {
                    'success': True,
                    'data': profile.to_dict(viewer=request.user),
                },
                status=201,
            )
        except Exception as e:
            return handle_exception(e)
        
    @method_decorator(csrf_protect)
    @method_decorator(require_artist)
    def patch(self, request):
        try:
            profile = get_artist_profile_by_user_id(request.user.id)
            data = parse_json_body(request)
            validated = validate_artist_profile_update(data)
            if not validated:
                return JsonResponse(
                    {
                        'success': False,
                        'error': {
                            'code': 'VALIDATION_ERROR',
                            'message': 'Không có dữ liệu để cập nhật'
                        }
                    },
                    status=400,
                )
            profile = update_artist_profile(profile, request.user, validated)
            return JsonResponse(
                {
                    'success': True,
                    'data': profile.to_dict(viewer=request.user)
                }
            )
        except Exception as e:
            return handle_exception(e)
        
        
class MyArtistStatsView(View):
    """
    GET /api/v1/artists/me/stats/ - Thống kê của chính mình
    """
    @method_decorator(require_artist)
    def get(self, request):
        try:
            stats = get_artist_stats(request.user.id)
            top_songs = list_artist_top_songs(request.user.id, limit=10)
            return JsonResponse(
                {
                    'success': True,
                    'data': {
                        **stats,
                        'top_songs': top_songs,
                    }
                }
            )
        except Exception as e:
            return handle_exception(e)
        
class ArtistDetailView(View):
    """
    GET /api/v1/artists/<user_id>/ - Xem hồ sơ nghệ sĩ công khai
    """
    def get(self, request, user_id):
        try:
            profile = get_artist_profile_detail(user_id, viewer=request.user)
            return JsonResponse(
                {
                    'success': True,
                    'data': profile.to_dict(viewer=request.user),
                }
            )
        except Exception as e:
            return handle_exception(e)

class ArtistStatsView(View):
    """
    GET /api/v1/artists/<user_id>/stats/ - Thống kê công khai của một nghệ sĩ
    """
    def get(self, request, user_id):
        try:
            # get_artist_profile_detail từ raise ArtistProfileNotFound nếu không tồn tại/bị block
            get_artist_profile_detail(user_id, viewer=request.user)
            stats = get_artist_stats(user_id)
            top_songs = list_artist_top_songs(user_id, limit=10)
            return JsonResponse(
                {
                    'success': True,
                    'data': {
                        **stats,
                        'top_songs':top_songs,
                    }
                }
            )
        except Exception as e:
            return handle_exception(e)