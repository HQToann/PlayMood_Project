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
            
    def post(self, request, conversation_id):
        """
        POST /api/v1/chat/conversations/<conversation_id>/messages/
        Gửi tin nhắn thông qua API (Dùng cho tính năng chia sẻ)
        """
        if not request.user.is_authenticated:
            return JsonResponse({'success': False, 'error': {'code': 'AUTH_REQUIRED', 'message': 'Vui lòng đăng nhập'}}, status=401)
            
        try:
            body = json.loads(request.body)
            # Gọi services để tạo tin nhắn
            msg = services.create_message(request.user, conversation_id, body)
            
            # Bắn qua WebSocket để real-time cho các thành viên trong room
            from channels.layers import get_channel_layer
            from asgiref.sync import async_to_sync
            channel_layer = get_channel_layer()
            if channel_layer:
                async_to_sync(channel_layer.group_send)(
                    f'chat_{conversation_id}',
                    {
                        'type': 'chat_message',
                        'message_data': msg.to_dict()
                    }
                )
            
            return JsonResponse({'success': True, 'data': msg.to_dict()}, status=201)
        except Exception as e:
            return handle_exception(e)

@method_decorator(csrf_exempt, name='dispatch')
class UploadImageView(View):
    """
    POST /api/v1/chat/upload-image/
    Upload ảnh lên server/cloudinary và trả về URL để gửi qua WebSockets.
    """
    def post(self, request):
        if not request.user.is_authenticated:
            return JsonResponse({'success': False, 'error': {'code': 'AUTH_REQUIRED', 'message': 'Vui lòng đăng nhập'}}, status=401)
            
        try:
            image_file = request.FILES.get('image')
            if not image_file:
                return JsonResponse({'success': False, 'error': {'code': 'VALIDATION_ERROR', 'message': 'Không có file ảnh'}}, status=400)
                
            # Kiểm tra định dạng
            allowed_types = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
            if image_file.content_type not in allowed_types:
                return JsonResponse({'success': False, 'error': {'code': 'VALIDATION_ERROR', 'message': 'Định dạng ảnh không hợp lệ'}}, status=400)
                
            # Upload dùng default_storage (sẽ tự động đẩy lên Cloudinary theo settings)
            from django.core.files.storage import default_storage
            import uuid
            
            ext = image_file.name.split('.')[-1]
            filename = f"chat_images/{uuid.uuid4()}.{ext}"
            path = default_storage.save(filename, image_file)
            url = default_storage.url(path)
            
            # Đảm bảo dùng HTTPS cho Cloudinary URL nếu có thể (nhưng default_storage thường tự lo)
            return JsonResponse({
                'success': True, 
                'data': {
                    'image_url': url
                }
            })
            
        except Exception as e:
            return handle_exception(e)
