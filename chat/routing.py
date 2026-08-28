from django.urls import path
from . import consumers

websocket_urlpatterns = [
    # Kết nối vào thông báo toàn cục (Online status, Notification)
    path('ws/chat/global/', consumers.GlobalConsumer.as_asgi()),
    
    # Kết nối vào một cuộc trò chuyện cụ thể
    path('ws/chat/conversation/<uuid:conversation_id>/', consumers.ChatConsumer.as_asgi()),
]
