import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.core.cache import cache

from . import services
from . import selectors
from .exceptions import ConversationNotFoundError


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        """Khi có một Client kết nối tới ws://..."""
        self.user = self.scope["user"]
        self.conversation_id = self.scope['url_route']['kwargs']['conversation_id']
        
        # 1. Kiểm tra đăng nhập
        if not self.user.is_authenticated:
            await self.close()
            return
            
        # 2. Kiểm tra quyền truy cập (Dùng database_sync_to_async vì có query DB)
        try:
            await self.check_conversation_access(self.conversation_id, self.user)
        except ConversationNotFoundError:
            await self.close()
            return
            
        # 3. Tạo tên nhóm (Room) cho Redis
        self.room_group_name = f'chat_{self.conversation_id}'
        
        # 4. Tham gia nhóm
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()

    async def disconnect(self, close_code):
        """Khi Client ngắt kết nối"""
        # Rời khỏi nhóm
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )

    @database_sync_to_async
    def check_conversation_access(self, conversation_id, user):
        return selectors.get_conversation_by_id(conversation_id, user)

    async def receive(self, text_data):
        """Nhận dữ liệu từ Client gửi lên"""
        try:
            data = json.loads(text_data)
            event_type = data.get('type')
            
            if event_type == 'send_message':
                await self.handle_send_message(data)
            elif event_type == 'typing_status':
                await self.handle_typing_status(data)
            elif event_type == 'mark_read':
                await self.handle_mark_read(data)
                
        except Exception as e:
            await self.send(text_data=json.dumps({'error': str(e)}))

    # --- CÁC HÀM XỬ LÝ (HANDLERS) ---
    
    async def handle_send_message(self, data):
        """Lưu tin nhắn vào DB, sau đó broadcast cho nhóm"""
        message = await self.create_message_db(data)
        
        # Phát sóng (Broadcast) sự kiện tới tất cả người trong nhóm
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message', # Tên hàm sẽ được gọi để nhận event này
                'message_data': message
            }
        )
        
    async def handle_typing_status(self, data):
        """Trạng thái đang gõ (Không lưu DB)"""
        is_typing = data.get('is_typing', False)
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'typing_indicator',
                'user_id': str(self.user.id),
                'is_typing': is_typing
            }
        )
        
    async def handle_mark_read(self, data):
        """Cập nhật đã xem"""
        updated_count = await self.mark_read_db()
        if updated_count > 0:
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'read_receipt',
                    'user_id': str(self.user.id)
                }
            )

    # --- CÁC HÀM NHẬN BROADCAST TỪ REDIS VÀ GỬI XUỐNG CLIENT ---
    
    async def chat_message(self, event):
        """Nhận message từ group và gửi cho WebSocket client"""
        await self.send(text_data=json.dumps({
            'type': 'new_message',
            'data': event['message_data']
        }))
        
    async def typing_indicator(self, event):
        await self.send(text_data=json.dumps({
            'type': 'typing_status',
            'user_id': event['user_id'],
            'is_typing': event['is_typing']
        }))
        
    async def read_receipt(self, event):
        await self.send(text_data=json.dumps({
            'type': 'read_receipt',
            'user_id': event['user_id']
        }))

    # --- WRAPPER GỌI DATABASE (SYNC TO ASYNC) ---
    
    @database_sync_to_async
    def create_message_db(self, data):
        msg = services.create_message(self.user, self.conversation_id, data)
        return msg.to_dict()
        
    @database_sync_to_async
    def mark_read_db(self):
        return services.mark_messages_as_read(self.conversation_id, self.user)


class GlobalConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        """Kết nối toàn cục khi User vừa mở web/app"""
        self.user = self.scope["user"]
        
        if not self.user.is_authenticated:
            await self.close()
            return
            
        # 1. Đặt trạng thái Online vào Redis Cache (Sống 60 giây)
        self.cache_key = f'user_online_{self.user.id}'
        cache.set(self.cache_key, 'online', timeout=60)
        
        # 2. Lấy danh sách bạn bè để thông báo mình vừa Online
        friends = await self.get_friends_list(self.user)
        
        # 3. Join vào group cá nhân của chính mình (để nhận notifications)
        self.personal_group = f'user_global_{self.user.id}'
        await self.channel_layer.group_add(self.personal_group, self.channel_name)
        
        # 4. Bắn sự kiện online cho group của từng người bạn
        for friend_id in friends:
            await self.channel_layer.group_send(
                f'user_global_{friend_id}',
                {
                    'type': 'presence_update',
                    'user_id': str(self.user.id),
                    'status': 'online'
                }
            )
            
        await self.accept()

    async def disconnect(self, close_code):
        """Khi User tắt web"""
        if hasattr(self, 'user') and self.user.is_authenticated:
            # Xoá cache Online
            cache.delete(self.cache_key)
            
            # Thông báo cho bạn bè mình đã Offline
            friends = await self.get_friends_list(self.user)
            for friend_id in friends:
                await self.channel_layer.group_send(
                    f'user_global_{friend_id}',
                    {
                        'type': 'presence_update',
                        'user_id': str(self.user.id),
                        'status': 'offline'
                    }
                )
                
            await self.channel_layer.group_discard(self.personal_group, self.channel_name)

    async def receive(self, text_data):
        """Nhận Heartbeat từ Client để gia hạn thời gian Online"""
        try:
            data = json.loads(text_data)
            if data.get('type') == 'heartbeat':
                # Gia hạn thêm 60 giây
                cache.set(self.cache_key, 'online', timeout=60)
        except Exception:
            pass

    async def presence_update(self, event):
        """Nhận event từ bạn bè và đẩy xuống Client"""
        await self.send(text_data=json.dumps({
            'type': 'presence_update',
            'user_id': event['user_id'],
            'status': event['status']
        }))

    @database_sync_to_async
    def get_friends_list(self, user):
        """Lấy danh sách ID bạn bè từ Follow model"""
        from social.models import Follow
        # Những người mà user đang follow VÀ họ cũng follow lại user
        following_ids = Follow.objects.filter(follower=user).values_list('following_id', flat=True)
        friends_ids = Follow.objects.filter(follower_id__in=following_ids, following=user).values_list('follower_id', flat=True)
        return list(friends_ids)
