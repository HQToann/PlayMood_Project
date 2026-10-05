from django.urls import path
from . import views

urlpatterns = [
    # Danh sách cuộc trò chuyện và tạo cuộc trò chuyện mới
    path('conversations/', views.ConversationListView.as_view(), name='conversation-list'),
    
    # Lịch sử tin nhắn
    path('conversations/<uuid:conversation_id>/messages/', views.MessageListView.as_view(), name='message-list'),
    
    # Upload ảnh
    path('upload-image/', views.UploadImageView.as_view(), name='upload-image'),
]
