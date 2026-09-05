import json
from channels.generic.websocket import AsyncWebsocketConsumer

class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope["user"]
        
        # Chỉ những người đã đăng nhập mới kết nối được
        if self.user.is_anonymous:
            await self.close()
        else:
            self.room_group_name = f'user_{self.user.id}'
            
            # Tham gia vào room của riêng user này
            await self.channel_layer.group_add(
                self.room_group_name,
                self.channel_name
            )
            
            await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )

    # Lắng nghe sự kiện "notification_message"
    async def notification_message(self, event):
        message = event['message']
        notification_data = event.get('notification_data', {})
        
        # Bắn dữ liệu về client dưới dạng JSON
        await self.send(text_data=json.dumps({
            'message': message,
            'notification': notification_data
        }))
