"""
accounts/views.py

Tầng HTTP cho app accounts.

Quy ước tầng views:
  - Chỉ nhận request, gọi validator/service, trả JsonResponse
  - Không chứa business logic, Không truy vấn DB trực tiếp
  - Bắt exception từ validators/services và map sang HTTP status code
  - Xử lý lỗi theo pattern

Mọi endpoint thay đổi dữ liệu (POST/PATCH/DELETE) dùng @csrf_protect.
GET endpoint không cần CSRF.
"""

import json
import logging

from django.http import JsonResponse
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie

from accounts.decorators import require_auth, require_admin
from accounts.validators import (
    validate_register,
    validate_login,
    validate_update_profile,
    validate_change_password,
    validate_password_reset_request,
    validate_password_reset_confirm,
    validate_id_card_upload,
)
from accounts.services import (
    register_user,
    login_user,
    logout_user,
    update_profile,
    update_avatar,
    update_privacy,
    change_password,
    toggle_block,
    submit_verification,
    approve_verification,
    reject_verification,
)
from accounts.selectors import (
    get_public_profile,
    get_my_verification,
    list_pending_verifications,
)
from accounts.exceptions import (
    ValidationError,
    AuthenticationError,
    PermissionDenied,
    NotFound,
    AlreadyExists,
    AccountInactive,
)

logger = logging.getLogger(__name__)

def _json_body(request) -> dict:
    """Parse JSON body an toàn - trả {} nếu body rỗng hoặc lỗi parse."""
    try:
        return json.loads(request.body or '{}')
    except (json.JSONDecodeError, ValueError):
        return {}
    
def _handle_exception(e: Exception) -> JsonResponse:
    """
    Map exception nghiệp vụ sang HTTP response.
    Dùng chung cho mọi view trong app này.
    """

    if isinstance(e, ValidationError):
        return JsonResponse(
            {
                'success': False,
                'error': {
                    'code': 'VALIDATION_ERROR',
                    'message': e.message,
                    'fields': e.fields
                }
            },
            status=400,
        )
    if isinstance(e, AuthenticationError):
        return JsonResponse (
            {
                'success': False,
                'error': {
                    'code': e.error_code,
                    'message': e.message
                }
            },
            status=401,
        )
    if isinstance(e, (PermissionDenied, AccountInactive)):
        return JsonResponse(
            {
                'success': False,
                'error': {
                    'code': e.error_code,
                    'message': e.message
                }
            },
            status=403,
        )
    if isinstance(e, NotFound):
        return JsonResponse (
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
    
    # Lỗi không mong đợi
    logger.exception('Unhandled exception: %s', e)
    return JsonResponse(
        {
            'success': False,
            'error': {
                'code': 'SERVER_ERROR',
                'message': 'Lỗi server',
            }
        },
        status=500,
    )

# Auth View
@method_decorator(ensure_csrf_cookie, name='dispatch')
class CsrfView(View):
    """
    GET /api/v1/auth/csrf/
    
    Set cookie csrftoken (nếu chưa có) và trả response.
    Client gọi endpoint một lần này trước khi thực hiện POST đầu tiên.
    """

    def get(self, request):
        return JsonResponse({
            'success': True,
            'detail': 'CSRF cookie set'
        })
    
@method_decorator(csrf_protect, name='dispatch')
class RegisterView(View):
    """POST api/v1/auth/register/ - Đăng ký tài khoản mới."""

    def post(self, request):
        try:
            data = _json_body(request)
            validated = validate_register(data)
            user = register_user(validated)
            return JsonResponse (
                {
                    'success': True,
                    'data': user.to_dict(include_private=True)
                },
                status=201,
            )
        except Exception as e:
            return _handle_exception(e)
        
@method_decorator(csrf_protect, name='dispatch')
class LoginView(View):
    """POST /api/v1/auth/login/ - Đăng nhập."""

    def post(self, request):
        try:
            data = _json_body(request)
            validated = validate_login(data)
            user = login_user(request, validated)
            return JsonResponse (
                {
                    'success': True,
                    'data': user.to_dict(include_private=True)
                },
                status=200,
            )
        except Exception as e:
            return _handle_exception(e)
        
@method_decorator([csrf_protect, require_auth], name='dispatch')
class LogoutView(View):
    """POST /api/v1/auth/logout/ - Đăng xuất."""

    def post(self, request):
        logout_user(request)
        return JsonResponse({
            'success': True,
            'message': 'Đã đăng xuất thành công'
        })
    
class MeAuthView(View):
    """GET /api/v1/auth/me/ - Kiểm tra trạng thái đăng nhập."""

    @method_decorator(require_auth)
    def get(self, request):
        return JsonResponse(
            {
                'success': True,
                'data': request.user.to_dict(include_private=True)
            }
        )
    
@method_decorator([csrf_protect, require_auth], name='dispatch')
class ChangePasswordView(View):
    """POST /api/v1/auth/password/change/ - Đổi mật khẩu."""

    def post(self, request):
        try:
            data = _json_body(request)
            validated = validate_change_password(data)
            change_password(
                request,
                request.user,
                validated
            )
            return JsonResponse({
                'success': True,
                'message': 'Đổi mật khẩu thành công',
            })
        except Exception as e:
            return _handle_exception(e)
        
# Account Profile Views
class MyProfileView(View):
    """
    GET /api/v1/accounts/me/ - Xem thông tin cá nhân
    PATCH /api/v1/accounts/me/ - Cập nhật thông tin cá nhân
    """

    @method_decorator(require_auth)
    def get(self, request):
        return JsonResponse(
            {
                'success': True,
                'data': request.user.to_dict(include_private=True),
            }
        )
    
    @method_decorator(csrf_protect)
    @method_decorator(require_auth)
    def patch(self, request):
        try:
            data = _json_body(request)
            validated = validate_update_profile(data)
            if not validated:
                return JsonResponse(
                    {
                        'success': False,
                        'error': {
                            'code': 'VALIDATION_ERROR',
                            'message': 'Không có dữ liệu để cập nhật',
                        }
                    },
                    status=400,
                )
            user = update_profile(request.user, validated)
            return JsonResponse(
                {
                    'success': True,
                    'data': user.to_dict(include_private=True),
                }
            )
        except Exception as e:
            return _handle_exception(e)
        
@method_decorator([csrf_protect, require_auth], name='dispatch')
class AvatarUploadView(View):
    """POST /api/v1/accounts/me/avatar/ - Upload ảnh đại diện."""

    def post(self, request):
        try:
            if 'avatar' not in request.FILES:
                return JsonResponse(
                    {
                        'success': False,
                        'error': {
                            'code': 'VALIDATION_ERROR',
                            'fields': {'avatar': ['File ảnh là bắt buộc']},
                        }
                    },
                    status=400,
                )
            avatar_file = request.FILES['avatar']

            # Validate MIME type ảnh
            allowed_types = {'image/jpeg', 'image/pnj', 'image/webp', 'image/gif'}
            if avatar_file.content_type not in allowed_types:
                return JsonResponse(
                    {
                        'success': False,
                        'error': {
                            'code': 'VALIDATION_ERROR',
                            'fields': {'avatar': ['Chỉ nhấp nhận JPEG, PNG, WEBP, GIF']},
                        }
                    },
                    status=400,
                )
            
            max_size = 5 * 1024 * 1024
            if avatar_file.size > max_size:
                return JsonResponse(
                    {
                        'success': False,
                        'error': {
                            'code': 'VALIDATION_ERROR',
                            'fields': {'avatar': ['File tối đa 5 MB']},
                        }
                    },
                    status=400,
                )
            
            user = update_avatar(request.user, avatar_file)
            return JsonResponse({
                'success': True,
                'data': {
                    'avatar': user.avatar.url if user.avatar else None,
                },
            })
        except Exception as e:
            return _handle_exception(e)

@method_decorator([csrf_protect, require_auth], name='dispatch')
class PrivacyView(View):
    """PATCH /api/v1/accounts/me/privacy/ - Cập nhật chế độ riêng tư."""

    def patch(self, request):
        try:
            data = _json_body(request)
            is_private = data.get('is_private')
            if is_private is None or not isinstance(is_private, bool):
                return JsonResponse(
                    {
                        'success': False,
                        'error': {
                            'code': 'VALIDATION_ERROR',
                            'fields' : {'is_private': ['Giá trị phải là true hoặc false']}
                        }
                    },
                    status=400,
                )
            user = update_privacy(request.user, is_private)
            return JsonResponse({
                'success': True,
                'data': {
                    'is_private': user.is_private
                }
            })
        except Exception as e:
            return _handle_exception(e)

class PublicProfileView(View):
    """GET /api/v1/accounts/users/<user_id>/ - Xem hồ sơ công khai."""

    def get(self, request, user_id):
        try:
            user = get_public_profile(user_id, viewer=request.user)
            # Không include private fields (email) cho người xem
            return JsonResponse({
                'success': True,
                'data': user.to_dict(include_private=False)
            })
        except Exception as e:
            return _handle_exception(e)

# Block Views
@method_decorator([csrf_protect, require_auth], name='dispatch')
class BlockView(View):
    """POST /api/v1/accounts/users/<user_id>/block/ - Block/unblock user."""

    def post(self, request, user_id):
        try:
            result = toggle_block(request.user, user_id)
            return JsonResponse({
                'success': True,
                'data': result
            })
        except Exception as e:
            return _handle_exception(e)
    
# Artist Verification Views
@method_decorator(require_auth, name='dispatch')
class ArtistVerificationView(View):
    """
    GET /api/v1/accounts/artist-verification/me/ - Xem trạng thái yêu cầu
    POST /api/v1/accounts/artist-verification/ - Nộp yêu cầu xác thực
    """

    def get(self, request):
        verification = get_my_verification(request.user)
        if not verification:
            return JsonResponse({
                'success': True,
                'data': None
            })
        return JsonResponse({
            'success': True,
            'data': verification.to_dict()
        })
    
    @method_decorator(csrf_protect)
    def post(self, request):
        try:
            # Validate file minh chứng
            validate_id_card_upload(request.FILES)

            data = {
                'real_name': request.POST.get('real_name', '').strip(),
                'note': request.POST.get('note', '').strip(),
            }

            if not data['real_name']:
                raise ValidationError(
                    'Tên thật là bắt buộc',
                    fields={'real_name': ['Tên thật là bắt buộc']},
                )
            
            verification = submit_verification(
                user=request.user,
                data=data,
                id_card_file=request.FILES['id_card_image'],
            )
            return JsonResponse(
                {
                    'success': True,
                    'data': verification.to_dict()
                }, 
                status=201
            )
        except Exception as e:
            return _handle_exception(e)

@method_decorator(require_admin, name='dispatch')
class AdminVerificationListView(View):
    """GET /api/v1/accounts/admin/verifications/ - Danh sách yêu cầu chờ duyệt."""

    def get(self, request):
        verifications = list_pending_verifications()
        return JsonResponse({
            'success': True,
            'data': {
                'items': [v.to_dict() for v in verifications],
                'total': verifications.count(),
            },
        })
    
@method_decorator([csrf_protect, require_admin], name='dispatch')
class AdminVerificationApproveView(View):
    """POST /api/v1/accounts/admin/verifications/<id>/approve/"""

    def post(self, request, verification_id):
        try:
            verification = approve_verification(verification_id, admin=request.user)
            return JsonResponse({
                'success': True,
                'data': verification.to_dict()
            })
        except Exception as e:
            return _handle_exception(e)

@method_decorator([csrf_protect, require_admin], name='dispatch')
class AdminVerificationRejectView(View):
    """POST /api/v1/accounts/admin/verifications/<id>/reject/"""

    def post(self, request, verification_id):
        try:
            data = _json_body(request)
            reason = data.get('reason', '').strip()
            verification = reject_verification(verification_id, admin=request.user, reason=reason)
            return JsonResponse({
                'success': True,
                'data': verification.to_dict()
            })
        except Exception as e:
            return _handle_exception(e)