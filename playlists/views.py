import json
import logging

from django.http import JsonResponse
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect

from accounts.decorators import require_auth
from accounts.exceptions import (
    ValidationError,
    PermissionDenied,
    NotFound,
    AlreadyExists
)
from music.exceptions import SongNotFound
from playlists.exceptions import (
    PlaylistNotFound,
    NotPlaylistOwner,
    SongAlreadyInPlaylist,
    SongNotInPlaylist, 
    InvalidReorderData,
)
from playlists.validators import (
    validate_playlist_create, 
    validate_playlist_update, 
    validate_visibility,
    validate_add_song, 
    validate_reorder, 
    validate_cover_image,
    validate_list_playlists_params,
)
from playlists.selectors import (
    list_my_playlists, 
    get_playlist_by_id, 
    get_playlist_detail, 
    list_playlist_songs,
)
from playlists.services import (
    create_playlist, 
    update_playlist, 
    update_cover_image, 
    update_visibility,
    delete_playlist, 
    add_song_to_playlist, 
    remove_song_from_playlist,
    reorder_playlist_songs,
)
logger = logging.getLogger(__name__)

#parse json body
#trả {} nếu body rỗng hoặc lỗi
def parse_json_body(request) -> dict:
    try:
        return json.load(request.body or '{}')
    except (json.JSONDecodeError, ValueError):
        return {}
    

#chuyển exception nghiệp vụ sạng HTTp response
def handle_exception(e: Exception) -> JsonResponse:
    if isinstance(e, ValidationError):
        return JsonResponse(
            {
                'success': False,
                'error': {
                    'code': 'VALIDATION_ERROR',
                    'message': e.message,
                    'fields': e.fields,
                },
            }, status=400,
        )
    
    if isinstance(e, InvalidReorderData):
        return JsonResponse(
            {
                'success': False,
                'error': {
                    'code': e.error_code,
                    'message': e.message,
                },
            }, status=400,
        )
    if isinstance(e, (NotPlaylistOwner, PermissionDenied)):
        return JsonResponse(
            {
                'success': False,
                'error': {
                    'code': e.error_code,
                    'message': e.message, 
                },
            }, status=403,
        )
    
    if isinstance(e, (PlaylistNotFound, SongNotFound, SongNotInPlaylist, NotFound)):
        return JsonResponse(
            {
                'success': False,
                'error': {
                    'code': 'NOT_FOUND',
                    'message': e.message,
                },
            }, status=404,
        )
    
    if isinstance(e, (SongAlreadyInPlaylist, AlreadyExists)):
        return JsonResponse(
            {
                'success': False,
                'error': {
                    'code': 'ALREDY_EXISTS',
                    'message': e.message
                },
            }, status=409,
        )
    
    logger.exception('Uhandled exception in playlists views: %s', e)
    return JsonResponse(
        {
            'success': False,
            'error': {
                'code': 'SERVER_ERROR',
                'message': 'Lỗi server',
            },
        }, status=500,
    )

#Playlist views
#GET /api/v1/playlists/ Danh sách phát của tôi (auth)
#POST /api/v1/playlists/ Tạo playlist mới (auth+csrf)
class PlaylistListView(View):

    @method_decorator(require_auth)
    def get(self, request):
        try:
            filters = validate_list_playlists_params(request.GET)
            result = list_my_playlists(request.user, filters)
            return JsonResponse(
                {
                    'success': True,
                    'data': result,
                },
            )
        except Exception as e:
            return handle_exception(e)
        
    @method_decorator(csrf_protect)
    @method_decorator(require_auth)
    def post(self, request):
        try: 
            data = parse_json_body(request)
            validated = validate_playlist_create(data)
            playlist = create_playlist(request.user, validated)
            return JsonResponse(
                {
                    'success': True,
                    'data': playlist.to_dict(viewer=request.user),
                }, status=201,
            )
        except Exception as e:
            return handle_exception(e)
        


#GET /api/v1/playlists/<id>/ chi tiết playlist (Public nếu is_public, Owner nếu private)
#PATCH /api/v1/playlists/<id> cập nhật title/description (auth+owner+csrf)
#DELETE /api/v1/playlists/<id> xúa playlist (auth+owner+csrf)
class PlaylistDetailView(View):
    def get(self, request, playlist_id):
        try:
            playlist = get_playlist_detail(playlist_id, viewer=request.user)
            return JsonResponse(
                {
                    'success': True,
                    'data': playlist.to_dict(viewer=request.user),
                }
            )
        except Exception as e:
            return handle_exception(e)

    @method_decorator(csrf_protect)
    @method_decorator(require_auth)
    def patch(self, request, playlist_id):
        try:
            playlist = get_playlist_by_id(playlist_id)
            data = parse_json_body(request)
            validated = validate_playlist_update(data)
            if not validated:
                return JsonResponse(
                    {
                        'success': False,
                        'error': {
                            'code': 'VALIDATION_ERROR',
                            'message': 'Không có dữ liệu để cập nhật',
                        }, 
                    }, status=400,
                )
            playlist = update_playlist(playlist, request.user, validated)
            return JsonResponse(
                {
                    'success': True,
                    'data': playlist.to_dict(viewer=request.user),
                }
            )
        except Exception as e:
            return handle_exception(e)
        
    
    @method_decorator(csrf_protect)
    @method_decorator(require_auth)
    def delete(self, request, playlist_id):
        try:
            playlist = get_playlist_by_id(playlist)
            delete_playlist(playlist, request.user)
            return JsonResponse(
                {
                    'success': True,
                }, status=204
            )
        except Exception as e:
            return handle_exception(e)
    

#POST /api/v1/playlists/<id>/cover/ upload ảnh bìa (auth+owner+csfs)
class PlaylistCoverUploadView(View):
    @method_decorator(csrf_protect)
    @method_decorator(require_auth)
    def post(self, request, playlist_id):
        try:
            validate_cover_image(request.FILES)
            playlist = get_playlist_by_id(playlist_id)
            playlist = update_cover_image(playlist, request.user, request.FILES['cover_image'])
            return JsonResponse(
                {
                    'success': True,
                    'data': {
                        'cover_image': playlist.cover_image.url if playlist.cover_image else None,
                    },
                }
            )
        except Exception as e:
            return handle_exception(e)


#PATCH /api/v1/playlists/<id>/visibility/ đặt public/private (auth+owner+csrf)
class PlaylistVisibilityView(View):
    @method_decorator(csrf_protect)
    @method_decorator(require_auth)
    def patch(self, request, playlist_id):
        try:
            data = parse_json_body(request)
            validated = validate_visibility(data)
            playlist = get_playlist_by_id(playlist_id)
            playlist = update_visibility(playlist, request.user, validated['is_public'])
            return JsonResponse(
                {
                    'success': True,
                    'data': {
                        'is_public': playlist.is_public,
                    },
                }
            )
        except Exception as e:
            return handle_exception(e)
        


#PLAYLIST SONGS VIEWS
#GET /api/v1/playlist/<id>/songs/ danh sách bài hát (public nếu is_public, owner nếu private)
#POST /api/v1/playlist/<id>/songs/ thêm bài hát (auth+owner+csrf)
class PlaylistSongListView(View):
    def get(self, request, playlist_id):
        try:
            #get_playlist_detail tự raise PlaylistNotFound nếu không có quyền xem
            get_playlist_detail(playlist_id, viewer=request.user)

            page = int(request.GET.get('page', 1))
            page_size = min(100, int(request.GET.get('page_size', 50)))
            result = list_playlist_songs(playlist_id, viewer=request.user, page=page, page_size=page_size)
            return JsonResponse(
                {
                    'success': True,
                    'data': result,
                }
            )
        except Exception as e:
            return handle_exception(e)
    

    @method_decorator(csrf_protect)
    @method_decorator(require_auth)
    def post(self, request, playlist_id):
        try:
            data = parse_json_body(request)
            validated = validate_add_song(data)
            playlist = get_playlist_by_id(playlist_id)
            playlist_song = add_song_to_playlist(playlist, request.user, validated['song_id'])
            return JsonResponse(
                {
                    'success': True,
                    'data': playlist_song.to_dict(),
                }, status=201
            )
        except Exception as e:
            return handle_exception(e)
        

#DELETE /api/v1/playlists/<id>/songs/<song_id>/ — Xóa bài hát (Auth+Owner+CSRF)
class PlaylistSongDetailView(View):
    @method_decorator(csrf_protect)
    @method_decorator(require_auth)
    def delete(self, request, playlist_id, song_id):
        try:
            playlist = get_playlist_by_id(playlist_id)
            remove_song_from_playlist(playlist, request.user, song_id)
            return JsonResponse(
                {
                    'success': True,
                }, status=204
                )
        except Exception as e:
            return handle_exception(e)
    
class PlaylistSongDetailView(View):
    """DELETE /api/v1/playlists/<id>/songs/<song_id>/ — Xóa bài hát (Auth+Owner+CSRF)"""

    @method_decorator(csrf_protect)
    @method_decorator(require_auth)
    def delete(self, request, playlist_id, song_id):
        try:
            playlist = get_playlist_by_id(playlist_id)
            remove_song_from_playlist(playlist, request.user, song_id)
            return JsonResponse({'success': True}, status=204)
        except Exception as e:
            return handle_exception(e)

#DELETE /api/v1/playlists/<id>/songs/<song_id>/ xoá bài hát (auth+owner+csrf)
class PlaylistSongReorderView(View):
    @method_decorator(csrf_protect)
    @method_decorator(require_auth)
    def patch(self, request, playlist_id):
        try:
            data = parse_json_body(request)
            validated = validate_reorder(data)
            playlist = get_playlist_detail(playlist_id)
            reorder_playlist_songs(playlist, request.user, validated['song_ids'])
            return JsonResponse(
                {
                    'success': True,
                    'message': 'Đã cập nhật thứ tự'
                }
            )
        except Exception as e:
            return handle_exception(e)

            

