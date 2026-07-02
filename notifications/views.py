
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
)

from notifications.exceptions import NotificationNotFound
from notifications.validators import validate_list_notifications_params
from notifications.selectors import (
    list_notifications,
    count_unread,
    get_notification_by_id,
)
from notifications.services import (
    mark_read,
    mark_all_read,
    delete_notification,
)

logger = logging.getLogger(__name__)


def handle_exception(e: Exception) -> JsonResponse:
    if isinstance(e, ValidationError):
        return JsonResponse(
            {
                'success': False,
                'error': {
                    'code': 'VALIDATION_ERROR',
                    'message': e.message,
                }
            }, status=400
        )
    
    if isinstance(e, PermissionDenied):
        return JsonResponse(
            {
                'success': False,
                'error': {
                    'code': e.error_code,
                    'message': e.message,
                },
            }, status=403
            
        )
    
    if isinstance(e, (NotificationNotFound, NotFound)):
        return JsonResponse(
            {
                'success': False,
                'error': {
                    'code': 'NOT_FOUND',
                    'message': e.message,
                },
            }, status=404
        )
    
    logger.exception('Unhandled exception in notification view: %s', e)
    return JsonResponse(
        {
            'success': False,
            'error': {
                'code': 'SERVER_ERROR',
                'message': 'Lỗi server',
            },
        }, status=500
    )


#GET /api/v1/notifications/ danh sách thông báo của tôi
class NotificationListView(View):
    @method_decorator(require_auth)
    def get(self, request):
        try:
            filters = validate_list_notifications_params(request.GET)
            result = list_notifications(
                request.user,
                page=filters['page'],
                page_size=filters['page_size'],
                unread_only=filters['unread_only'],
            )
            return JsonResponse(
                {
                    'success': True,
                    'data': result,
                },
            )
        
        except Exception as e:
            return handle_exception(e)
        


#GET /api/v1/notifications/unread-count/ số thông báo chưa đọc (auth)
class UnreadCountView(View):
    @method_decorator(require_auth)
    def get(self, request):
        try:
            count = count_unread(request.user)
            return JsonResponse(
                {
                    'success': True,
                    'data': {
                        'unread_count': count,
                    },
                },
            )
        except Exception as e:
            return handle_exception(e)
        

#POST /api/v1/notifications/<id>/read/ đánh dấu 1 thông báo đã đọc
class NotificationReadView(View):
    @method_decorator(csrf_protect)
    @method_decorator(require_auth)
    def post(self, request, notification_id):
        try:
            notification = get_notification_by_id(notification_id,request.user)
            notification = mark_read(notification, request.user)

            return JsonResponse(
                {
                    'success': True,
                    'data': notification.to_dict(),
                },
            )
        except Exception as e:
            return handle_exception(e)
        


#Post /api/v1/notification/read-all/ đánh dấu tất cả đã đọc (auth+csrf)
class MarkAllReadView(View):
    @method_decorator(csrf_protect)
    @method_decorator(require_auth)
    def post(self, request):
        try:
            updated = mark_all_read(request.user)
            return JsonResponse(
                {
                    'success': True,
                    'data': {
                        'updated_count': updated
                    },
                },
            )
        
        except Exception as e:
            return handle_exception(e)
        


#delete /api/v1/notifications/<id>/ xoá 1 thông báo (auth+Owner+Csrf)
class NotificationDetailView(View):
    @method_decorator(csrf_protect)
    @method_decorator(require_auth)
    def delete(self, request, notification_id):
        try:
            notification = get_notification_by_id(notification_id, request.user)
            delete_notification(notification, request.user)
            return JsonResponse(
                {
                    'success': True,
                }, status=204
            )
        except Exception as e:
            return handle_exception(e)