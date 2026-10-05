#namespace URL dành riêng cho các endpoint liên quan đến authentication
#/api/v1/auth

from django.urls import path
from accounts.views import (
    CsrfView,
    RegisterView,
    LoginView,
    LogoutView,
    MeAuthView,
    ChangePasswordView,
    PasswordResetRequestView,
    PasswordResetConfirmView,
)

urlpatterns = [
    #csrf token
    path('csrf/', CsrfView.as_view(), name='auth-csrf'),

    #đăng ký đăng nhập đăng xuất
    path('register/', RegisterView.as_view(), name='auth-register'),
    path('login/', LoginView.as_view(), name='auth-login'),
    path('logout/', LogoutView.as_view(), name='auth-logout'),
    
    #kiểm tra trạng thái đăng nhập
    path('me/', MeAuthView.as_view(), name='auth-me'),

    #đổi mật khẩu
    path('password/change/', ChangePasswordView.as_view(), name='auth-password-change'),

    #đặt lại mật khẩu (quên mật khẩu)
    path('password/reset/request/', PasswordResetRequestView.as_view(), name='auth-password-reset-request'),
    path('password/reset/confirm/', PasswordResetConfirmView.as_view(), name='auth-password-reset-confirm'),
]
