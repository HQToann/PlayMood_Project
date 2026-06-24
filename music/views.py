"""
music/views.py

Tầng HTTP cho app music.

Quy ước:
  - views.py KHÔNG import Song, Genre, Comment... để query trực tiếp
  - Mọi query qua selectors.py, mọi ghi qua services.py
  - Exception từ services/selectors được map sang HTTP status
"""

import json
import logging

from django.http import JsonResponse
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect

from accounts.decorators import require_auth, require_artist, require_admin
from accounts.exceptions import (
    ValidationError,
    PermissionDenied,
    NotFound,
    AlreadyExists,
    AppException,
)
from music.exceptions import (
    SongNotFound,
    GenreNotFound,
    CommentNotFound,
    NotSongOwner,
    NotCommentOwner,
    DownloadNotAllowed,
    BlockedByArtist,
    GenreHasSongs,
    SongAlreadyPublished,
    InvalidParentComment,
    ReportNotFound,
)
from music.validators import (
    validate_genre,
    validate_song_create,
    validate_song_update,
    validate_rating,
    validate_comment,
    validate_report,
    validate_list_songs_params,
)
from music.selectors import (
    list_genres,
    get_genre_by_id,
    list_songs,
    list_trending_songs,
    get_song_by_id,
    get_song_detail,
    get_song_like_count,
    get_song_rating_stats,
    list_comments,
    get_comment_by_id,
    list_listen_history,
    list_reports,
    get_report_by_id,
)
from music.services import (
    create_genre, update_genre, delete_genre,
    create_song, update_song, delete_song, publish_song, hide_song,
    admin_hide_song, admin_toggle_trending,
    record_play,
    toggle_like,
    upsert_rating,
    create_comment, delete_comment, admin_hide_comment, toggle_comment_like,
    clear_listen_history,
    create_report, resolve_report,
)

logger = logging.getLogger(__name__)

# Helpers
def parse_json_body(request) -> dict:
    """Parse JSON body an toàn."""
    try:
        return json.loads(request.body or '{}')
    except (json.JSONDecodeError, ValueError):
        return {}
    
def handle_exception(e: Exception) -> JsonResponse:
    """Map exception nghiệp vụ sang HTTP response chuẩn."""
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
    if isinstance(e, (GenreHasSongs, SongAlreadyPublished, InvalidParentComment)):
        return JsonResponse(
            {
                'success': False,
                'error': {
                    'code': e.error_code,
                    'message': e.message,
                }
            },
            status=400,
        )
    if isinstance(e, (NotSongOwner, NotCommentOwner, PermissionDenied, DownloadNotAllowed, BlockedByArtist)):
        return JsonResponse(
            {
                'success': False,
                'error': {
                    'code': e.error_code,
                    'message': e.message,
                }
            },
            status=403,
        )
    if isinstance(e, (SongNotFound, GenreNotFound, CommentNotFound, ReportNotFound, NotFound)):
        return JsonResponse(
            {
                'success': False,
                'error': {
                    'code': 'NOT_FOUND',
                    'message': e.message,
                }
            },
            status=404,
        )
    if isinstance(e, AlreadyExists):
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
    logger.exception('Unhandled exception in music views: %s', e)
    return JsonResponse(
        {
            'success': False,
            'error': {
                'code': 'SERVER_ERROR',
                'message': 'Lỗi Server'
            }
        },
        status=500,
    )

# Genre Views
class GenreListView(View):
    """
    GET /api/v1/music/genres/ - Publish
    POST /api/v1/music/genres/ - Admin
    """

    def get(self, request):
        genres = list_genres()
        return JsonResponse(
            {
                'success': True,
                'data': {
                    'items': genres,
                    'total': len(genres),
                }
            }
        )
    @method_decorator(csrf_protect)
    @method_decorator(require_admin)
    def post(self, request):
        try:
            data = parse_json_body(request)
            validated = validate_genre(data)
            genre = create_genre(validated)
            return JsonResponse(
                {
                    'success': True,
                    'data': genre.to_dict(),
                },
                status=201,
            )
        except Exception as e:
            return handle_exception(e)

class GenreDetailView(View):
    """
    PUT /api/v1/music/genres/<id>/ - Admin
    DELETE /api/v1/music/genres/<id>/ - Admin
    """
    @method_decorator(csrf_protect)
    @method_decorator(require_admin)
    def put(self, request, genre_id):
        try:
            data = parse_json_body(request)
            validated = validate_genre(data)
            genre = get_genre_by_id(genre_id)
            genre = update_genre(genre, validated)
            return JsonResponse(
                {
                    'success': True,
                    'data': genre.to_dict(),
                }
            )
        except Exception as e:
            return handle_exception(e)
        
    @method_decorator(csrf_protect)
    @method_decorator(require_admin)
    def delete(self, request, genre_id):
        try:
            genre = get_genre_by_id(genre_id)
            delete_genre(genre)
            return JsonResponse({'success': True}, status=204)
        except Exception as e:
            return handle_exception(e)

# Song Views
class SongListView(View):
    """
    GET /api/v1/music/songs/ - Public
    POST /api/v1/music/songs/ - Artist
    """
    def get(self, request):
        #try:
            filters = validate_list_songs_params(request.GET)
            result = list_songs(filters, viewer=request.user)
            return JsonResponse(
                {
                    'success': True,
                    'data': result,
                }
            )
        #except Exception as e:
            #return handle_exception(e)
    
    @method_decorator(csrf_protect)
    @method_decorator(require_artist)
    def post(self, request):
        try:
            # multipart/form-data: data từ POST, files từ FILES
            validated = validate_song_create(request.POST, request.FILES)
            song = create_song(artist=request.user, data=validated, files=request.FILES)
            return JsonResponse(
                {
                    'success': True,
                    'data': song.to_dict(viewer=request.user),
                },
                status=201,
            )
        except Exception as e:
            return handle_exception(e)

class SongTrendingView(View):
    """GET /api/v1/music/songs/trending/ - Public."""
    def get(self, request):
        songs = list_trending_songs()
        return JsonResponse(
            {
                'success': True,
                'data': {
                    'items': songs,
                    'total': len(songs)
                }
            }
        )
    
class SongDetailView(View):
    """
    GET /api/v1/music/songs/<id>/ - Public
    PATCH /api/v1/music/songs/<id>/ - Artist+Owner
    DELETE /api/v1/music/songs/<id>/ - Artist+Owner
    """
    def get(self, request, song_id):
        try:
            song = get_song_detail(song_id, viewer=request.user)
            return JsonResponse(
                {
                    'success': True,
                    'data': song.to_dict(viewer=request.user)
                }
            )
        except Exception as e:
            return handle_exception(e)
        
    @method_decorator(csrf_protect)
    @method_decorator(require_artist)

    def patch(self, request, song_id):
        try:
            song = get_song_by_id(song_id)
            # Hỗ trợ cả JSON (chỉ update text) và multipart/form-data (có file)
            if request.content_type and 'multipart/form-data' in request.content_type:
                data = request.POST
            else:
                data = parse_json_body(request)
            validated = validate_song_update(data, request.FILES)
            if not validated:
                return JsonResponse(
                    {'success': False, 'error': {'code': 'VALIDATION_ERROR',
                                                'message': 'Không có dữ liệu để cập nhật'}},
                    status=400,
                )
            song = update_song(song, request.user, validated, request.FILES)
            return JsonResponse({'success': True, 'data': song.to_dict(viewer=request.user)})
        except Exception as e:
            return handle_exception(e)

    @method_decorator(csrf_protect)
    @method_decorator(require_artist)
    def delete(self, request, song_id):
        try:
            song = get_song_by_id(song_id)
            delete_song(song, request.user)
            return JsonResponse(
                {
                    'success': True
                },
                status=204,
            )
        except Exception as e:
            return handle_exception(e)
        
class SongPublishView(View):
    """POST /api/v1/music/songs/<id>/publish/ - Artist+Owner"""
    @method_decorator(csrf_protect)
    @method_decorator(require_artist)
    def post(self, request, song_id):
        try:
            song = get_song_by_id(song_id)
            song = publish_song(song, request.user)
            return JsonResponse(
                {
                    'success': True,
                    'data': {
                        'id': str(song.id),
                        'status': song.status,
                        'released_at': song.released_at.isoformat() if 
                        song.released_at else None,
                    },
                }
            )
        except Exception as e:
            return handle_exception(e)
        
class SongHideView(View):
    """POST /api/v1/music/songs/<id>/hide/ - Artist+Owner."""
    @method_decorator(csrf_protect)
    @method_decorator(require_artist)
    def post(self, request, song_id):
        try:
            song = get_song_by_id(song_id)
            song = hide_song(song, request.user)
            return JsonResponse(
                {
                    'success': True,
                    'data': {
                        'id': str(song.id),
                        'status': song.status,
                    }
                }
            )
        except Exception as e:
            return handle_exception(e)
        
class SongPlayView(View):
    """POST /api/v1/music/songs/<id>/play/ - Auth."""
    @method_decorator(require_auth)
    def post(self, request, song_id):
        try:
            song = get_song_detail(song_id, viewer=request.user)
            play_count = record_play(request.user, song)
            return JsonResponse(
                {
                    'success': True,
                    'data': {'play_count': play_count}
                }
            )
        except Exception as e:
            return handle_exception(e)

class SongDownloadView(View):
    """
    GET api/v1/music/songs/<id>/download/ - Auth
    
    Trả Cloudinary signed URL (redirect) khi production
    hoặc URL file trực tiếp khi dev.
    """

    @method_decorator(require_auth)
    def get(self, request, song_id):
        try:
            song = get_song_detail(song_id, viewer=request.user)

            if song.status != Song.STATUS_PUBLISHED:
                raise SongNotFound()
            
            if not song.allow_download:
                raise DownloadNotAllowed()
            
            # Trả URL của file Cloudinary
            audio_url = song.audio_file.url if song.audio_file else None
            if not audio_url:
                raise SongNotFound('File audio không tồn tại')
            ext = song.audio_file.name.split('.')[-1] if '.' in song.audio_file.name else 'mp3'
            filename = f"{song.title}.{ext}"

            return JsonResponse(
                {
                    'success': True,
                    'data': {
                        'download_url': audio_url,
                        'filename': filename,
                        'expires_in': 300, # giây (Cloudinary signed URL)
                    }
                }
            )
        except Exception as e:
            return handle_exception(e)
        
from music.models import Song

class SongLikeView(View):
    """
    GET /api/v1/music/songs/<id>/likes/ - Public
    POST /api/v1/music/songs/<id>/likes/ - Auth+CSRF
    """
    def get(self, request, song_id):
        try:
            result = get_song_like_count(song_id, viewer=request.user)
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
    def post(self, request, song_id):
        try:
            song = get_song_detail(song_id, viewer=request.user)
            result = toggle_like(request.user, song)
            return JsonResponse(
                {
                    'success': True,
                    'data': result,
                }
            )
        except Exception as e:
            return handle_exception(e)
        
# Rating View
class SongRatingView(View):
    """
    GET /api/v1/music/songs/<id>/rating/ - Public
    POST /api/v1/music/sóng/<id>/rate - Auth+CSRF
    """
    def get(self, request, song_id):
        try:
            result = get_song_rating_stats(song_id, viewer=request.user)
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
    def post(self, request, song_id):
        try:
            data = parse_json_body(request)
            validated = validate_rating(data)
            song = get_song_detail(song_id, viewer=request.user)
            result = upsert_rating(request.user, song, validated['score'])
            return JsonResponse(
                {
                    'success': True,
                    'data': result
                }
            )
        except Exception as e:
            return handle_exception(e)
        
# Comment Views
class SongCommentListView(View):
    """
    GET /api/v1/music/songs/<id>/comments/ - Public
    POST /api/v1/music/songs/<id>/comments/ - Auth+CSRF
    """
    def get(self, request, song_id):
        try:
            page = int(request.GET.get('page', 1))
            page_size = min(100, int(request.GET.get('page_size', 20)))
            result = list_comments(song_id, viewer=request.user, page=page, page_size=page_size)
            return JsonResponse(
                {

                    'success': True,
                    'data': result
                }
            )
        except Exception as e:
            return handle_exception(e)
        
    @method_decorator(csrf_protect)
    @method_decorator(require_auth)
    def post(self, request, song_id):
        try:
            # Dùng get_song_by_id (không check block) để service create_comment
            # tự raise BlockedByArtist -> 403, thay vì get_song_detail trả 404
            # giấu thông tin (chỉ dùng cho việc xem bài hát, không phải comment).
            song      = get_song_by_id(song_id)
            data      = parse_json_body(request)
            validated = validate_comment(data)
            comment   = create_comment(request.user, song, validated)
            return JsonResponse(
                {'success': True, 'data': comment.to_dict(viewer=request.user)},
                status=201,
            )
        except Exception as e:
            return handle_exception(e)
        
class CommentDetailView(View):
    """DELETE /api/v1/music/comments/<id>/ — Auth+Owner+CSRF"""

    @method_decorator(csrf_protect)
    @method_decorator(require_auth)
    def delete(self, request, comment_id):
        try:
            comment = get_comment_by_id(comment_id)
            delete_comment(comment, request.user)
            return JsonResponse(
                {
                    'success': True
                }, 
                status=204)
        except Exception as e:
            return handle_exception(e)
        
class CommentLikeView(View):
    """POST /api/v1/music/comments/<id>/like/ — Auth+CSRF"""

    @method_decorator(csrf_protect)
    @method_decorator(require_auth)
    def post(self, request, comment_id):
        try:
            comment = get_comment_by_id(comment_id)
            result  = toggle_comment_like(request.user, comment)
            return JsonResponse({'success': True, 'data': result})
        except Exception as e:
            return handle_exception(e)

# ListenHistory Views
class ListenHistoryView(View):
    """
    GET /api/v1/music/me/history/ - Auth
    DELETE /api/v1/music/me/history/ - Auth+CSRF
    """

    @method_decorator(require_auth)
    def get(self, request):
        try:
            page = int(request.GET.get('page', 1))
            page_size = min(100, int(request.GET.get('page_size', 20)))
            result = list_listen_history(request.user, page=page, page_size=page_size)
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
    def delete(self, request):
        try:
            clear_listen_history(request.user)
            return JsonResponse(
                {
                    'success': True
                },
                status=204,
            )
        except Exception as e:
            return handle_exception(e)
        
# Report Views
class ReportCreateView(View):
    """POST /api/v1/music/reports/ - Auth+CSRF."""
    @method_decorator(csrf_protect)
    @method_decorator(require_auth)
    def post(self, request):
        try:
            data = parse_json_body(request)
            validated = validate_report(data)
            report = create_report(request.user, validated)
            return JsonResponse(
                {
                    'success': True,
                    'data': report.to_dict(),
                },
                status=201
            )
        except Exception as e:
            return handle_exception(e)
    
class AdminReportListView(View):
    """GET /api/v1/music/admin/reports/ — Admin"""

    @method_decorator(require_admin)
    def get(self, request):
        try:
            filters = {
                'status':      request.GET.get('status', ''),
                'target_type': request.GET.get('target_type', ''),
                'page':        request.GET.get('page', 1),
                'page_size':   request.GET.get('page_size', 20),
            }
            result = list_reports(filters)
            return JsonResponse({'success': True, 'data': result})
        except Exception as e:
            return handle_exception(e)

class AdminReportResolveView(View):
    """POST /api/v1/music/admin/reports/<id>/resolve/ - Admin+CSRF"""
    @method_decorator(csrf_protect)
    @method_decorator(require_admin)
    def post(self, request, report_id):
        try:
            data = parse_json_body(request)
            action = data.get('action', '').strip()
            note = data.get('note', '').strip()
            report = get_report_by_id(report_id)
            report = resolve_report(report, request.user, action, note)
            return JsonResponse(
                {
                    'success': True,
                    'data': report.to_dict(),
                }
            )
        except Exception as e:
            return handle_exception(e)

# Admin Song/Comment Views
class AdminSongTrendingView(View):
    """POST /api/v1/music/admin/songs/<id>/trending/  Admin+CSRF"""

    @method_decorator(csrf_protect)
    @method_decorator(require_admin)
    def post(self, request, song_id):
        try:
            song = get_song_by_id(song_id)
            song = admin_toggle_trending(song)
            return JsonResponse(
                {
                    'success': True,
                    'data': {
                        'id': str(song.id),
                        'is_trending': song.is_trending,
                    },
                }
            )
        except Exception as e:
            return handle_exception(e)

class AdminSongHideView(View):
    """POST /api/v1/music/admin/songs/<id>/hide/ - Admin+CSRF"""
    @method_decorator(csrf_protect)
    @method_decorator(require_admin)
    def post(self, request, song_id):
        try:
            song = get_song_by_id(song_id)
            song = admin_hide_song(song)
            return JsonResponse(
                {
                    'success': True,
                    'data': {
                        'id': str(song.id),
                        'status': song.status,
                    },
                }
            )
        except Exception as e:
            return handle_exception(e)

class AdminCommentHideView(View):
    """POST /api/v1/music/admin/comments/<id>/hide/ - Admin+CSRF"""
    @method_decorator(csrf_protect)
    @method_decorator(require_admin)
    def post(self, request, comment_id):
        try:
            comment = get_comment_by_id(comment_id)
            comment = admin_hide_comment(comment)
            return JsonResponse(
                {
                    'success': True,
                    'data': {
                        'id': str(comment.id),
                        'is_hidden': comment.is_hidden,
                    }
                }
            )
        except Exception as e:
            return handle_exception(e)