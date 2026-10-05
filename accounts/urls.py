#namespace URL dành riêng cho endpoint quản lý tài khoảng
#/api/v1/accounts/

from django.urls import path
from accounts.views import (
    MyProfileView,
    ImageUploadView,
    PrivacyView,
    PublicProfileView,
    BlockView,
    BlockListView,
    ArtistVerificationView,
    AdminVerificationListView,
    AdminVerificationApproveView,
    AdminVerificationRejectView,
    NotificationSettingsView,
)

urlpatterns = [
    #hồ sơ cá nhân
    path('me/', MyProfileView.as_view(), name='account-me'),
    path('me/images/', ImageUploadView.as_view(), name='account-images'),
    path('me/privacy/', PrivacyView.as_view(), name='account-privacy'),
    path('me/notifications/', NotificationSettingsView.as_view(), name='account-notifications'),
    path('me/blocks/', BlockListView.as_view(), name='account-block-list'),

    #hồ sơ công khai
    path('users/<uuid:user_id>/', PublicProfileView.as_view(), name='account-public-profile'),

    #block
    path('users/<uuid:user_id>/block/', BlockView.as_view(), name='account-block'),

    #xác thực nghệ sĩ
    path('artist-verification/', ArtistVerificationView.as_view(), name='artist-verification-submit'),
    path('artist-verification/me/', ArtistVerificationView.as_view(), name='artist-verfication-me'),
    
    #admin
    path('admin/verifications/', AdminVerificationListView.as_view(), name='admin-verification-list'),
    path('admin/verifications/<uuid:verification_id>/approve/', AdminVerificationApproveView.as_view(), name='admin-verification-approve'),
    path('admin/verifications/<uuid:verification_id>/reject/', AdminVerificationRejectView.as_view(), name='admin-verification-reject'),
]
