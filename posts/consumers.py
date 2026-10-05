import json
from channels.generic.websocket import AsyncWebsocketConsumer

class FeedConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope["user"]
        
        # Ai cũng có thể xem feed
        if self.user.is_anonymous:
            await self.close()
        else:
            self.room_group_name = 'live_feed'
            
            # Tham gia vào room chung của bảng tin
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

    # Lắng nghe sự kiện "feed_message"
    async def feed_message(self, event):
        message_type = event['message_type']
        data = event.get('data', {})
        
        await self.send(text_data=json.dumps({
            'type': message_type,
            'data': data
        }))
