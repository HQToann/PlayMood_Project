from django.contrib import admin
from .models import Conversation, Message

class MessageInline(admin.TabularInline):
    """
    Giúp hiển thị các tin nhắn ngay bên trong trang chi tiết của Cuộc trò chuyện
    """
    model = Message
    extra = 0
    readonly_fields = ('id', 'created_at')

@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ('id', 'created_at', 'updated_at')
    inlines = [MessageInline]
    filter_horizontal = ('participants',)
    readonly_fields = ('id', 'created_at', 'updated_at')
    search_fields = ('participants__username', 'participants__email')

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'conversation',
        'sender',
        'short_content',
        'is_read',
        'created_at',
    )

    list_filter = (
        'is_read',
        'created_at',
    )

    search_fields = (
        'content',
        'sender__email',
        'sender__username',
    )

    readonly_fields = (
        'id',
        'created_at',
    )

    def short_content(self, obj):
        """
        Cắt ngắn nội dung tin nhắn nếu quá dài để hiển thị gọn trên bảng
        """
        if obj.content:
            return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
        if obj.image_url:
            return '[Hình ảnh]'
        if obj.shared_song:
            return f'[Chia sẽ bài hát: {obj.shared_song.title}]'
        return '[Không có nội dung]'
    short_content.short_description = 'Nội dung'