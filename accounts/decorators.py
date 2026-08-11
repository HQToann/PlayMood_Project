# accounts/decorators.py
# Decorators xác thực và phân quyền.

# Dùng trong views để kiểm soát quyền truy cập:
#   @require_auth       -> phải đăng nhập
#   @require_artist     -> phải là nghệ sĩ
#   @require_admin      -> phải là admin

# Thứ tự decorator đúng trong views:
#   @method_decorator(csrf_protect)   Ngoài cùng kiểm tra CSRF trước
#   @method_decorator(require_auth)   Trong kiểm tra session
#   def post(self, request): ...

# Hoặc dùng với Class-Based View:
#   @method_decorator([csrf_protect, require_auth], name='dispatch')
#   class MyView(View): ...

from functools import wraps
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_protect as django_csrf_protect


def require_auth(view_func):
    #kiểm tra đăng nhập trả 401 JSON thay vì redirect login
    #áp dụng cho mọi endpoint yêu cầu đăng nhập
    #nếu tài khoản bị khóa (is_active=False), trả 403

    @wraps (view_func)
    def wrapper(request, *args, **kwargs):
        #kiểm tra is_active trước is_authenticated
        #Django's force_login() (dùng trong test) bypass AuthenticationBackend
        #và có thể đặt user inactive vào request phải kiểm tra DB-level is_active

        if request.user.is_authenticated:
            #kiểm tra từ DB để đám bảo chính xác
            if not request.user.is_active:
                return JsonResponse(
                    {
                        'success': False,
                        'error': {
                            'code': 'ACCOUNT_INACTIVE',
                            'message': 'Tài khoản đã bị khóa'
                        },
                    }, status=403,
                )
            return view_func(request, *args, **kwargs)
        
        return JsonResponse(
            {
                'success': False,
                'error': {
                    'code': 'AUTH_REQUIRED',
                    'message': 'Cần đăng nhập để thực hiện hành động này'
                },
            }, status=401,
        )
    
    return wrapper


def require_artist(view_func):
    #kiểm tra quyền role = artist
    #bao gồm require_auth không cần dùng cả hai một lúc

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        #kiểm tra đăng nhập trước
        if not request.user.is_authenticated:
            return JsonResponse(
                {
                    'success': False,
                    'error': {
                        'code': 'AUTH_REQUIRED',
                        'message': 'Cần phải đăng nhập',
                    },
                }, status=401,
            )
        if not request.user.is_active:
            return JsonResponse(
                {
                    'success': False,
                    'error': {
                        'code': 'ACCOUNT_INACTIVE',
                        'message': 'Tài khoản đã bị khóa',
                    },
                }, status=403,
            )
        
        if request.user.role != 'artist':
            return JsonResponse(
                {
                    'success': False,
                    'error': {
                        'code':    'ARTIST_ONLY',
                        'message': 'Chỉ nghệ sĩ mới được thực hiện hành động này',
                    },
                },
                status=403,
            )

        return view_func(request, *args, **kwargs)
    

    return wrapper



def require_admin(view_func):
    #kiểm tra quyền admin — chấp nhận cả role='admin' lẫn is_superuser Django
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse(
                {
                    'success': False,
                    'error': {
                        'code': 'AUTH_REQUIRED',
                        'message': 'Cần phải đăng nhập',
                    },
                }, status=401
            )
        if not request.user.is_active:
            return JsonResponse(
                {
                    'success': False,
                    'error': {
                        'code': 'ACCOUNT_INACTIVE',
                        'message': 'Tài khoản đã bị khóa',
                    },
                }, status=403,
            )
        # Dùng is_admin property (= role=='admin' OR is_superuser)
        if not request.user.is_admin:
            return JsonResponse(
                {
                    'success': False,
                    'error': {
                        'code': 'ADMIN_ONLY',
                        'message': 'Chỉ quản trị viên mới được thực hiện hành động này',
                    },
                }, status=403,
            )
        
        return view_func(request, *args, **kwargs)
    
    
    return wrapper