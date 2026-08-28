import json
from django.views import View
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

# Import các file nghiệp vụ
from . import selectors
from . import services
from .exceptions import ChatException
from accounts.exceptions import AppException

def handle_exception(e):
    """Hàm tiện ích để chuyển đổi Exception thành JSON Error Response"""
    if isinstance(e, AppException):
        status_code = 400
        if e.error_code == 'NOT_FOUND':
            status_code = 404
        elif e.error_code in ['NOT_FRIENDS', 'PERMISSION_DENIED']:
            status_code = 403
            
        payload = {'code': e.error_code, 'message': e.message}
        if hasattr(e, 'fields') and e.fields:
            payload['fields'] = e.fields
            
        return JsonResponse({'success': False, 'error': payload}, status=status_code)
    
    # Lỗi hệ thống không lường trước được
    return JsonResponse({
        'success': False, 
        'error': {'code': 'SERVER_ERROR', 'message': str(e)}
    }, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class ConversationListView(View):
    """
    GET /api/v1/chat/conversations/
    Lấy danh sách các cuộc trò chuyện của user hiện tại.
    """
    def get(self, request):
        if not request.user.is_authenticated:
            return JsonResponse({'success': False, 'error': {'code': 'AUTH_REQUIRED', 'message': 'Vui lòng đăng nhập'}}, status=401)
            
        try:
            # Gọi hàm ở selectors.py
            conversations = selectors.list_user_conversations(request.user)
            return JsonResponse({'success': True, 'data': conversations})
        except Exception as e:
            return handle_exception(e)
            
    """
    POST /api/v1/chat/conversations/
    Tạo hoặc mở một cuộc trò chuyện 1-1 với bạn bè.
    Body: { "target_user_id": "<uuid>" }
    """
    def post(self, request):
        if not request.user.is_authenticated:
            return JsonResponse({'success': False, 'error': {'code': 'AUTH_REQUIRED', 'message': 'Vui lòng đăng nhập'}}, status=401)
            
        try:
            body = json.loads(request.body)
            target_user_id = body.get('target_user_id')
            
            if not target_user_id:
                return JsonResponse({'success': False, 'error': {'code': 'VALIDATION_ERROR', 'message': 'Thiếu target_user_id'}}, status=400)
                
            from accounts.models import User
            target_user = User.objects.get(id=target_user_id)
            
            # Gọi hàm ở services.py
            conv, created = services.get_or_create_direct_conversation(request.user, target_user)
            
            return JsonResponse({
                'success': True, 
                'data': conv.to_dict(viewer=request.user),
                'is_new': created
            }, status=201 if created else 200)
            
        except User.DoesNotExist:
            return JsonResponse({'success': False, 'error': {'code': 'NOT_FOUND', 'message': 'Không tìm thấy người dùng'}}, status=404)
        except Exception as e:
            return handle_exception(e)


@method_decorator(csrf_exempt, name='dispatch')
class MessageListView(View):
    """
    GET /api/v1/chat/conversations/<conversation_id>/messages/
    Lấy lịch sử tin nhắn của một cuộc trò chuyện (có phân trang).
    """
    def get(self, request, conversation_id):
        if not request.user.is_authenticated:
            return JsonResponse({'success': False, 'error': {'code': 'AUTH_REQUIRED', 'message': 'Vui lòng đăng nhập'}}, status=401)
            
        try:
            page = int(request.GET.get('page', 1))
            page_size = int(request.GET.get('page_size', 20))
            
            # Gọi hàm ở selectors.py
            result = selectors.list_messages_in_conversation(
                conversation_id=conversation_id,
                user=request.user,
                page=page,
                page_size=page_size
            )
            return JsonResponse({'success': True, 'data': result})
            
        except ValueError:
            return JsonResponse({'success': False, 'error': {'code': 'VALIDATION_ERROR', 'message': 'Tham số phân trang không hợp lệ'}}, status=400)
        except Exception as e:
            return handle_exception(e)
