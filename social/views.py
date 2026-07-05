"""
social/views.py
"""

import json
import logging

from django.http import JsonResponse
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect

from accounts.decorators import require_auth
from accounts.exceptions import ValidationError, PermissionDenied, NotFound, AlreadyExists

from social.exceptions import CannotFollowSelf, FollowTargetNotFound, BlockedFollowError, MoodNotFound
from social.validators import validate_set_mood, validate_list_feed_params, validate_list_follow_params
from social.selectors import (
    is_following, get_follow_counts, list_followers, list_following,
    get_my_mood, get_user_mood, list_feed, list_my_activities,
)
from social.services import (
    toggle_follow, set_mood, delete_mood,
    accept_follow_request, reject_follow_request, cancel_follow_request,
)
from social.models import FollowRequest, MoodType, MoodTheme
from social.selectors import list_friends

logger = logging.getLogger(__name__)


class MoodThemeListView(View):
    """
    GET /api/v1/social/mood-themes/
    Trả về danh sách bản màu chủ đề (Theme) do Admin tạo.
    Frontend dùng để render ô chọn màu khi user viết custom mood.
    """

    def get(self, request):
        themes = MoodTheme.objects.filter(is_active=True).order_by('name')
        return JsonResponse({
            'success': True,
            'data': [t.to_dict() for t in themes],
        })


class MoodTypeListView(View):
    """
    GET /api/v1/social/mood-types/
    Trả về danh sách loại cảm xúc do Admin tạo - không cần đăng nhập.
    Frontend dùng để render các card chọn cảm xúc một cách dynamic.
    """

    def get(self, request):
        mood_types = MoodType.objects.filter(is_active=True).order_by('order', 'name')
        return JsonResponse({
            'success': True,
            'data': [mt.to_dict() for mt in mood_types],
        })

def parse_json_body(request) -> dict:
    """Parse json body an toàn - trả {} nếu rỗng hoặc lỗi parse"""
    try:
        return json.loads(request.body or '{}')
    except (json.JSONDecodeError, ValueError):
        return {}
    
def handle_exception(e: Exception) -> JsonResponse:
    """Map exception nghiệp vụ sang HTTP response chuẩn. Dùng chung cho mọi view"""
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
    
    if isinstance(e, CannotFollowSelf):
        return JsonResponse(
            {
                'success': False,
                'error': {
                    'code': e.error_code,
                    'message': e.message
                }
            },
            status=400,
        )
    
    if isinstance(e, (BlockedFollowError, PermissionDenied)):
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
    
    if isinstance(e, (FollowTargetNotFound, MoodNotFound, NotFound)):
        return JsonResponse(
            {
                'success': False,
                'error': {
                    'code': 'NOT_FOUND',
                    'message': e.message
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
    
    logger.exception('Unhandle exception in social views: %s', e)
    return JsonResponse(
        {
            'success': False,
            'error': {
                'code': 'SERVER_ERROR',
                'message': 'Lỗi server'
            }
        },
        status=500,
    )

# Follow View
class FollowToggleView(View):
    """
    POST /api/v1/social/users/<user_id>/follow/ - Toggle follow/unfollow (Auth+CSRF)
    """
    
    @method_decorator(csrf_protect)
    @method_decorator(require_auth)
    def post(self, request, user_id):
        try:
            result = toggle_follow(request.user, user_id)
            return JsonResponse(
                {
                    'success': True,
                    'data': result,
                }
            )
        except Exception as e:
            return handle_exception(e)
        
class FollowStatusView(View):
    """GET /api/v1/social/user/<user_id>/follow-status/ - Trạng thái follow + số lượng"""

    def get(self, request, user_id):
        try:
            counts = get_follow_counts(user_id)
            viewer_id = getattr(request.user, 'id', None)
            am_following = False
            if viewer_id and getattr(request.user, 'is_authenticated', False):
                am_following = is_following(viewer_id, user_id)
            return JsonResponse(
                {
                    'success': True,
                    'data': {
                        **counts,
                        'is_following': am_following
                    }
                }
            )
        except Exception as e:
            return handle_exception(e)
        
class FollowersListView(View):
    """
    GET /api/v1/social/users/<user_id>/followers/ - Danh sách follower
    """

    def get(self, request, user_id):
        try:
            filters = validate_list_follow_params(request.GET)
            result = list_followers(
                user_id, 
                viewer=request.user, 
                page=filters['page'], 
                page_size=filters['page_size'],
            )
            return JsonResponse(
                {
                    'success': True,
                    'data': result,
                }
            )
        except Exception as e:
            return handle_exception(e)
        
class FollowingListView(View):
    """
    GET /api/v1/social/users/<user_id>/following/ - Danh sách following
    """

    def get(self, request, user_id):
        try:
            filters = validate_list_follow_params(request.GET)
            result = list_following(
                user_id,
                viewer=request.user,
                page=filters['page'],
                page_size=filters['page_size'],
            )
            return JsonResponse(
                {
                    'success': True,
                    'data': result,
                }
            )
        except Exception as e:
            return handle_exception(e)
        
# Mood View
class MyMoodView(View):
    """
    GET /api/v1/social/me/mood/ - Xem mood hiện tại của tôi
    POST /api/v1/social/me/mood/ - Thiết lập/cập nhật mood
    DELETE /api/v1/social/me/mood/ - Xoá mood hiện tại
    """

    @method_decorator(require_auth)
    def get(self, request):
        try:
            mood = get_my_mood(request.user)
            return JsonResponse(
                {
                    'success': True,
                    'data': mood.to_dict(),
                }
            )
        except Exception as e:
            return handle_exception(e)
        
    @method_decorator(csrf_protect)
    @method_decorator(require_auth)
    def post(self, request):
        try:
            data = parse_json_body(request)
            validated = validate_set_mood(data)
            mood = set_mood(request.user, validated)
            return JsonResponse(
                {
                    'success': True,
                    'data': mood.to_dict(),
                },
                status=201,
            )
        except Exception as e:
            return handle_exception(e)
        
    @method_decorator(csrf_protect)
    @method_decorator(require_auth)
    def delete(self, request):
        try:
            delete_mood(request.user)
            return JsonResponse(
                {
                    'success': True,
                },
                status=204,
            )
        except Exception as e:
            return handle_exception(e)
        
class UserMoodView(View):
    """
    GET /api/v1/social/feed/ - Bảng tin hoạt động của những người tôi theo dõi (Auth)
    """
    
    def get(self, request, user_id):
        try:
            mood = get_user_mood(user_id, viewer=request.user)
            return JsonResponse(
                {
                    'success': True,
                    'data': mood.to_dict() if mood else None,
                }
            )
        except Exception as e:
            return handle_exception(e)
        
# Feed View
class FeedView(View):
    """
    GET /api/v1/social/feed/ - Bảng tin hoạt động của những người tôi theo dõi
    """

    @method_decorator(require_auth)
    def get(self, request):
        try:
            filters = validate_list_feed_params(request.GET)
            result = list_feed(request.user, page=filters['page'], page_size=filters['page_size'])
            return JsonResponse(
                {
                    'success': True,
                    'data': result,
                }
            )
        except Exception as e:
            return handle_exception(e)
        
class MyActivitiesView(View):
    """
    GET /api/v1/social/me/activities/ - Lịch sử hoạt động của chính nó
    """
    
    @method_decorator(require_auth)
    def get(self, request):
        try:
            filters = validate_list_feed_params(request.GET)
            result = list_my_activities(request.user, page=filters['page'], page_size=filters['page_size'])
            return JsonResponse({'success': True, 'data': result})
        except Exception as e:
            return handle_exception(e)


# ─────────────────────────────────────────────
# FOLLOW REQUEST VIEWS
# ─────────────────────────────────────────────

class FollowRequestReceivedView(View):
    """GET /api/v1/social/follow-requests/received/ - Yêu cầu nhận được"""
    @method_decorator(require_auth)
    def get(self, request):
        try:
            reqs = FollowRequest.objects.filter(receiver=request.user).select_related('sender')
            items = [r.to_dict() for r in reqs]
            return JsonResponse({'success': True, 'data': {'items': items, 'total': len(items)}})
        except Exception as e:
            return handle_exception(e)


class FollowRequestSentView(View):
    """GET /api/v1/social/follow-requests/sent/ - Yêu cầu đã gửi"""
    @method_decorator(require_auth)
    def get(self, request):
        try:
            reqs = FollowRequest.objects.filter(sender=request.user).select_related('receiver')
            items = [r.to_dict() for r in reqs]
            return JsonResponse({'success': True, 'data': {'items': items, 'total': len(items)}})
        except Exception as e:
            return handle_exception(e)


class FollowRequestAcceptView(View):
    """POST /api/v1/social/follow-requests/<id>/accept/"""
    @method_decorator(csrf_protect)
    @method_decorator(require_auth)
    def post(self, request, request_id):
        try:
            accept_follow_request(request.user, request_id)
            return JsonResponse({'success': True, 'message': 'Đã chấp nhận yêu cầu kết bạn.'})
        except Exception as e:
            return handle_exception(e)


class FollowRequestRejectView(View):
    """POST /api/v1/social/follow-requests/<id>/reject/"""
    @method_decorator(csrf_protect)
    @method_decorator(require_auth)
    def post(self, request, request_id):
        try:
            reject_follow_request(request.user, request_id)
            return JsonResponse({'success': True, 'message': 'Đã từ chối yêu cầu kết bạn.'})
        except Exception as e:
            return handle_exception(e)


class FollowRequestCancelView(View):
    """POST /api/v1/social/follow-requests/<id>/cancel/ - Người GỮi hủy yêu cầu"""
    @method_decorator(csrf_protect)
    @method_decorator(require_auth)
    def post(self, request, request_id):
        try:
            cancel_follow_request(request.user, request_id)
            return JsonResponse({'success': True, 'message': 'Đã hủy yêu cầu kết bạn.'})
        except Exception as e:
            return handle_exception(e)


class FriendsListView(View):
    """GET /api/v1/social/friends/ - Danh sách bạn bè (follow 2 chiều)"""
    @method_decorator(require_auth)
    def get(self, request):
        try:
            page = int(request.GET.get('page', 1))
            page_size = int(request.GET.get('page_size', 50))
            q = request.GET.get('q', '').strip()
            
            result = list_friends(request.user, page=page, page_size=page_size, search_query=q)
            return JsonResponse({'success': True, 'data': result})
        except Exception as e:
            return handle_exception(e)